import os
import json
import re
import requests
from collections import OrderedDict
from functools import lru_cache
import spacy
from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv
import pykakasi
import io  # ✅ メモリでデータを処理するために追加

# Dropbox の URL
DROPBOX_URL = "https://www.dropbox.com/scl/fi/tvmzgc4vgy97nkl6v1u54/surnames.csv?rlkey=xxxxx&dl=1"

nlp = spacy.load("ja_core_news_sm")

def load_surnames():
    """✅ Dropbox から苗字リストを取得し、メモリ上で処理"""
    print(f"📥 Dropbox から {DROPBOX_URL} をダウンロードします...")
    try:
        response = requests.get(DROPBOX_URL, timeout=10)
        response.raise_for_status()
        
        csv_data = response.content.decode("utf-8")  # ✅ ファイル保存せずメモリ処理
        surnames = [line.strip() for line in csv_data.splitlines()]

        if not surnames:
            print("⚠️ 苗字リストが空です。")
        else:
            print(f"✅ 苗字リストを {len(surnames)} 件ロードしました！")
        
        return surnames
    except requests.RequestException as e:
        print(f"❌ Dropbox から surnames.csv のダウンロードに失敗しました: {e}")
        return []

def load_whitelist(json_path="data/whitelist.json"):
    """✅ ホワイトリストを読み込む"""
    if not os.path.exists(json_path):
        print(f"⚠️ {json_path} が見つかりません。ホワイトリストは空です。")
        return set()
    with open(json_path, "r", encoding="utf-8") as f:
        return set(json.load(f))

@lru_cache(maxsize=1000)
def cached_tokenize(text):
    doc = nlp(text)
    return [token.lemma_ for token in doc]

# テキストごとの判定結果をキャッシュ
_eval_cache = {}

def load_offensive_dict(json_path="offensive_words.json"):
    """✅ offensive_words.json を読み込む"""
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} が見つかりません。")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data

def flatten_offensive_words(offensive_dict):
    """✅ offensive_words.json の全単語をリスト化"""
    all_words = []
    categories = offensive_dict.get("categories", {})
    for _, word_list in categories.items():
        all_words.extend(word_list)
    return list(set(all_words))

def normalize_text(text):
    """✅ 全角→半角, カタカナ→ひらがな, 漢字→ひらがな変換"""
    kakasi = pykakasi.kakasi()
    result = kakasi.convert(text)
    return "".join([entry['hira'] for entry in result])

def fuzzy_match_keywords(text, keywords, threshold=80):
    """✅ 類似度チェック（閾値80）"""
    for kw in keywords:
        score = fuzz.partial_ratio(kw, text)
        if score >= threshold:
            return True
    return False

@lru_cache(maxsize=1000)
def check_partial_match(text, word_list, whitelist, threshold=80):
    """✅ 部分一致チェック（ホワイトリスト考慮）"""
    for w in word_list:
        if w in whitelist:
            continue  # ✅ ホワイトリストにある場合は無視

        if w in text:
            return True, w, 100  # ✅ 完全一致なら即マッチ

        score = fuzz.partial_ratio(w, text)
        if score >= threshold:
            return True, w, score
    return False, None, None

def detect_personal_accusation(text):
    """✅ 「お前」などの指示語 + 「詐欺グループ」「反社」等が同一文にあるかを検出"""
    pronouns_pattern = r"(お前|こいつ|この人|あなた|アナタ|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_pattern = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン)"

    norm = normalize_text(text)
    pattern = rf"{pronouns_pattern}.*?{crime_pattern}|{crime_pattern}.*?{pronouns_pattern}"
    
    matches = re.findall(pattern, norm)
    return bool(matches)

def evaluate_text(text, offensive_dict, whitelist=None):
    """✅ テキストを評価し、問題のある表現を検出する"""
    if whitelist is None:
        whitelist = set()

    if text in _eval_cache:
        return _eval_cache[text]

    normalized = normalize_text(text.lower())  
    all_offensive = flatten_offensive_words(offensive_dict)
    surnames = load_surnames()  # ✅ Dropbox から取得する方式

    problematic = False
    detail_flags = []

    # ✅ 固定リストによる完全一致チェック
    violence_keywords = {"殺す", "死ね", "殴る", "蹴る", "爆破"}
    harassment_kws = {"お前消えろ", "存在価値ない", "いらない人間"}
    threat_kws = {"晒す", "特定する", "ぶっ壊す", "復讐する"}

    if normalized in violence_keywords:
        return "⚠️ 一部の表現が問題となる可能性があります。", "暴力的表現（完全一致）"
    if normalized in harassment_kws:
        return "⚠️ 一部の表現が問題となる可能性があります。", "ハラスメント的表現（完全一致）"
    if normalized in threat_kws:
        return "⚠️ 一部の表現が問題となる可能性があります。", "脅迫的表現（完全一致）"

    match, w, score = check_partial_match(normalized, tuple(all_offensive), tuple(whitelist), threshold=80)
    if match and w not in whitelist:
        problematic = True
        detail_flags.append(f"offensive_word: {w} (score={score})")

    found_surnames = [sn for sn in surnames if sn in normalized]
    if found_surnames:
        detail_flags.append(f"found_surnames: {found_surnames}")

    if fuzzy_match_keywords(normalized, violence_keywords, threshold=80):
        problematic = True
        detail_flags.append("暴力的表現（部分一致）")
    if fuzzy_match_keywords(normalized, harassment_kws, threshold=80):
        problematic = True
        detail_flags.append("ハラスメント的表現（部分一致）")
    if fuzzy_match_keywords(normalized, threat_kws, threshold=80):
        problematic = True
        detail_flags.append("脅迫的表現（部分一致）")

    if found_surnames and match:
        problematic = True
        detail_flags.append("人名 + オフェンシブ表現")

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
        print(f"\n入力: {t}\n判定: {res}\n{'-'*40}")
