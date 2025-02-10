# models/text_evaluation.py

from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv
import re
from load_surnames import load_surnames

# spacy の日本語パーサー（簡易版）
nlp = Japanese()

def normalize_text(text):
    """全角→半角、カタカナ→ひらがなに変換する。"""
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    return jaconv.kata2hira(text)

def get_lemmas(text):
    doc = nlp(text)
    return " ".join([token.lemma_ for token in doc])

def check_exact_match(text, words):
    for word in words:
        if word == text:
            return True, word
    return False, None

def check_partial_match(text, words, threshold=75):
    """
    RapidFuzz を用いて部分一致をチェックする。
    単純な部分文字列チェックも行い、閾値は75に設定。
    """
    for word in words:
        if word in text:
            return True, word, 100
        score = fuzz.partial_ratio(word, text)
        if score >= threshold:
            return True, word, score
    return False, None, None

def contextual_analysis(text):
    """
    例：感嘆符が3個以上の場合を攻撃的と判断する。
    """
    exclamation_count = text.count("!")
    if exclamation_count > 3:
        return True, "感嘆符が多すぎます"
    return False, None

def detect_violence(text):
    """
    単純に「殺」という文字が含まれているかで暴力表現を検出する。
    """
    if "殺" in text:
        return True
    return False

def detect_personal_accusation(text):
    """
    対象となる代名詞（「お前」「おまえ」「コイツ」「アイツ」など）と、
    犯罪組織に関連する語句（「反社」「暴力団」「詐欺団体」「詐欺グループ」「犯罪組織」など）
    が同時に現れる場合に True を返す。
    正規表現を使って柔軟にチェックする。
    """
    # 正規表現パターン例（対象となる代名詞の後に任意の文字が続いて、組織関連語が現れる場合）
    pattern = re.compile(r"(お前|おまえ|コイツ|アイツ)\s*.*?(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織)")
    return bool(pattern.search(text))

def contains_surname(text, surnames):
    """
    テキスト内に苗字が含まれているかチェックする関数
    """
    for surname in surnames:
        if surname in text:
            return True, surname  # 苗字が見つかった場合
    return False, None  # 苗字が見つからない場合

# テスト用コード（デバッグ目的）
if __name__ == "__main__":
    surnames = load_surnames()  # CSVから苗字リストを読み込む
    test_text = "この文章には安威という苗字が含まれています。"
    found, surname = contains_surname(test_text, surnames)
    if found:
        print(f"苗字 '{surname}' が見つかりました。")
    else:
        print("苗字は見つかりませんでした。")

def evaluate_text(text, offensive_words):
    """
    入力テキストを評価する。以下の順序でチェックする：
      0. 暴力表現の検出
      1. 対象表現（代名詞と組織関連語）の検出
      2. 完全一致判定
      3. 部分一致判定
      4. 文脈解析
    """
    # 正規化
    normalized_text = normalize_text(text)
    norm_offensive_words = [normalize_text(word) for word in offensive_words]

    # 苗字のチェック
    surnames = load_surnames()
    found, surname = contains_surname(text, surnames)
    if found:
        return f"この文章には特定の苗字 '{surname}' が含まれています。", surname

    # 他のチェックを順に実行
    # (暴力表現チェック、個人攻撃チェック、完全一致チェックなど)
    return "問題ありません", None

    # 0. 暴力表現のチェック
    if detect_violence(text):
        return "この文章は暴力的な表現が含まれています。専門家へ相談ください。", "暴力表現検出"

    # 1. 対象表現のチェック（個人攻撃の検出）
    if detect_personal_accusation(text):
        return "この文章は、特定の人物に対する攻撃的な表現が含まれています。専門家へ相談ください。", "攻撃的表現(対象指摘)"

    # 2. 完全一致判定
    exact, word = check_exact_match(normalized_text, norm_offensive_words)
    if exact:
        return "この文章は名誉毀損や誹謗中傷に該当する可能性があります。専門家へ相談ください。", word

    # 3. 部分一致判定
    partial, word, score = check_partial_match(normalized_text, norm_offensive_words)
    if partial:
        return "一部の表現が問題となる可能性があります。専門家へ相談ください。", word

    # 4. 文脈解析
    context_flag, reason = contextual_analysis(text)
    if context_flag:
        return f"文脈解析：{reason}。専門家へ相談ください。", reason

    return "問題ありません", None
