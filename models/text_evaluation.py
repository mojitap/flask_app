import os
import json
import re

import spacy
from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv

# あなたの環境で苗字をロードする関数
from load_surnames import load_surnames


# ==============================
# 簡易キャッシュ（メモリに保存）
# ==============================
_eval_cache = {}  # { "入力テキスト": "判定結果" }

# ==============================
# SpaCy の日本語モデルをロード
# ==============================
nlp = Japanese()


def load_offensive_dict(json_path="offensive_words.json"):
    """
    `offensive_words.json` を辞書としてロード。
    例:
    {
      "categories": {
        "insults": [...],
        "defamation": [...],
      },
      "names": [...]
    }
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} が見つかりません。")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def flatten_offensive_words(offensive_dict):
    """
    "categories" 下のリスト + "names" リストを全て合体し、
    単純な1次元リストとして返す。
    """
    all_words = []

    categories = offensive_dict.get("categories", {})
    for cat_name, word_list in categories.items():
        all_words.extend(word_list)

    if "names" in offensive_dict:
        all_words.extend(offensive_dict["names"])

    return all_words


def normalize_text(text):
    """
    全角→半角、カタカナ→ひらがな、などの正規化。
    """
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    text = jaconv.kata2hira(text)
    return text


def tokenize_and_lemmatize(text):
    """
    形態素解析してトークンの原形リストを返す。
    """
    doc = nlp(text)
    return [token.lemma_ for token in doc]


def check_partial_match(text, word_list, threshold=75):
    """
    文字列ベースの部分一致チェック。
    - 完全に含まれていれば score=100
    - fuzzy マッチングが threshold 以上ならヒット
    """
    for w in word_list:
        if w in text:
            return True, w, 100
        score = fuzz.partial_ratio(w, text)
        if score >= threshold:
            return True, w, score
    return False, None, None


def check_keywords_via_token(text, keywords):
    """
    形態素解析で分割したトークン列に keywords が含まれているか判定。
    """
    tokens = tokenize_and_lemmatize(text)
    return any(kw in tokens for kw in keywords)


def detect_personal_accusation(text):
    """
    対象となる代名詞 + 犯罪組織に関連する語句の同時出現を検出。
    例: 「お前、詐欺グループとつながってるんじゃないか」
    """
    pronouns_pattern = r"(お前|こいつ|この人|あなた|アナタ|このひと|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_words_pattern = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン|マネーロンダリング)"

    # 正規化してから正規表現で検索
    norm = normalize_text(text)
    pattern = rf"{pronouns_pattern}.*{crime_words_pattern}|{crime_words_pattern}.*{pronouns_pattern}"
    # 代名詞→犯罪ワード or 犯罪ワード→代名詞 の順で出現するパターン
    if re.search(pattern, norm):
        return True
    return False


def evaluate_text(text, offensive_dict):
    """
    メインのテキスト評価関数
    """

    # ===== キャッシュチェック =====
    # 同じテキストなら即返却
    if text in _eval_cache:
        return _eval_cache[text]

    # 1) 正規化
    normalized_text = normalize_text(text)

    # 2) オフェンシブワードをフラットリスト化
    all_offensive_words = flatten_offensive_words(offensive_dict)

    # 3) 部分一致チェック（文字列ベース）
    found_words = []
    for w in all_offensive_words:
        match, matched_word, score = check_partial_match(normalized_text, [w])
        if match:
            found_words.append(matched_word)

    # 4) 人名（苗字）チェック
    surnames = load_surnames()  # あなたの既存実装が読み込む想定
    found_surnames = [sn for sn in surnames if sn in normalized_text]

    # 5) detect_personal_accusation のチェック
    if detect_personal_accusation(text):
        # 代名詞 + 犯罪組織 があった場合の専用判定を入れてもいい
        # ここでは例示的に返すだけ
        _eval_cache[text] = "⚠️ 個人攻撃や犯罪組織関連の表現が含まれている可能性があります"
        return _eval_cache[text]

    # 6) 人名 + オフェンシブワード の組み合わせ
    if found_words and found_surnames:
        result = "⚠️ この文章には問題のある表現と特定の苗字が含まれています"
        _eval_cache[text] = result
        return result

    # 7) 形態素解析で暴力・ハラスメント・脅迫などを軽くチェック
    violence_keywords = ["殺す", "死ぬ", "殴る", "蹴る", "刺す", "轢く", "焼く", "爆破"]
    if check_keywords_via_token(normalized_text, violence_keywords):
        _eval_cache[text] = "⚠️ 暴力的な表現が含まれています"
        return _eval_cache[text]

    harassment_keywords = ["お前消えろ", "存在価値ない", "いらない人間", "死んだほうがいい", "社会のゴミ"]
    if check_keywords_via_token(normalized_text, harassment_keywords):
        _eval_cache[text] = "⚠️ いじめ・ハラスメントの可能性があります"
        return _eval_cache[text]

    threat_keywords = ["晒す", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"]
    if check_keywords_via_token(normalized_text, threat_keywords):
        _eval_cache[text] = "⚠️ 脅迫・犯罪関連の表現が含まれています"
        return _eval_cache[text]

    # 8) 完全一致 or 部分一致で「一部の表現が問題の可能性」 
    #   => 形態素解析ベースではなく文字列ベースで実施
    #   => 例として "もし何かしらの単語がヒットしたら" という簡易チェック
    if found_words:
        result = "⚠️ 一部の表現が問題となる可能性があります"
        _eval_cache[text] = result
        return result

    # 何も当てはまらない → 問題なし
    _eval_cache[text] = "問題ありません"
    return _eval_cache[text]


if __name__ == "__main__":
    # テスト例
    offensive_dict = load_offensive_dict("offensive_words.json")

    test_inputs = [
        "山下ってブスだよな",
        "あいつは過去に補導されたことあるらしい",
        "お前は詐欺グループとつながってるんだろ？",
        "黙れクズ",
        "何も問題のない文章です",
    ]

    for ti in test_inputs:
        print(f"入力: {ti}")
        result = evaluate_text(ti, offensive_dict)
        print(f"判定: {result}")
        print("----")
