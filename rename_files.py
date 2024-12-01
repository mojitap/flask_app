import os
import re

def clean_filenames(folder_path):
    for filename in os.listdir(folder_path):
        if '_?_?' in filename or '?' in filename:
            print(f'Found file: {filename}')  # 確認用の出力
clean_filenames('/Users/macuser/Desktop/flask_app/pdfs_defamation')
