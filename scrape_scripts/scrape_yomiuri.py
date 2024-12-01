import requests
from bs4 import BeautifulSoup
import csv

# 読売新聞のトップページURL
url = 'https://www.yomiuri.co.jp/'

def scrape_yomiuri():
    print("読売新聞のスクレイピングを開始します...")
    try:
        response = requests.get(url)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        articles = soup.find_all('a', href=True)

        with open('data/yomiuri_articles.csv', mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Title", "Content"])

            article_links = []
            for article in articles:
                link = article['href']
                if '/news/' in link:
                    if link.startswith('/'):
                        link = 'https://www.yomiuri.co.jp' + link
                    article_links.append(link)

            print(f"取得した記事リンク数: {len(article_links)}")

            for link in article_links:
                try:
                    article_response = requests.get(link)
                    article_response.encoding = article_response.apparent_encoding
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')

                    title_tag = article_soup.find('h1', class_='headline')
                    title = title_tag.get_text().strip() if title_tag else 'タイトルなし'

                    paragraphs = article_soup.find_all('p')
                    content = ''.join([p.get_text() for p in paragraphs]).strip()

                    writer.writerow([title, content])

                    print(f"記事タイトル: {title}")
                    print(f"本文: {content[:100]}...")

                    time.sleep(600)

                except Exception as e:
                    print(f"記事の取得中にエラーが発生しました: {e}")

        print("読売新聞のスクレイピングが完了しました。")

    except Exception as e:
        print(f"読売新聞のスクレイピング中にエラーが発生しました: {e}")

# スクレイピングを実行
scrape_yomiuri()
