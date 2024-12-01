import os
import re

# フォルダパスとプレフィックス
folder_path = '/Users/macuser/Desktop/flask_app/pdfs_human_rights'
prefix = '11'

# ファイル名の変換処理
def clean_filenames_in_human_rights():
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            print(f'Checking: {filename}')
            
            # 「?」や「??」を削除し、スペースも削除
            new_filename = re.sub(r'\?+', '', filename)  # 「?」や「??」を削除
            new_filename = re.sub(r'\s+', '', new_filename)  # スペースを削除
            new_filename = re.sub(r'(^' + re.escape(prefix) + r'_)+', f'{prefix}_', new_filename)  # プレフィックスの重複を整理
            
            # ファイルの拡張子が存在しない場合は .pdf を追加
            if not new_filename.endswith('.pdf'):
                new_filename += '.pdf'
            
            # 新しいファイル名へのパスを生成
            new_file_path = os.path.join(folder_path, new_filename)
            
            # ファイルの名前が変更された場合にのみリネームを実行
            if file_path != new_file_path:
                os.rename(file_path, new_file_path)
                print(f'Renamed: {filename} -> {new_filename}')
            else:
                print(f'No change for: {filename}')

# 関数を実行
clean_filenames_in_human_rights()
