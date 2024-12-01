import os
import re

# フォルダパスを指定
folder = '/Users/macuser/Desktop/flask_app/pdfs_defamation'

# ファイル名の改行・スペースを削除
def rename_files_in_folder(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            # 改行とスペースを削除
            new_filename = re.sub(r'[\n\s]+', '', filename)
            new_file_path = os.path.join(folder, new_filename)
            if new_filename != filename:
                os.rename(file_path, new_file_path)
                print(f'Renamed: {filename} -> {new_filename}')

# 実行
rename_files_in_folder(folder)
