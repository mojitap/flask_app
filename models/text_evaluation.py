from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv

# spacy の日本語パーサー（簡易版）
nlp = Japanese()

def normalize_text(text):
    # 全角を半角に変換し、カタカナをひらがなに変換
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    return jaconv.kata2hira(text)

def get_lemmas(text):
    doc = nlp(text)
    return " ".join([token.lemma_ for token in doc])

def evaluate_text(text, offensive_words):
    normalized_text = normalize_text(text)
    norm_offensive_words = [normalize_text(word) for word in offensive_words]

    # 完全一致判定
    for word in norm_offensive_words:
        if word in normalized_text:
            return "この文章は名誉毀損や誹謗中傷に該当する可能性があります。専門家へ相談ください。", word

    # 部分一致判定（RapidFuzz を利用）
    for word in norm_offensive_words:
        if fuzz.partial_ratio(word, normalized_text) >= 80:
            return "一部の表現が問題となる可能性があります。専門家へ相談ください。", word

    # 文脈解析の場合も、必要に応じて同様にメッセージを変更
    # 例：if 文脈解析の結果があれば...
    context_flag, reason = contextual_analysis(text)
    if context_flag:
        return "文脈が攻撃的であるかを判定し、追加の注意喚起を表示。専門家へ相談ください。", reason

    return "問題ありません", None
