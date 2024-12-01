import requests
from bs4 import BeautifulSoup

# 判例検索システムのURLにアクセス（例として架空のURLを使用）
url = "https://www.courts.go.jp/app/hanrei_jp/search1"
response = requests.get(url)

# BeautifulSoupでページのHTMLを解析
soup = BeautifulSoup(response.text, 'html.parser')

# 判例のテキスト部分を抽出（適切なタグやクラスを指定）
case_texts = soup.find_all('div', class_='case-text')

# 抽出された判例テキストを表示
for case_text in case_texts:
    print(case_text.get_text())
