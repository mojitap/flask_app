import requests
from bs4 import BeautifulSoup
import time
import csv

# 毎日新聞のトップページURL
url = 'https://mainichi.jp/'

def scrape_mainichi():
    print("毎日新聞のスクレイピングを開始します...")
    try:
        response = requests.get(url)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        articles = soup.find_all('a', href=True)  # すべての<a>タグを対象にする

        # CSVファイルを開く（dataフォルダに保存）
        with open('data/mainichi_articles.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Title", "Content"])  # ヘッダー

            article_links = []
            for article in articles:
                link = article['href']
                # 記事のリンクかどうかを確認する
                if '/articles/' in link:
                    if link.startswith('/'):
                        link = 'https://mainichi.jp' + link
                    article_links.append(link)

            print(f"取得した記事リンク数: {len(article_links)}")

            for link in article_links:
                try:
                    # 記事ページのHTMLを取得
                    article_response = requests.get(link)
                    article_response.encoding = article_response.apparent_encoding
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')

                    # 記事タイトルを取得
                    title_tag = article_soup.find('h1', class_='title-page')  # タイトルのクラス名
                    title = title_tag.get_text().strip() if title_tag else 'タイトルなし'

                    # 記事本文を取得
                    paragraphs = article_soup.find_all('p')  # すべての<p>タグを取得
                    content = ''.join([p.get_text() for p in paragraphs]).strip()

                    # 記事をCSVに保存
                    writer.writerow([title, content])

                    print(f"記事タイトル: {title}")
                    print(f"本文: {content[:100]}...")  # 本文の先頭100文字を表示

                    # リクエスト間に10分の待機時間を設ける
                    time.sleep(600)

                except Exception as e:
                    print(f"記事の取得中にエラーが発生しました: {e}")

        print("毎日新聞のスクレイピングが完了しました。")

    except Exception as e:
        print(f"毎日新聞のスクレイピング中にエラーが発生しました: {e}")

# スクレイピングを実行
scrape_mainichi()
