import os
import re

# 対象フォルダとプレフィックスを指定
folder_path = '/Users/macuser/Desktop/flask_app/pdfs_human_rights'
prefix = '11'

# ファイル名の変換処理
def clean_filenames_in_human_rights():
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            # ファイルの確認用メッセージ
            print(f'Checking: {filename}')
            
            # 特殊文字「?」「??」を削除
            new_filename = re.sub(r'\?+', '', filename)
            # プレフィックスが重複する場合は、最初のプレフィックスだけを残す
            new_filename = re.sub(r'(^' + re.escape(prefix) + r'_)+', f'{prefix}_', new_filename)
            # 新しいファイル名に変更
            new_file_path = os.path.join(folder_path, new_filename)
            
            if file_path != new_file_path:
                os.rename(file_path, new_file_path)
                print(f'Renamed: {filename} -> {new_filename}')
            else:
                print(f'No change for: {filename}')

# 関数を実行
clean_filenames_in_human_rights()
