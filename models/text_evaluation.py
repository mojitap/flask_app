from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv
import re
from load_surnames import load_surnames
from flask import current_app
from textblob import TextBlob

# spacy の日本語パーサー（簡易版）
nlp = Japanese()

def normalize_text(text):
    """全角→半角、カタカナ→ひらがなに変換する。"""
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    return jaconv.kata2hira(text)

def check_exact_match(text, words):
    for word in words:
        if word == text:
            return True, word
    return False, None

def check_partial_match(text, words, threshold=75):
    """RapidFuzz を用いて部分一致をチェックする。"""
    for word in words:
        if word in text:
            return True, word, 100
        score = fuzz.partial_ratio(word, text)
        if score >= threshold:
            return True, word, score
    return False, None, None

def detect_violence(text):
    """暴力表現の検出"""
    return "殺" in text

def detect_personal_accusation(text):
    """対象となる代名詞 + 犯罪組織に関連する語句の組み合わせを検出"""
    pattern = re.compile(r"(お前|おまえ|コイツ|アイツ)\s*.*?(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織)")
    return bool(pattern.search(text))

def analyze_sentiment(text):
    """感情分析（ユーザーには表示しない）"""
    analysis = TextBlob(text)
    polarity = analysis.sentiment.polarity  # -1.0（ネガティブ）～ +1.0（ポジティブ）
    
    if polarity > 0.2:
        return "ポジティブ", polarity
    elif polarity < -0.2:
        return "ネガティブ", polarity
    else:
        return "ニュートラル", polarity

def evaluate_text(text, offensive_words):
    """
    入力テキストを評価する。感情分析の結果を内部的に利用し、問題表現の精度を向上させる。
    """
    # 正規化
    normalized_text = normalize_text(text)
    norm_offensive_words = [normalize_text(word) for word in offensive_words]

    # 感情分析を実施（表示はしない）
    sentiment_label, sentiment_score = analyze_sentiment(text)

    # 苗字リストを取得
    surnames = load_surnames()

    # **問題単語 + 苗字の組み合わせをチェック**
    found_words = []
    found_surnames = []

    for word in offensive_words:
        match, matched_word, _ = check_partial_match(text, [word])
        if match:
            found_words.append(matched_word)

    for surname in surnames:
        if surname in text:
            found_surnames.append(surname)

    # **問題単語と苗字の両方が含まれる場合は問題あり**
    if found_words and found_surnames:
        return "⚠️ 該当あり", f"この文章には問題のある表現と特定の苗字が含まれています: {', '.join(found_words + found_surnames)}"

    # **暴力表現のチェック**
    if detect_violence(text):
        return "⚠️ この文章は暴力的な表現が含まれています。専門家へ相談ください。", "暴力表現検出"

    # **対象表現のチェック（個人攻撃の検出）**
    if detect_personal_accusation(text):
        return "⚠️ この文章は、特定の人物に対する攻撃的な表現が含まれています。専門家へ相談ください。", "攻撃的表現(対象指摘)"

    # **完全一致判定**
    exact, word = check_exact_match(normalized_text, norm_offensive_words)
    if exact:
        return "⚠️ この文章は名誉毀損や誹謗中傷に該当する可能性があります。専門家へ相談ください。", word

    # **部分一致判定**
    partial, word, score = check_partial_match(normalized_text, norm_offensive_words)
    if partial:
        return "⚠️ 一部の表現が問題となる可能性があります。専門家へ相談ください。", word

    # **感情分析を利用して、ネガティブな場合は再評価**
    if sentiment_label == "ネガティブ":
        return "⚠️ 感情分析により注意が必要な表現が含まれています。", "ネガティブ検出"

    return "✅ 問題ありません", None
