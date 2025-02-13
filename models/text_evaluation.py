import spacy
from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv
import re
from load_surnames import load_surnames
from flask import current_app
from textblob import TextBlob

# ✅ SpaCy の日本語モデルをロード（軽量モデル使用）
nlp = Japanese()

def normalize_text(text):
    """全角→半角、カタカナ→ひらがなに変換する。"""
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    return jaconv.kata2hira(text)

def tokenize_and_lemmatize(text):
    """形態素解析をして、単語の原形リストを取得する"""
    doc = nlp(text)
    return [token.lemma_ for token in doc]  # ✅ すべての単語を原形に変換

def check_keywords(text, keywords):
    """
    形態素解析した単語リストとキーワードリストを比較し、一致するか判定する。
    """
    tokens = tokenize_and_lemmatize(text)
    return any(keyword in tokens for keyword in keywords)

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

def detect_personal_accusation(text):
    """対象となる代名詞 + 犯罪組織に関連する語句の組み合わせを検出"""
    pronouns = r"(お前|こいつ|この人|あなた|アナタ|このひと|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_words = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン|マネーロンダリング)"

def evaluate_text(text, offensive_words):
    """
    入力テキストを評価する。
    """
    # 正規化
    normalized_text = normalize_text(text)
    norm_offensive_words = [normalize_text(word) for word in offensive_words]
    
    # 苗字リストを取得
    surnames = load_surnames()
    
    # 1️⃣ **問題単語 + 苗字の組み合わせをチェック**
    found_words = []
    found_surnames = []
    
    for word in offensive_words:
        match, matched_word, _ = check_partial_match(text, [word])
        if match:
            found_words.append(matched_word)
    
    for surname in surnames:
        if surname in text:
            found_surnames.append(surname)
    
    if found_words and found_surnames:
        return "⚠️ この文章には問題のある表現と特定の苗字が含まれています"
    
    # ✅ **形態素解析で単語の原形を取得**
    tokens = tokenize_and_lemmatize(normalized_text)
    
    # ✅ **カテゴリ別チェック**
    
    # 2️⃣ **暴力表現のチェック**
    violence_keywords = ["殺す", "死ぬ", "殴る", "蹴る", "刺す", "轢く", "焼く", "爆破する"]
    if check_keywords(text, violence_keywords):
        return "⚠️ この文章には暴力的な表現が含まれています"
    
    # 3️⃣ **ハラスメント・いじめ表現のチェック**
    harassment_keywords = ["お前消えろ", "存在価値ない", "いらない人間", "死んだほうがいい", "社会のゴミ"]
    if check_keywords(text, harassment_keywords):
        return "⚠️ この文章はいじめ・ハラスメントの可能性があります"
    
    # 4️⃣ **脅迫・犯罪関連のチェック**
    threat_keywords = ["晒す", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"]
    if check_keywords(text, threat_keywords):
        return "⚠️ この文章には脅迫・犯罪関連の表現が含まれています"
    
    # 5️⃣ **曖昧な表現のチェック**
    ambiguous_keywords = ["○○人は出て行け", "○○人はゴミ", "○○人は劣っている", "女は黙れ"]
    if check_keywords(text, ambiguous_keywords):
        return "⚠️ この文章には問題となる可能性のある表現が含まれています"
    
    # 6️⃣ **完全一致判定**
    exact, word = check_exact_match(normalized_text, norm_offensive_words)
    if exact:
        return "⚠️ 一部の表現が問題となる可能性があります"
    
    # 7️⃣ **部分一致判定**
    partial, word, score = check_partial_match(normalized_text, norm_offensive_words)
    if partial:
        return "⚠️ 一部の表現が問題となる可能性があります"
    
    return "問題ありません"
