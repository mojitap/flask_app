import os
import json
import re
from collections import OrderedDict  # キャッシュ管理用
from functools import lru_cache
import spacy
from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv
import pykakasi

# あなたの環境で苗字をロードする関数
from models.load_surnames import load_surnames

nlp = spacy.load("ja_core_news_sm")

@lru_cache(maxsize=1000)
def cached_tokenize(text):
    doc = nlp(text)
    return [token.lemma_ for token in doc]

# テキストごとの判定結果をキャッシュ
_eval_cache = {}

def load_offensive_dict(json_path="offensive_words.json"):
    """
    offensive_words.json を辞書としてロード。
    {
      "categories": {
        "insults": [...],
        "defamation": [...],
        "harassment": [...],
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
    """
    offensive_words.json の "categories" 内のリストを全て合体して、1次元リストとして返す。
    """
    all_words = []
    categories = offensive_dict.get("categories", {})
    for _, word_list in categories.items():
        all_words.extend(word_list)
    return all_words

def normalize_text(text):
    """
    - 全角→半角変換
    - カタカナ→ひらがな変換
    - 漢字→ひらがな変換
    """
    kakasi = pykakasi.kakasi()
    result = kakasi.convert(text)
    return "".join([entry['hira'] for entry in result])

def tokenize_and_lemmatize(text):
    return cached_tokenize(text)

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
      - fuzz.(partial_)ratio(w, text) が threshold 以上ならマッチ
    """
    for w in word_list:
        # 完全一致チェック
        if w in text:
            return True, w, 100
        # ★ ここを ratio から partial_ratio に置き換える
-       score = fuzz.ratio(w, text)
+       score = fuzz.partial_ratio(w, text)

        if score >= threshold:
            return True, w, score
    return False, None, None

def detect_personal_accusation(text):
    """
    「お前」などの指示語 + 「詐欺グループ」「反社」等が同一文にあるかをざっくり検出
    """
    pronouns_pattern = r"(お前|こいつ|この人|あなた|アナタ|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_pattern = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン)"

    norm = normalize_text(text)
    pattern = rf"{pronouns_pattern}\W*{crime_pattern}|{crime_pattern}\W*{pronouns_pattern}"
    
    match = re.search(pattern, norm)
    return match is not None


def evaluate_text(text, offensive_dict, whitelist=None):
    """
    テキストを総合的に評価し、
    「問題ありません」もしくは「⚠️ 一部の表現が問題となる可能性があります。」
    を返す。detail に補足説明を入れる。
    """
    if whitelist is None:
        whitelist = set()

    # キャッシュにあれば使う
    if text in _eval_cache:
        return _eval_cache[text]
    # キャッシュが大きくなりすぎないよう適当に削除
    if len(_eval_cache) > 1000:
        _eval_cache.popitem(last=False)

    normalized = normalize_text(text)
    all_offensive = flatten_offensive_words(offensive_dict)
    surnames = load_surnames()

    # 判定用フラグや詳細メッセージをためる
    problematic = False
    detail_flags = []

    # --- (1) offensive_words.json に基づく部分一致チェック ---
    match, w, score = check_partial_match(normalized, tuple(all_offensive), threshold=80)
    if match:
        # ホワイトリストでなければ「問題あり」候補
        if w not in whitelist:
            problematic = True
            detail_flags.append(f"offensive_word: {w} (score={score})")

    # --- (2) 苗字チェック ---
    found_surnames = [sn for sn in surnames if sn in normalized]
    if found_surnames:
        detail_flags.append(f"found_surnames: {found_surnames}")

    # --- (3) 個人攻撃 + 犯罪組織 ---
    if detect_personal_accusation(text):
        problematic = True
        detail_flags.append("個人攻撃+犯罪組織表現")

    # --- (4) 苗字 + offensiveワード が同時にあれば問題度UP ---
    #     (すでにfound_surnamesも(1)もtrueなら問題あり)
    if found_surnames and match:
        problematic = True
        detail_flags.append("人名+オフェンシブ表現")

    # --- (5) ここまででオフェンシブ辞書にヒットしなかった場合でも
    #          (6) (7) (8) の暴力表現・ハラスメント・脅迫を確認したいので、まだreturnしない ---

    # (6) 暴力的表現
    violence_keywords = ["殺す", "死ね", "殴る", "蹴る", "刺す", "轢く", "焼く", "爆破"]
    # しきい値ゆるめ (60) で判定
    if any(kw in normalized for kw in violence_keywords) or fuzzy_match_keywords(normalized, violence_keywords, threshold=60):
        problematic = True
        detail_flags.append("暴力的表現")

    # (7) ハラスメント例
    harassment_kws = ["お前消えろ", "存在価値ない", "いらない人間", "死んだほうがいい", "社会のゴミ", "学校来るな"]
    # 「学校来るな」もここに入れたい場合はこの配列に追加しておくか、offensive_words.jsonに入れて部分一致でもOK
    if any(kw in normalized for kw in harassment_kws) or fuzzy_match_keywords(normalized, harassment_kws, threshold=60):
        problematic = True
        detail_flags.append("ハラスメント的表現")

    # (8) 脅迫表現
    threat_kws = ["晒す", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"]
    if any(kw in normalized for kw in threat_kws) or fuzzy_match_keywords(normalized, threat_kws, threshold=60):
        problematic = True
        detail_flags.append("脅迫的表現")

    # --- 最終判定 ---
    if problematic:
        judgement = "⚠️ 一部の表現が問題となる可能性があります。"
        detail = " / ".join(detail_flags) + "\n※この判定は..."
    else:
        judgement = "問題ありません"
        detail = ""

    # ここで初めて return
    return judgement, detail


if __name__ == "__main__":
    # テスト
    offensive_dict = load_offensive_dict("offensive_words.json")
    test_texts = [
        "山下ってブスだよな",         # 人名+侮辱 => 問題あり
        "山下は政治家",               # 人名のみ => 問題なし
        "ブスだな",                   # (辞書に「ブス」あれば) => 問題あり
        "死ね",                       # 暴力的 => 問題あり
        "お前は詐欺グループとつながってる", # 個人攻撃+犯罪組織 => 問題あり
        "普通の文章です",            # 問題なし
        "学校来るな"                 # ハラスメント => 問題あり
    ]

    for t in test_texts:
        res = evaluate_text(t, offensive_dict)
        print(f"\n入力: {t}\n判定: {res}\n{'-'*40}")
