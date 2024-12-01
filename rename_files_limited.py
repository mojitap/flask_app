import os
import re

folders = {
    '/Users/macuser/Desktop/flask_app/pdfs_defamation': '21',
    '/Users/macuser/Desktop/flask_app/pdfs_human_rights': '11'
}

def rename_files_in_folder(folder, prefix):
    print(f"Processing folder: {folder}")  # フォルダ名の表示
    for filename in os.listdir(folder):
        print(f"Found file: {filename}")  # 各ファイル名を表示
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path) and not filename.startswith('.'):
            if not filename.startswith(prefix):
                new_filename = re.sub(r'[^\w\s-]', '', filename)  # 特殊文字削除
                new_filename = re.sub(r'_{2,}', '_', new_filename)  # 連続アンダースコアを1つに
                new_filename = new_filename.lstrip('_')  # 先頭のアンダースコアを削除
                new_filename = f"{prefix}_{new_filename}"  # プレフィックス追加
                new_file_path = os.path.join(folder, new_filename)
                os.rename(file_path, new_file_path)
                print(f'Renamed: {filename} -> {new_filename}')

for folder, prefix in folders.items():
    rename_files_in_folder(folder, prefix)
