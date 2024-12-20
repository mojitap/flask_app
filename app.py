import logging
import os
from flask import Flask, Response, url_for
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# ローカルと本番のパスを動的に設定
GOOGLE_CREDENTIALS_LOCAL = os.path.join(os.getcwd(), 'client_secrets.json')
GOOGLE_APPLICATION_CREDENTIALS = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', GOOGLE_CREDENTIALS_LOCAL)

# 環境変数にパスを設定
if os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GOOGLE_APPLICATION_CREDENTIALS
    print(f"Using GOOGLE_APPLICATION_CREDENTIALS: {GOOGLE_APPLICATION_CREDENTIALS}")
else:
    raise FileNotFoundError(f"Google credentials file not found at: {GOOGLE_APPLICATION_CREDENTIALS}")

# ログの設定
logging.basicConfig(level=logging.INFO)

# Flask アプリのインスタンス化
app = Flask(__name__)

# .env ファイルの読み込み
load_dotenv()

# 環境変数の取得
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///default.db')
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
OAUTH_REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI')

# 環境変数の確認
logging.info(f"FLASK_ENV: {FLASK_ENV}")
logging.info(f"DATABASE_URL: {DATABASE_URL}")
logging.info(f"SECRET_KEY: {SECRET_KEY}")
logging.info(f"OAUTH_REDIRECT_URI: {OAUTH_REDIRECT_URI}")

# サイトマップのエンドポイント
@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    urls = [url_for(rule.endpoint, _external=True) for rule in app.url_map.iter_rules() if "GET" in rule.methods and len(rule.arguments) == 0]
    sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    {"".join([f"<url><loc>{url}</loc></url>" for url in urls])}
    </urlset>"""
    return Response(sitemap_xml, mimetype="application/xml")

# Flask の設定
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy の設定
db = SQLAlchemy(app)

# 簡易ホームエンドポイント
@app.route("/")
def home():
    return "Hello, Flask with Sitemap!"

# アプリ起動
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
