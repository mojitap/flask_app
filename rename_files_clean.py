import os
import re

# 対象フォルダのリスト
folders = [
    '/Users/macuser/Desktop/flask_app/pdfs_defamation',
    '/Users/macuser/Desktop/flask_app/data/pdfs_defamation',
    '/Users/macuser/Desktop/flask_app/pdfs_human_rights',
    '/Users/macuser/Desktop/flask_app/pdfs_business_obstruction'
]

# ファイル名の変換処理
def rename_files_in_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            # 特殊文字 (?や_) を削除し、先頭のアンダーバーも取り除く
            new_filename = re.sub(r'[^\w\s-]', '', filename)  # 特殊文字を削除
            new_filename = re.sub(r'_{2,}', '_', new_filename)  # 連続アンダーバーを1つに
            new_filename = new_filename.lstrip('_')  # 先頭のアンダーバーを削除
            new_file_path = os.path.join(folder, new_filename)
            os.rename(file_path, new_file_path)
            print(f'Renamed: {filename} -> {new_filename}')

# 各フォルダでファイル名を変換
for folder in folders:
    rename_files_in_folder(folder)
