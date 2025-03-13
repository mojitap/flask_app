# text_evaluation.py
import os
import json
import re

from collections import OrderedDict  # キャッシュ管理用
from functools import lru_cache
import spacy
from spacy.lang.ja import Japanese
from rapidfuzz import fuzz
import jaconv

# あなたの環境で苗字をロードする関数（相対 or 絶対インポートに合わせて調整してください）
from .load_surnames import load_surnames

# 形態素解析のキャッシュ
nlp = spacy.load("ja_core_news_sm")

@lru_cache(maxsize=1000)
def cached_tokenize(text: str):
    """
    spaCy で形態素解析して lemma を返す。キャッシュ付き。
    """
    doc = nlp(text)
    return [token.lemma_ for token in doc]

# 簡易キャッシュ（メモリに保存）: テキスト → 判定結果
_eval_cache = {}


# =====================================================
# 1) offensive_words.json をロード → 形態素解析
# =====================================================
def load_offensive_dict_with_tokens(json_path="offensive_words.json"):
    """
    1) JSON をロード
    2) "offensive" キーのリストを取り出し
    3) 各ワードをトークン化
    4) [{"original": w, "norm": w_norm, "tokens": [...]}] を返す
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} が見つかりません。")

    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    words = raw_data.get("offensive", [])  # "offensive"キーが無ければ空
    results = []
    for w in words:
        w_norm = normalize_text(w)
        w_tokens = tokenize_and_lemmatize(w_norm)
        results.append({
            "original": w,
            "norm": w_norm,
            "tokens": w_tokens
        })
    return results

# =====================================================
# 2) whitelist.json のロード
# =====================================================
def load_whitelist(json_path="data/whitelist.json"):
    """
    ["ありがとう", "愛してる", ...] のように配列形式を想定 → set(...) へ
    """
    if not os.path.exists(json_path):
        print(f"⚠️ {json_path} が見つかりません。ホワイトリストは空です。")
        return set()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # data は配列想定
    return set(data)
    
# =====================================================
# 3) 個別のロジック（個人攻撃 + 犯罪組織）
# =====================================================
def detect_personal_accusation(text: str) -> bool:
    """
    「お前 × 詐欺グループ」など個人攻撃 + 犯罪組織の簡易検出
    """
    pronouns_pattern = r"(お前|こいつ|この人|あなた|アナタ|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_pattern = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン)"
    norm = normalize_text(text)
    pattern = rf"{pronouns_pattern}.*{crime_pattern}|{crime_pattern}.*{pronouns_pattern}"
    return bool(re.search(pattern, norm))

# =====================================================
# 4) メインの判定
# =====================================================
_eval_cache = {}

@lru_cache(maxsize=1000)
def evaluate_text(
    text: str,
    offensive_list: list,  # [{"original":..., "norm":..., "tokens":[...]}]
    whitelist: set = None
):
    """
    :param text: 入力文字列
    :param offensive_list: 形態素解析済み辞書
    :param whitelist: {"ありがとう", "愛してる", ...} のようなセット
    :return: (判定, detail)
    """
    if whitelist is None:
        whitelist = set()

    # 既に判定済みならキャッシュから返す
    if text in _eval_cache:
        return _eval_cache[text]

    print(f"[DEBUG] evaluate_text called with text='{text}'")

    # A) 入力テキストを形態素解析
    input_norm = normalize_text(text)
    input_tokens = tokenize_and_lemmatize(input_norm)

    # B) offensive_list 判定
    found_offensive = []
    for item in offensive_list:
        dict_original = item["original"]
        dict_norm = item["norm"]
        dict_tokens = item["tokens"]

        # tokens ⊆ input_tokens ?
        if set(dict_tokens).issubset(set(input_tokens)):
            # ホワイトリストチェック
            if dict_original in whitelist or dict_norm in whitelist:
                print(f"✅ ホワイトリスト除外: {dict_original}")
                continue
            found_offensive.append(dict_original)

    # C) 個人攻撃 + 犯罪組織
    if detect_personal_accusation(text):
        judgement = "⚠️ 個人攻撃 + 犯罪組織関連の表現あり"
        detail = "※この判定は約束できるものではありません。専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    # D) offensive_list にヒットした場合
    if found_offensive:
        judgement = "⚠️ 一部の表現が問題の可能性"
        detail = f"辞書ヒット: {', '.join(found_offensive)}\n※専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    # E) 以下、暴力・ハラスメント・脅迫などを substring/fuzzy で判定
    # --------------------------------------------------
    violence_keywords = ["殺す", "死ね", "殴る", "蹴る", "刺す", "轢く", "焼く", "爆破", "死んでしまえ"]
    if any(kw in input_norm for kw in violence_keywords) \
       or any(fuzz.partial_ratio(kw, input_norm) >= 60 for kw in violence_keywords):
        judgement = "⚠️ 暴力的表現あり"
        detail = "※専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    harassment_kws = ["お前消えろ", "存在価値ない", "いらない人間", "死んだほうがいい", "社会のゴミ"]
    if any(kw in input_norm for kw in harassment_kws) \
       or any(fuzz.partial_ratio(kw, input_norm) >= 60 for kw in harassment_kws):
        judgement = "⚠️ ハラスメント表現あり"
        detail = "※専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    threat_kws = ["晒す", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"]
    if any(kw in input_norm for kw in threat_kws) \
       or any(fuzz.partial_ratio(kw, input_norm) >= 60 for kw in threat_kws):
        judgement = "⚠️ 脅迫表現あり"
        detail = "※専門家にご相談ください。"
        _eval_cache[text] = (judgement, detail)
        return (judgement, detail)

    # F) 問題なし
    _eval_cache[text] = ("問題ありません", "")
    return ("問題ありません", "")

# =====================================================
# 5) テスト実行
# =====================================================
if __name__ == "__main__":
    from pathlib import Path

    # 例: python text_evaluation.py
    # A) offensive_list
    offensive_list = load_offensive_dict_with_tokens("offensive_words.json")
    # B) whitelist
    wl = load_whitelist("data/whitelist.json")

    tests = [
        "山下ってブスだよな",          # 問題あり(辞書にブスがあれば)
        "ブスだな",                    # 問題あり(同上)
        "愛してる",                    # ホワイトリストにあれば除外
        "ありがとう",                  # 同上
        "死ね",                        # 暴力表現
        "殴ってやる",                 # 暴力表現
        "お前消えろ",                  # ハラスメント
        "お前は詐欺グループとつながってる",  # 個人攻撃 + 犯罪組織
        "普通の文章です"               # 問題なし
    ]
    for t in tests:
        j, d = evaluate_text(t, offensive_list, wl)
        print(f"[TEST] {t} => {j} / {d}")
