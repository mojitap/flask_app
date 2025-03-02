import os
import json
import re
from functools import lru_cache
import spacy
from rapidfuzz import fuzz
import jaconv
import glob

# Dropbox側のファイルパス（必要に応じて修正）
WHITELIST_PATH = "/path/to/dropbox/whitelist.json"
OFFENSIVE_WORDS_PATH = "/path/to/dropbox/offensive_words.json"
SURNAMES_SPLIT_DIR = "/path/to/dropbox/surnames_split/"

# GitHub上に直接登録している直接チェック用のリスト（例）
DIRECT_VIOLENCE_KWS = ["殺す", "死ね", "殴る", "蹴る", "刺す", "轢く", "焼く", "爆破"]
DIRECT_HARASSMENT_KWS = ["お前消えろ", "存在価値ない", "いらない人間", "死んだほうがいい", "社会のゴミ"]
DIRECT_THREAT_KWS = ["晒す", "特定する", "ぶっ壊す", "復讐する", "燃やす", "呪う", "報復する"]

# spaCy の日本語モデルのロード（1回だけ）
nlp = spacy.load("ja_core_news_sm")

@lru_cache(maxsize=1000)
def cached_tokenize(text):
    """
    spaCy を使ってテキストを形態素解析し、基本形（lemma）のリストを返す
    """
    doc = nlp(text)
    return [token.lemma_ for token in doc]

def tokenize_text(text):
    """
    入力テキストを正規化してから形態素解析を実行し、トークンのリストを返す
    """
    normalized = normalize_text(text)
    return cached_tokenize(normalized)

def normalize_text(text):
    """
    全角→半角、カタカナ→ひらがなに変換する
    """
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    return jaconv.kata2hira(text)

# シンプルなキャッシュ：テキスト -> 判定結果
_eval_cache = {}

