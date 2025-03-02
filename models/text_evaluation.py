import os
import json
import re
from collections import OrderedDict
from functools import lru_cache
import spacy
from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv
import pykakasi

# 苗字をロードする関数
from models.load_surnames import load_surnames

nlp = spacy.load("ja_core_news_sm")

@lru_cache(maxsize=1000)
def cached_tokenize(text):
    doc = nlp(text)
    return [token.lemma_ for token in doc]

# テキストごとの判定結果をキャッシュ
_eval_cache = {}

def load_offensive_dict(json_path="offensive_words.json"):
    """offensive_words.json を読み込む"""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} が見つかりません。")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data

def flatten_offensive_words(offensive_dict):
    """offensive_words.json の全ての単語をリスト化"""
    all_words = []
    categories = offensive_dict.get("categories", {})
    for _, word_list in categories.items():
        all_words.extend(word_list)
    return all_words

def normalize_text(text):
    """全角→半角, カタカナ→ひらがな, 漢字→ひらがな変換"""
    kakasi = pykakasi.kakasi()
    result = kakasi.convert(text)
    return "".join([entry['hira'] for entry in result])

def fuzzy_match_keywords(text, keywords, threshold=80):
    """
    類似度チェック（閾値80に設定）
    """
    for kw in keywords:
        score = fuzz.partial_ratio(kw, text)
        if score >= threshold:
            return True
    return False

@lru_cache(maxsize=1000)
def check_partial_match(text, word_list, threshold=80):
    """単語の部分一致チェック（類似度スコアも考慮）"""
    for w in word_list:
        if w in text:
            return True, w, 100  # 完全一致なら即マッチ
        score = fuzz.partial_ratio(w, text)
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
    """テキストを評価し、問題のある表現を検出する"""
    if whitelist is None:
        whitelist = set()

    # キャッシュにあればそのまま返す
    if text in _eval_cache:
        return _eval_cache[text]

    normalized = normalize_text(text)
    all_offensive = flatten_offensive_words(offensive_dict)
    surnames = load_surnames()

    problematic = False
    detail_flags = []

    # --- (1) 完全一致チェック（最優先） ---
    violence_keywords = {"殺す", "死ね", "殺し", "殴って", "殴る", "蹴る", "刺す", "轢く", "焼く", "爆破", "クソが"}
    harassment_kws = {"お前消えろ", "存在価値ない", "いらない人間", "死んだほうがいい", "社会のゴミ", "学校来るな"}
    threat_kws = {"晒す", "晒そう", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"}

    if normalized in violence_keywords:
        return "⚠️ 一部の表現が問題となる可能性があります。", "暴力的表現（完全一致）"

    if normalized in harassment_kws:
        return "⚠️ 一部の表現が問題となる可能性があります。", "ハラスメント的表現（完全一致）"

    if normalized in threat_kws:
        return "⚠️ 一部の表現が問題となる可能性があります。", "脅迫的表現（完全一致）"

    # --- (2) offensive_words.json の部分一致チェック ---
    match, w, score = check_partial_match(normalized, all_offensive, threshold=80)
    if match and w not in whitelist:
        problematic = True
        detail_flags.append(f"offensive_word: {w} (score={score})")

    # --- (3) 苗字チェック ---
    found_surnames = [sn for sn in surnames if sn in normalized]
    if found_surnames:
        detail_flags.append(f"found_surnames: {found_surnames}")

    # --- (4) 類似度チェック（部分一致） ---
    if fuzzy_match_keywords(normalized, violence_keywords, threshold=80):
        problematic = True
        detail_flags.append("暴力的表現（部分一致）")

    if fuzzy_match_keywords(normalized, harassment_kws, threshold=80):
        problematic = True
        detail_flags.append("ハラスメント的表現（部分一致）")

    if fuzzy_match_keywords(normalized, threat_kws, threshold=80):
        problematic = True
        detail_flags.append("脅迫的表現（部分一致）")

    # --- (5) 苗字 + offensive ワード が同時にあれば問題度UP ---
    if found_surnames and match:
        problematic = True
        detail_flags.append("人名 + オフェンシブ表現")

    # --- (6) 個人攻撃 + 犯罪組織チェック ---
    if detect_personal_accusation(text):
        return "⚠️ 一部の表現が問題となる可能性があります。", "個人攻撃+犯罪組織表現"

    # --- (7) 判定結果の生成 ---
    if problematic:
        judgement = "⚠️ 一部の表現が問題となる可能性があります。"
        detail = " / ".join(detail_flags) + "\n※この判定は..."
    else:
        judgement = "問題ありません"
        detail = ""

    _eval_cache[text] = (judgement, detail)
    return judgement, detail

if __name__ == "__main__":
    offensive_dict = load_offensive_dict("offensive_words.json")
    test_texts = [
        "山下ってブスだよな",
        "山下は政治家",
        "ブスだな",
        "死ね",
        "お前は詐欺グループとつながってる",
        "普通の文章です",
        "学校来るな"
    ]

    for t in test_texts:
        res = evaluate_text(t, offensive_dict)
        print(f"\n入力: {t}\n判定: {res}\n{'-'*40'}")
