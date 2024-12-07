import logging
import os
from flask import Flask, request, abort, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_sitemap import Sitemap
from dotenv import load_dotenv
import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from google_auth_oauthlib.flow import Flow

# ログの設定
logging.basicConfig(level=logging.INFO)

# Flask アプリのインスタンス化
app = Flask(__name__)
ext = Sitemap(app=app)

# 環境変数を読み込む
load_dotenv()

# Flaskの設定
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
logging.info(f"SECRET_KEY is: {app.config['SECRET_KEY']}")

# SQLAlchemy データベース設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///search_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# OAuth設定
flow = Flow.from_client_secrets_file(
    'client_secrets.json',  # ファイルパス
    scopes=['https://www.googleapis.com/auth/userinfo.email'],
    redirect_uri='https://mojitap.com/oauth2callback'
)

# モデルとトークナイザーのグローバル変数
model = None
tokenizer = None

# 特定のパスをブロック
@app.before_request
def block_disallowed_paths():
    blocked_paths = [
        ".env", "wordpress", "wp-admin", "wp-content", 
        "updates.php", "bless.php", "index/admin.php", 
        "wp-includes", "wp-login.php", "setup-config.php"
    ]
    if any(path in request.path for path in blocked_paths):
        logging.info(f"Blocked path accessed: {request.path}")
        abort(404)  # 404エラーを返す

# モデルとトークナイザーのロード
def load_model_and_tokenizer():
    global model, tokenizer
    if model is None or tokenizer is None:
        logging.info("Loading model and tokenizer...")
        model = DistilBertForSequenceClassification.from_pretrained("./models")
        tokenizer = DistilBertTokenizer.from_pretrained("./models")

# テキスト分類関数
def classify_text(text):
    load_model_and_tokenizer()
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding='max_length', max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        prediction = torch.argmax(logits, dim=1).item()
    return prediction

# データベースモデル
class SearchData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)

# データベース初期化
with app.app_context():
    db.create_all()

# 簡易ルート
@app.route("/")
def home():
    return "Hello, Render!"

# ログインルート
@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return redirect(authorization_url)

@app.route('/test_blocked_path')
def test_blocked_path():
    return "This route should not be blocked.", 200

@app.route('/oauth2callback')
def oauth2callback():
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    return jsonify({
        "message": "Login Successful!",
        "credentials": {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
        },
    })

# 分類エンドポイント
@app.route('/classify', methods=['POST'])
def classify():
    data = request.json
    text = data.get('text', '')
    prediction = classify_text(text)
    return jsonify({'prediction': prediction})

# アプリ起動
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