def load_offensive_words(json_path=OFFENSIVE_WORDS_PATH):
    """
    offensive_words.json を単一の offensive ワードのリストとして読み込む。
    JSON例:
    {
      "offensive": ["被害者ズラ", "好きじゃない", "バカ", "クズ", "ダサいのに気づいてないの？"]
    }
    または単にリストそのものでも可。
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"{json_path} が見つかりません。")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data.get("offensive", [])
    return data

def load_whitelist(json_path=WHITELIST_PATH):
    """
    whitelist.json を読み込み、set を返す。
    例: ["ありがとう", "愛してる", ...]
    """
    if not os.path.exists(json_path):
        print(f"⚠️ {json_path} が見つかりません。ホワイトリストは空です。")
        return set()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return set(data)

def load_surnames():
    """
    surnames_split フォルダ内のすべてのテキストファイルから苗字を読み込み、1次元リストとして返す。
    """
    surname_list = []
    pattern = os.path.join(SURNAMES_SPLIT_DIR, "*.txt")
    for file in glob.glob(pattern):
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    surname_list.append(line)
    return surname_list

def check_direct_keywords(normalized_text, keywords):
    """
    GitHub に直接登録しているキーワードについて、単純部分一致でチェックする。
    """
    for kw in keywords:
        if kw in normalized_text:
            return True, kw
    return False, None

def evaluate_keywords(normalized_text, tokenized_text, keywords, threshold=80):
    """
    offensive ワードリスト (keywords) について、入力テキスト（正規化済み・トークン化済み）と比較する。
    完全一致の場合はスコア100、部分一致なら fuzzy マッチ（fuzz.partial_ratio）でスコアを計算する。
    最大スコアが threshold 以上なら (True, 該当ワード, スコア) を返す。
    """
    max_score = 0
    matched_keyword = None
    for kw in keywords:
        kw_norm = normalize_text(kw)
        if kw_norm in normalized_text:
            score = 100
        else:
            # トークン列をスペース区切りの文字列にして fuzzy 比較
            score = fuzz.partial_ratio(kw_norm, tokenized_text)
        if score > max_score:
            max_score = score
            matched_keyword = kw
    if max_score >= threshold:
        return True, matched_keyword, max_score
    return False, None, None

def detect_personal_accusation(normalized_text):
    """
    個人攻撃＋犯罪組織に関する表現を正規表現で検出する
    """
    pronouns_pattern = r"(お前|こいつ|この人|あなた|アナタ|あいつ|あんた|アンタ|おまえ|オマエ|コイツ|てめー|テメー|アイツ)"
    crime_pattern = r"(反社|暴力団|詐欺団体|詐欺グループ|犯罪組織|闇組織|マネロン)"
    pattern = rf"{pronouns_pattern}.*{crime_pattern}|{crime_pattern}.*{pronouns_pattern}"
    return re.search(pattern, normalized_text) is not None

def evaluate_text(text, offensive_list, whitelist=None):
    """
    offensive_list は offensive ワードの単一リストを前提とする。
    GitHub の直接登録キーワード、offensive_list、苗字チェック、個人攻撃＋犯罪組織チェックを行い、
    最も高いスコアの判定結果を返す。
    """
    if whitelist is None:
        whitelist = load_whitelist()
    if text in _eval_cache:
        return _eval_cache[text]
    if len(_eval_cache) > 1000:
        _eval_cache.popitem(last=False)

    # 正規化と形態素解析（トークン化）
    normalized = normalize_text(text)
    tokens = tokenize_text(text)
    tokenized_text = " ".join(tokens)

    results = []

    # (A) GitHub 直接登録キーワードチェック（完全一致または単純部分一致）
    for kw_list, msg in [(DIRECT_VIOLENCE_KWS, "暴力的表現"),
                         (DIRECT_HARASSMENT_KWS, "ハラスメント表現"),
                         (DIRECT_THREAT_KWS, "脅迫表現")]:
        hit, kw = check_direct_keywords(normalized, kw_list)
        if hit:
            results.append({
                "judgement": f"⚠️ {msg}あり（直接登録キーワード: {kw}）",
                "detail": "※この判定は約束できるものではありません。専門家にご相談ください。",
                "score": 100
            })

    # (B) offensive_list のチェック（ホワイトリスト除外後、fuzzy マッチ）
    filtered_offensive = [kw for kw in offensive_list if kw not in whitelist]
    hit, matched_kw, score = evaluate_keywords(normalized, tokenized_text, filtered_offensive, threshold=80)
    if hit:
        results.append({
            "judgement": "⚠️ 一部の表現が問題となる可能性があります。",
            "detail": f"※該当ワード: {matched_kw} （スコア: {score}）\n※この判定は約束できるものではありません。専門家にご相談ください。",
            "score": score
        })

    # (C) 苗字チェック（苗字が含まれている場合、offensive_list との組み合わせもチェック）
    surnames = load_surnames()
    found_surnames = [sn for sn in surnames if sn in normalized]
    if found_surnames:
        hit, matched_kw, score = evaluate_keywords(normalized, tokenized_text, filtered_offensive, threshold=80)
        if hit:
            results.append({
                "judgement": "⚠️ 人名と offensive ワードの組み合わせが検出されました。",
                "detail": f"※該当ワード: {matched_kw} （スコア: {score}）\n※この判定は約束できるものではありません。専門家にご相談ください。",
                "score": score
            })

    # (D) 個人攻撃＋犯罪組織の表現チェック（正規表現）
    if detect_personal_accusation(normalized):
        results.append({
            "judgement": "⚠️ 個人攻撃＋犯罪組織関連の表現あり",
            "detail": "※この判定は約束できるものではありません。専門家にご相談ください。",
            "score": 100
        })

    if results:
        final_result = max(results, key=lambda x: x["score"])
        _eval_cache[text] = (final_result["judgement"], final_result["detail"])
        return final_result["judgement"], final_result["detail"]

    judgement = "問題ありません"
    detail = ""
    _eval_cache[text] = (judgement, detail)
    return judgement, detail

# テスト用サンプル
if __name__ == "__main__":
    offensive_list = load_offensive_words(OFFENSIVE_WORDS_PATH)
    tests = [
        "山下ってブスだよな",           # GitHub 側（直接的な人名+侮辱）
        "山下は政治家",                 # 人名のみ → 問題なし
        "ブスだな",                     # offensive_list による判定 → 問題あり（部分一致）
        "死ね",                         # 直接登録の violence キーワード → 問題あり
        "お前は詐欺グループとつながってる",   # 個人攻撃＋犯罪組織 → 問題あり
        "普通の文章です"                # 問題なし
    ]
    for t in tests:
        judgement, detail = evaluate_text(t, offensive_list)
        print(f"入力: {t}\n判定: {judgement}\n詳細: {detail}\n")
