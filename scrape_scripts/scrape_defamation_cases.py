import requests
from bs4 import BeautifulSoup
import csv
import os
import time
import pdfplumber
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# PDFを保存するフォルダを作成（新しいフォルダパスに変更）
pdf_folder = 'pdfs_defamation'
if not os.path.exists(pdf_folder):
    os.makedirs(pdf_folder)

# ベースURL
base_url = 'https://www.courts.go.jp'

# requestsセッションを作成
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# CSVファイルのパスを指定（dataフォルダに保存）
csv_file = 'data/court_cases_defamation.csv'
with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["Title", "Date", "PDF Link", "Text Content"])

# 判例情報を取得する関数
def fetch_case_details(case):
    try:
        title_tag = case.find('a')
        title = title_tag.get_text().strip() if title_tag else 'タイトルなし'
        link = base_url + title_tag['href'] if title_tag else 'リンクなし'

        # 日付を取得
        date_tag = case.find_next('td')
        date = date_tag.get_text().strip() if date_tag else '日付なし'

        # PDFリンクの取得
        pdf_link_tag = case.find_next('a', string='全文')
        pdf_link = base_url + pdf_link_tag['href'] if pdf_link_tag else 'PDFリンクなし'
        pdf_text = 'PDF内容なし'

        # PDFをダウンロードして保存
        if pdf_link != 'PDFリンクなし':
            pdf_response = session.get(pdf_link)
            sanitized_title = title.replace("/", "_").replace(" ", "_")
            pdf_filename = os.path.join(pdf_folder, f'{sanitized_title}.pdf')

            # PDFを保存
            with open(pdf_filename, 'wb') as pdf_file:
                pdf_file.write(pdf_response.content)

            # PDFからテキストを抽出
            try:
                with pdfplumber.open(pdf_filename) as pdf:
                    pdf_text = ''
                    for page in pdf.pages:
                        pdf_text += page.extract_text()
                print(f"PDFからテキストを抽出: {pdf_text[:100]}...")

            except Exception as e:
                print(f"PDFの解析中にエラーが発生しました: {e}")
                pdf_text = 'テキスト抽出エラー'

        return [title, date, pdf_link, pdf_text]

    except Exception as e:
        print(f"判例の取得中にエラーが発生しました: {e}")
        return ['エラー', 'エラー', 'エラー', 'エラー']

# 検索結果ページをスクレイプする関数
def scrape_page(url):
    try:
        response = session.get(url)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')

        cases = soup.find_all('th', scope='row')
        print(f"取得した判例数: {len(cases)}")

        for case in cases:
            case_details = fetch_case_details(case)

            with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(case_details)

            # 各判例処理後に10分の待機時間を設ける
            time.sleep(600)

        next_page_tag = soup.find('a', text='次へ')
        if next_page_tag:
            next_url = base_url + next_page_tag['href']
            print(f"次のページ: {next_url}")
            return next_url
        else:
            print("次のページが見つかりませんでした。")
            return None
    except Exception as e:
        print(f"ページの取得中にエラーが発生しました: {e}")
        return None

# ページ番号を自動で増やす方法
current_page = 1
while current_page <= 42:
    url = f'https://www.courts.go.jp/app/hanrei_jp/list1?page={current_page}&sort=2&filter%5Btext1%5D=%E8%AA%B9%E8%AC%97%E4%B8%AD%E5%82%B7'
    url = scrape_page(url)
    current_page += 1

    # 次のページに進む前に10分の待機時間を設ける
    time.sleep(600)
