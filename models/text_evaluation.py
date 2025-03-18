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

# =========================================
# A) ユーティリティ関数
# =========================================
def normalize_text(text: str) -> str:
    """
    全角カタカナに統一するサンプル例。
      - h2z(..., kana=True) で半角カナ → 全角カナ
      - hira2kata() でひらがな → カタカナ
      - 半角の「ｰ」(U+FF70) は全角「ー」(U+30FC) に統一
    """
    # 1) 半角カナを全角カナへ
    text = jaconv.h2z(text, kana=True, digit=False, ascii=False)

    # 2) 半角の長音符号「ｰ」が残っている場合は全角「ー」に統一
    text = text.replace('ｰ', 'ー')

    # 3) ひらがな → カタカナ
    text = jaconv.hira2kata(text)

    return text

def tokenize_and_lemmatize(text: str):
    """
    正規化 + spaCy lemma の一連の処理
    """
    norm = normalize_text(text)
    return cached_tokenize(norm)

# =========================================
# B) offensive_words.json のロード（token化付き）
# =========================================
def load_offensive_dict_with_tokens(json_path="offensive_words.json"):
    """
    1) JSON をロード
    2) "offensive" キーのリストを取り出し
    3) 各ワードをトークン化
    4) [{"original": w, "norm": w_norm, "tokens": [...]}] を返す
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} が見つかりません。")

    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    words = raw_data.get("offensive", [])
    results = []
    for w in words:
        w_norm = normalize_text(w)
        w_tokens = tokenize_and_lemmatize(w_norm)
        results.append({
            "original": w,
            "norm": w_norm,
            "tokens": w_tokens
        })
    return results

# =========================================
# C) whitelist.json のロード（set で保持）
# =========================================
def load_whitelist(json_path="data/whitelist.json"):
    """
    ["ありがとう", "愛してる", ...] のように配列形式を想定 → set(...) へ
    """
    if not os.path.exists(json_path):
        print(f"⚠️ {json_path} が見つかりません。ホワイトリストは空です。")
        return set()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data)

# =========================================
# D) 個別ロジック（例: 個人攻撃 + 犯罪組織）
# =========================================
def detect_personal_accusation(text: str) -> bool:
    """
    「お前 × 詐欺グループ」など個人攻撃 + 犯罪組織の簡易検出
    """
    pronouns_pattern = r"(お前|こいつ|この人|あなた|アナタ|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_pattern = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン)"
    norm = normalize_text(text)
    pattern = rf"{pronouns_pattern}.*{crime_pattern}|{crime_pattern}.*{pronouns_pattern}"
    return bool(re.search(pattern, norm))

# =========================================
# ファジーマッチ用関数
# =========================================
def token_match(dict_token, input_token, threshold=85):
    """
    短いdict_token(2文字以下)は完全一致でチェック。
    3文字以上の場合はpartial_ratioで閾値判定。
    """
    # もし 2文字以下の単語なら完全一致チェック
    if len(dict_token) <= 2:
        return dict_token == input_token
    else:
        return fuzz.partial_ratio(dict_token, input_token) >= threshold
        
# =========================================
# E) メインの判定ロジック
# =========================================
_eval_cache = {}

def evaluate_text(
    text: str,
    offensive_list: list,  # [{"original":..., "norm":..., "tokens":[...]}]
    whitelist: set = None
):
    """
    :param text: 入力文字列
    :param offensive_list: 形態素解析済み辞書
    :param whitelist: {"ありがとう", "愛してる", ...} のようなセット
    :return: (判定, detail)
    """
    if whitelist is None:
        whitelist = set()

    # 既に判定済みならキャッシュから返す
    if text in _eval_cache:
        return _eval_cache[text]
        
    # A) 入力テキストを形態素解析
    input_norm = normalize_text(text)
    input_tokens = tokenize_and_lemmatize(input_norm)

    # B) offensive_list 判定
    found_offensive = []
    for item in offensive_list:
        dict_original = item["original"]
        dict_norm = item["norm"]
        dict_tokens = item["tokens"]

        # --- ファジーマッチを使った判定へ変更 ---
        # 「辞書の全トークン」が「入力文のどこかに80%以上部分一致」すればOKとする
        if all(
            any(token_match(dict_token, inp_token) for inp_token in input_tokens)
            for dict_token in dict_tokens
        ):
            # ホワイトリストチェック
            if dict_original in whitelist or dict_norm in whitelist:
                # print(f"✅ ホワイトリスト除外: {dict_original}")
                continue
            found_offensive.append(dict_original)

    # C) 個人攻撃 + 犯罪組織
    surnames = load_surnames()
    if any(sn in text for sn in surnames) and any(neg in text for neg in ["きらい", "嫌い", "憎い"]):
        judgement = "⚠️ 個人攻撃の可能性あり"
        detail = "※個人名と否定的な表現の組み合わせが検出されました。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    # D) offensive_list にヒットした場合
    surnames = load_surnames()
    if found_offensive:
        judgement = "⚠️ 一部の表現が問題の可能性"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    # E) 以下、暴力・ハラスメント・脅迫などを substring/fuzzy で判定
    # --------------------------------------------------
    surnames = load_surnames()
    violence_keywords = ["殺す", "死ね", "殴る", "蹴る", "刺す", "轢く", "焼く", "爆破", "死んでしまえ"]
    if any(fuzz.partial_ratio(kw, input_norm) >= 90 for kw in violence_keywords):
        judgement = "⚠️ 暴力的表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    surnames = load_surnames()
    harassment_kws = ["お前消えろ", "存在価値ない", "いらない人間", "死んだほうがいい", "社会のゴミ"]
    if any(fuzz.partial_ratio(kw, input_norm) >= 90 for kw in harassment_kws):
        judgement = "⚠️ ハラスメント表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    surnames = load_surnames()
    threat_kws = ["晒す", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"]
    if any(fuzz.partial_ratio(kw, input_norm) >= 90 for kw in threat_kws):
        judgement = "⚠️ 脅迫表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    # F) 問題なし
    _eval_cache[text] = ("問題ありません", "")
    return ("問題ありません", "")

# =========================================
# 5) テスト実行
# =========================================
if __name__ == "__main__":
    # A) offensive_list
    offensive_list = load_offensive_dict_with_tokens("offensive_words.json")
    # B) whitelist
    wl = load_whitelist("data/whitelist.json")

    tests = [
        "山下ってブスだよな",          # 問題あり(辞書にブスがあれば)
        "ブスだな",                    # 問題あり(同上)
        "愛してる",                    # ホワイトリストにあれば除外
        "ありがとう",                  # 同上
        "死ね",                        # 暴力表現
        "殴ってやる",                 # 暴力表現
        "お前消えろ",                  # ハラスメント
        "お前は詐欺グループとつながってる",  # 個人攻撃 + 犯罪組織
        "中居ってレイプ魔だろ",       # ←ファジーマッチで "レイプ魔" を検出
        "普通の文章です"               # 問題なし
    ]
    for t in tests:
        j, d = evaluate_text(t, offensive_list, wl)
        print(f"[TEST] {t} => {j} / {d}")
