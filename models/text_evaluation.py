from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv

nlp = Japanese()

def normalize_text(text):
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    return jaconv.kata2hira(text)

def get_lemmas(text):
    doc = nlp(text)
    return " ".join([token.lemma_ for token in doc])

def evaluate_text(text, offensive_words):
    normalized_text = normalize_text(text)
    norm_offensive_words = [normalize_text(word) for word in offensive_words]

    for word in norm_offensive_words:
        if word in normalized_text:
            return "この文章は名誉毀損や誹謗中傷に該当する可能性があります。", word

    for word in norm_offensive_words:
        if fuzz.partial_ratio(word, normalized_text) >= 80:
            return "一部の表現が問題となる可能性があります。", word

    return "問題ありません", None