import os
import json

SURNAMES_FOLDER = os.path.join(os.path.dirname(__file__), "surnames_split")
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "offensive_words.json")

def load_surnames():
    surnames = set()
    for filename in os.listdir(SURNAMES_FOLDER):
        if filename.endswith(".json"):
            with open(os.path.join(SURNAMES_FOLDER, filename), "r", encoding="utf-8") as f:
                data_list = json.load(f)  # JSON配列をロード
                for name in data_list:
                    # 不要な見出し "な行" などが入っていれば除外する処理をする
                    if "行" in name:
                        continue
                    surnames.add(name.strip())
    return list(surnames)

def update_offensive_words():
    # 既存の offensive_words を読み込む
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            offensive_words = json.load(f)
    except FileNotFoundError:
        offensive_words = {"categories": {}, "names": []}

    # 人名データを取得
    surnames = load_surnames()  # あ行、か行…わ行 すべて読み込む

    # "names" キーがなければ作る
    if "names" not in offensive_words:
        offensive_words["names"] = []

    # surnames を "names" に追加（重複チェック）
    for name in surnames:
        if name not in offensive_words["names"]:
            offensive_words["names"].append(name)

    # 更新したデータを書き込み
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(offensive_words, f, indent=4, ensure_ascii=False)

    print(f"✅ `offensive_words.json` に {len(surnames)} 件の人名を追加しました！")
