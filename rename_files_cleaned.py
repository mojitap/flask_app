import os
import re

# 各フォルダとそれに対応するプレフィックス
folders = {
    '/Users/macuser/Desktop/flask_app/pdfs_defamation': '21',
    '/Users/macuser/Desktop/flask_app/pdfs_human_rights': '11'
}

def rename_files_in_folder(folder, prefix):
    print(f"処理中のフォルダ: {folder}")
    for filename in os.listdir(folder):
        print(f"見つかったファイル: {filename}")
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path) and not filename.startswith('.'):
            # 特殊文字を削除し、プレフィックスの重複を防ぐ
            new_filename = re.sub(r'[^\w\s-]', '', filename)  # 特殊文字（例: `?`）を削除
            new_filename = re.sub(r'_{2,}', '_', new_filename)  # 複数のアンダースコアを1つに
            new_filename = new_filename.lstrip('_')  # 先頭のアンダースコアを削除
            if not new_filename.startswith(prefix):  # プレフィックスの重複を防止
                new_filename = f"{prefix}_{new_filename}"
            
            new_file_path = os.path.join(folder, new_filename)
            os.rename(file_path, new_file_path)
            print(f'リネーム完了: {filename} -> {new_filename}')

# 各フォルダにリネーム関数を適用
for folder, prefix in folders.items():
    rename_files_in_folder(folder, prefix)
