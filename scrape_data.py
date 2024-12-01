import requests
from bs4 import BeautifulSoup
import time
import csv

# 朝日新聞のトピックページURL
url = 'https://www.asahi.com/topics/'

# ウェブページのHTMLを取得
response = requests.get(url)
response.encoding = response.apparent_encoding

# BeautifulSoupでHTMLを解析
soup = BeautifulSoup(response.text, 'html.parser')

# 記事のリンクを抽出する
articles = soup.find_all('a')  # より多くのリンクを抽出するために<a>タグを取得

# CSVファイルを開く
with open('articles.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Title", "Content"])  # ヘッダー

    # 記事リンクを処理
    article_links = []
    for article in articles:
        a_tag = article.get('href')
        if a_tag and '/articles/' in a_tag:  # 記事リンクをフィルタ
            if a_tag.startswith('/'):
                link = 'https://www.asahi.com' + a_tag
            else:
                link = a_tag
            article_links.append(link)
    
    print(f"取得した記事リンク数: {len(article_links)}")

    for link in article_links:
        try:
            # 記事ページのHTMLを取得
            article_response = requests.get(link)
            article_response.encoding = article_response.apparent_encoding
            article_soup = BeautifulSoup(article_response.text, 'html.parser')

            # 記事タイトルを取得
            title_tag = article_soup.find('h1')
            title = title_tag.get_text().strip() if title_tag else 'タイトルなし'

            # 記事本文を取得
            paragraphs = article_soup.find_all('p')
            content = ''.join([p.get_text() for p in paragraphs]).strip()

            # 記事をCSVに保存
            writer.writerow([title, content])

            print(f"記事タイトル: {title}")
            print(f"本文: {content}\n")

            # リクエスト間に待機時間を設ける
            time.sleep(1)

        except Exception as e:
            print(f"記事の取得中にエラーが発生しました: {e}")
