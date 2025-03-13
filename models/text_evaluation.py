# text_evaluation.py
import os
import json
import re

from collections import OrderedDict  # キャッシュ管理用
from functools import lru_cache
import spacy
from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv

# あなたの環境で苗字をロードする関数（相対 or 絶対インポートに合わせて調整してください）
from .load_surnames import load_surnames

# 形態素解析のキャッシュ
nlp = spacy.load("ja_core_news_sm")  # 事前にロード（1回だけ）

@lru_cache(maxsize=1000)
def cached_tokenize(text):
    doc = nlp(text)
    return [token.lemma_ for token in doc]

# 簡易キャッシュ（メモリに保存）: テキスト → 判定結果
_eval_cache = {}

def load_offensive_dict(json_path="offensive_words.json"):
    """
    offensive_words.json を辞書としてロード。
    {
      "categories": {
        "insults": [...],
        "defamation": [...],
        "harassment": [...],
        "threats": [...],
         ...
      },
      "names": [...]
    }
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} が見つかりません。")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def load_whitelist(json_path="data/whitelist.json"):
    """
    whitelist.json を読み込んで set(...) を返す。
    形式: ["ありえない", "誤検出しがち", ...]
    """
    if not os.path.exists(json_path):
        print(f"⚠️ {json_path} が見つかりません。ホワイトリストは空です。")
        return set()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data)
    
def flatten_offensive_words(offensive_dict):
    # offensive_dict が { "offensive": [ ... ] } の場合
    if "offensive" in offensive_dict:
        return offensive_dict["offensive"]
    return []

def normalize_text(text):
    """
    全角→半角、カタカナ→ひらがな に変換
    """
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    return jaconv.kata2hira(text)

def tokenize_and_lemmatize(text):
    return cached_tokenize(text)

def check_keywords_via_token(text, keywords):
    """
    形態素解析した結果（トークン列）で判定するサンプル。
    text, keywords の両方を tokenize_and_lemmatize してから、
    set(kw_tokens).issubset(set(text_tokens)) で包含判定する例。
    """
    text_tokens = tokenize_and_lemmatize(text)
    for kw in keywords:
        kw_tokens = tokenize_and_lemmatize(kw)
        # すべてのトークンが text_tokens に含まれているか？
        if set(kw_tokens).issubset(set(text_tokens)):
            return True
    return False

def fuzzy_match_keywords(text, keywords, threshold=90):
    """
    text 内に、keywords のいずれかが部分一致または類似度スコアが threshold 以上で存在するか判定
    """
    for kw in keywords:
        score = fuzz.partial_ratio(kw, text)
        if score >= threshold:
            return True
    return False

@lru_cache(maxsize=1000)
def check_partial_match(text, word_list, threshold=80):
    """
    offensive_words.json に基づく文字列ベースの部分一致チェック
      - 完全一致なら score=100
      - fuzz.ratio(w, text) が threshold 以上ならマッチ
    """
    for w in word_list:
        if w in text:
            return True, w, 100
        score = fuzz.ratio(w, text)
        if score >= threshold:
            return True, w, score
    return False, None, None

def detect_personal_accusation(text):
    pronouns_pattern = r"(お前|こいつ|この人|あなた|アナタ|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_pattern = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン)"
    norm = normalize_text(text)
    pattern = rf"{pronouns_pattern}.*{crime_pattern}|{crime_pattern}.*{pronouns_pattern}"
    return re.search(pattern, norm) is not None

def evaluate_text(text, offensive_dict, whitelist=None):
    if whitelist is None:
        whitelist = set()

    if text in _eval_cache:
        return _eval_cache[text]
    if len(_eval_cache) > 1000:
        _eval_cache.popitem(last=False)  # キャッシュサイズ制限

    # ▼▼▼ デバッグ出力 ▼▼▼
    print(f"[DEBUG] evaluate_text called with text='{text}'")

    normalized = normalize_text(text)
    print(f"[DEBUG] normalized='{normalized}'")

    all_offensive = flatten_offensive_words(offensive_dict)
    print(f"[DEBUG] all_offensive[:34] = {all_offensive[:34]}")

    judgement = "問題ありません"
    detail = ""

    # ホワイトリストにも normalize_text() を適用
    whitelist = {normalize_text(w) for w in whitelist}

    # (1) offensive_words.json に基づく部分一致チェック（80%以上）
    found_words = [
        word for word in all_offensive if word in normalized
    ]

    # (1.5) 曖昧検索（80%以上でマッチ）
    fuzzy_matched_words = [
        word for word in all_offensive if fuzzy_match_keywords(normalized, [word], threshold=80)
    ]

    # (1.6) ホワイトリストにある単語は除外
    found_words = [w for w in found_words if w not in whitelist]
    fuzzy_matched_words = [w for w in fuzzy_matched_words if w not in whitelist]

    # (1.7) もし offensive_words に含まれる単語が見つかったら
    if found_words or fuzzy_matched_words:
        judgement = "⚠️ 一部の表現が問題の可能性"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        print(f"[DEBUG] 🔍 マッチした単語: {found_words + fuzzy_matched_words}")  # デバッグ用出力
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (2) 苗字チェック
    surnames = load_surnames()
    found_surnames = [sn for sn in surnames if sn in normalized]

    # (3) 個人攻撃 + 犯罪組織
    if detect_personal_accusation(text):
        judgement = "⚠️ 個人攻撃 + 犯罪組織関連の表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (4) 人名あり + offensive_words.json 登録キーワードがある場合（80%以上で判定）
    if found_words and found_surnames:
        judgement = "⚠️ 一部の表現が問題となる可能性があります。"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (5) 暴力表現の例（登録外でも、キーワードと入力テキストの類似度が80%以上なら検出）
    violence_keywords = ["殺す", "死ね", "殴る", "蹴る", "刺す", "轢く", "焼く", "爆破", "死んでしまえ"]
    if any(kw in normalized for kw in violence_keywords) or fuzzy_match_keywords(normalized, violence_keywords, threshold=80):
        judgement = "⚠️ 暴力的表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (6) いじめ/ハラスメントの例（80%以上で検出）
    harassment_kws = ["お前消えろ", "存在価値ない", "いらない人間", "死んだほうがいい", "社会のゴミ"]
    if any(kw in normalized for kw in harassment_kws) or fuzzy_match_keywords(normalized, harassment_kws, threshold=80):
        judgement = "⚠️ ハラスメント表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (7) 脅迫など（80%以上で検出）
    threat_kws = ["晒す", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"]
    if any(kw in normalized for kw in threat_kws) or fuzzy_match_keywords(normalized, threat_kws, threshold=80):
        judgement = "⚠️ 脅迫表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    _eval_cache[text] = (judgement, detail)
    return judgement, detail

    # (8) 脅迫など（80%以上で検出）
    threat_kws = ["晒す", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"]
    if any(kw in normalized for kw in threat_kws) or fuzzy_match_keywords(normalized, threat_kws, threshold=80):
        judgement = "⚠️ 脅迫表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    _eval_cache[text] = (judgement, detail)
    return judgement, detail

# テスト用サンプル
if __name__ == "__main__":
    offensive_dict = load_offensive_dict("offensive_words.json")
    tests = [
        "山下ってブスだよな",           # 人名+侮辱 => 問題あり
        "山下は政治家",                 # 人名のみ => 問題なし
        "ブスだな",                     # 人名なし+オフェンシブ => 問題あり
        "死ね",                         # 暴力的(形態素チェック) => 問題あり
        "お前は詐欺グループとつながってる",   # 個人攻撃+犯罪組織 => 問題あり
        "学校に来るな", 
        "普通の文章です"                # 問題なし
    ]
    for t in tests:
        res = evaluate_text(t, offensive_dict)
        print(f"入力: {t} => 判定: {res}")
