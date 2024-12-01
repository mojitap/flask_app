import os
import re

# フォルダパス
folder = '/Users/macuser/Desktop/flask_app/pdfs_human_rights'

# 「?」をすべて削除する関数
def remove_question_marks(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            # 全ての「?」を削除し、連続するアンダーバーも整える
            new_filename = re.sub(r'\?+', '', filename)  # すべての「?」と「??」を削除
            new_filename = re.sub(r'_{2,}', '_', new_filename)  # 連続アンダーバーを1つにまとめる
            new_file_path = os.path.join(folder, new_filename)
            # ファイル名が変更された場合のみリネーム
            if file_path != new_file_path:
                os.rename(file_path, new_file_path)
                print(f'Renamed: {filename} -> {new_filename}')

# 実行
remove_question_marks(folder)

# スクリプトのループ内
for filename in os.listdir(folder):
    print(f'Checking: {filename}')  # 各ファイルの確認用メッセージ
    ...
