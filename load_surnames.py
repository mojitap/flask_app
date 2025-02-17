import csv
import os

# CSVファイルのパスを指定
csv_file_path = os.path.join(os.path.dirname(__file__), "surnames.csv")

def load_surnames():
    """CSVファイルから苗字リストを読み込む関数"""
    surnames = []
    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            for row in reader:
                if row and row[0].strip():  # 空行や空白行を無視
                    surnames.append(row[0].strip())
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    return surnames

# テスト用コード
if __name__ == "__main__":
    surnames = load_surnames()
    print(f"読み込んだ苗字数: {len(surnames)}")
    print(surnames[:10])  # 最初の10件を表示