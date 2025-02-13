# text_evaluation.py
import os
import json
import re

import spacy
from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv

# あなたの環境で苗字をロードする関数（相対 or 絶対インポートに合わせて書き換えてください）
from ..load_surnames import load_surnames

# 簡易キャッシュ（メモリに保存）: テキスト → 判定結果
_eval_cache = {}

# SpaCy の日本語モデルをロード（軽量モデル使用）
nlp = Japanese()

def load_offensive_dict(json_path="offensive_words.json"):
    """
    `offensive_words.json` を辞書としてロード。
    {
      "categories": {
        "insults": [...],
        "defamation": [...],
        "harassment": [...],
        "threats": [...],
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

def flatten_offensive_words(offensive_dict):
    """
    "categories" 下のリスト + "names" リストを全て合体し、単純な1次元リストとして返す。
    例:
      {
        "categories": {
          "insults": [...],
          "defamation": [...],
          ...
        },
        "names": [...]
      }
    """
    all_words = []

    # categories のすべてのリストを合体
    categories = offensive_dict.get("categories", {})
    for _, word_list in categories.items():
        all_words.extend(word_list)

    # "names" も合体したい場合（オフェンシブ扱いするなら）:
    # if "names" in offensive_dict:
    #     all_words.extend(offensive_dict["names"])

    return all_words

def normalize_text(text):
    """
    全角→半角、カタカナ→ひらがな に変換
    """
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    return jaconv.kata2hira(text)

def tokenize_and_lemmatize(text):
    doc = nlp(text)
    return [token.lemma_ for token in doc]

def check_keywords_via_token(text, keywords):
    tokens = tokenize_and_lemmatize(text)
    return any(kw in tokens for kw in keywords)

def check_partial_match(text, word_list, threshold=80):
    """
    文字列ベースの部分一致チェック:
      - 完全に含まれていれば score=100
      - fuzzy(partial_ratio) >= threshold => マッチとみなす
    """
    for w in word_list:
        if w in text:
            return True, w, 100
        score = fuzz.partial_ratio(w, text)
        if score >= threshold:
            return True, w, score
    return False, None, None

def detect_personal_accusation(text):
    pronouns_pattern = r"(お前|こいつ|この人|あなた|アナタ|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_pattern = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン)"
    norm = normalize_text(text)
    pattern = rf"{pronouns_pattern}.*{crime_pattern}|{crime_pattern}.*{pronouns_pattern}"
    return re.search(pattern, norm) is not None

def evaluate_text(text, offensive_dict):
    """
    (判定ラベル, 詳細文字列) を返す
    """
    if text in _eval_cache:
        return _eval_cache[text]

    normalized = normalize_text(text)
    all_offensive = flatten_offensive_words(offensive_dict)

    judgement = "問題ありません"
    detail = ""

    # (1) 部分一致でオフェンシブワード
    found_words = []
    match, w, score = check_partial_match(normalized, all_offensive, threshold=80)
    if match:
        found_words.append((w, score))

    # (2) 苗字チェック
    surnames = load_surnames()
    found_surnames = [sn for sn in surnames if sn in normalized]

    # (3) 個人攻撃 + 犯罪組織
    if detect_personal_accusation(text):
        judgement = "⚠️ 個人攻撃 + 犯罪組織関連の表現あり"
        detail = "detect_personal_accusation が True"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (4) 人名あり + オフェンシブワード
    if found_words and found_surnames:
        judgement = "⚠️ 人名 + オフェンシブワード"
        detail_list = [f"('{fw}',score={sc})" for (fw,sc) in found_words]
        detail = f"苗字={found_surnames}, words={detail_list}"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (5) オフェンシブだけ
    if found_words:
        judgement = "⚠️ 一部の表現が問題の可能性"
        detail_list = [f"('{fw}',score={sc})" for (fw,sc) in found_words]
        detail = f"words={detail_list}"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (6) 暴力表現の例
    violence_keywords = ["殺す","死ね","殴る","蹴る","刺す","轢く","焼く","爆破"]
    if check_keywords_via_token(normalized, violence_keywords):
        judgement = "⚠️ 暴力的表現あり"
        detail = f"tokens in {violence_keywords}"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (7) いじめ/ハラスメントの例
    harassment_kws = ["お前消えろ","存在価値ない","いらない人間","死んだほうがいい","社会のゴミ"]
    if check_keywords_via_token(normalized, harassment_kws):
        judgement = "⚠️ ハラスメント表現あり"
        detail = f"tokens in {harassment_kws}"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # (8) 脅迫など
    threat_kws = ["晒す","特定する","ぶっ壊す","復讐する","燃やす","呪う","報復する"]
    if check_keywords_via_token(normalized, threat_kws):
        judgement = "⚠️ 脅迫表現あり"
        detail = f"tokens in {threat_kws}"
        _eval_cache[text] = (judgement, detail)
        return judgement, detail

    # 何も当てはまらなければ「問題なし」
    _eval_cache[text] = (judgement, detail)
    return judgement, detail

# テスト用サンプル
if __name__ == "__main__":
    offensive_dict = load_offensive_dict("offensive_words.json")

    tests = [
        "山下ってブスだよな",          # 人名+侮辱 => 問題あり
        "山下は政治家",                # 人名のみ => 問題なし
        "ブスだな",                    # 人名なし+オフェンシブ => 問題あり
        "死ね",                        # 暴力的(形態素チェック) => 問題あり
        "お前は詐欺グループとつながってる",  # 個人攻撃+犯罪組織 => 問題あり
        "普通の文章です"               # 問題なし
    ]

    for t in tests:
        res = evaluate_text(t, offensive_dict)
        print(f"入力: {t} => 判定: {res}")
