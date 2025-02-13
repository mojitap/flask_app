import os
import json

SURNAMES_FOLDER = os.path.join(os.path.dirname(__file__), "surnames_split")
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "offensive_words.json")

def load_surnames():
    """surnames_split/ フォルダ内の人名リストを読み込む"""
    surnames = set()
    for filename in os.listdir(SURNAMES_FOLDER):
        if filename.endswith(".json"):  # .json ファイルを対象にする
            with open(os.path.join(SURNAMES_FOLDER, filename), "r", encoding="utf-8") as f:
                for line in f:
                    surnames.add(line.strip())  # 空白を除去してセットに追加
    return list(surnames)

def update_offensive_words():
    """offensive_words.json に surnames_split のデータを統合する"""
    # 既存の offensive_words を読み込む
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            offensive_words = json.load(f)
    except FileNotFoundError:
        offensive_words = []  # ファイルがなければ新規作成

    # 人名データを取得
    surnames = load_surnames()

    # 統合（重複チェックあり）
    if "names" not in offensive_words:
    offensive_words["names"] = []  # "names" キーがない場合、追加

    for name in surnames:
        if name not in offensive_words["names"]:
            offensive_words["names"].append(name)

    # 更新したデータを書き込み
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(offensive_words, f, indent=4, ensure_ascii=False)

    print(f"✅ `offensive_words.json` に {len(surnames)} 件の人名を追加しました！")
