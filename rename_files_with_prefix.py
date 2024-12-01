import os
import re

# 各フォルダとそのプレフィックス番号を指定
folders = {
    '/Users/macuser/Desktop/flask_app/pdfs_defamation': '21',
    '/Users/macuser/Desktop/flask_app/data/pdfs_defamation': '41',
    '/Users/macuser/Desktop/flask_app/pdfs_human_rights': '11',
    '/Users/macuser/Desktop/flask_app/pdfs_business_obstruction': '31'
}

# ファイル名の変換処理
def rename_files_in_folder(folder, prefix):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            # 特殊文字と連続アンダーバーを削除し、先頭のアンダーバーを取り除く
            new_filename = re.sub(r'[^\w\s-]', '', filename)  # 特殊文字を削除
            new_filename = re.sub(r'_{2,}', '_', new_filename)  # 連続アンダーバーを1つに
            new_filename = new_filename.lstrip('_')  # 先頭のアンダーバーを削除
            # プレフィックスを追加して新しいファイル名に変更
            new_filename = f"{prefix}_{new_filename}"
            new_file_path = os.path.join(folder, new_filename)
            os.rename(file_path, new_file_path)
            print(f'Renamed: {filename} -> {new_filename}')

# 各フォルダのファイルをリネーム
for folder, prefix in folders.items():
    rename_files_in_folder(folder, prefix)
