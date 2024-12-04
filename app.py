from google.cloud import storage
import os
from flask import Flask, redirect, url_for, request, render_template, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_sitemap import Sitemap
from dotenv import load_dotenv
import spacy
import torch
import re
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from gunicorn.app.base import BaseApplication
from google_auth_oauthlib.flow import Flow

# Google Cloud Storageの設定
BUCKET_NAME = "my-legal-data"
MODEL_FOLDER = "models/distilbert-base-uncased"
LOCAL_MODEL_PATH = "./models"

# GCSからモデルをダウンロードする関数
def download_model_from_gcs():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix=MODEL_FOLDER)

        # ローカルにフォルダを作成
        os.makedirs(LOCAL_MODEL_PATH, exist_ok=True)

        for blob in blobs:
            filename = blob.name.split("/")[-1]  # ファイル名を取得
            local_file_path = os.path.join(LOCAL_MODEL_PATH, filename)
            blob.download_to_filename(local_file_path)
            print(f"Downloaded {filename} to {local_file_path}")
    except Exception as e:
        print(f"Error downloading model: {e}")
        raise

# モデルのロード
def load_model_and_tokenizer():
    global model, tokenizer
    if model is None or tokenizer is None:
        print("Loading model and tokenizer...")
        model = DistilBertForSequenceClassification.from_pretrained(LOCAL_MODEL_PATH)
        tokenizer = DistilBertTokenizer.from_pretrained(LOCAL_MODEL_PATH)

# 環境変数を読み込む
load_dotenv()

# Flask アプリのインスタンス化
app = Flask(__name__)
ext = Sitemap(app=app)

# Flaskの設定
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')

# OAuth設定
flow = Flow.from_client_secrets_file(
    'client_secrets.json',
    scopes=['https://www.googleapis.com/auth/userinfo.email'],
    redirect_uri=os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:5000/oauth2callback')
)

@app.route('/login')
def login():
    authorization_url, state = flow.authorization_url()
    session['state'] = state
    return redirect(authorization_url)

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

# モデルとトークナイザーのグローバル変数
model = None
tokenizer = None

# テキスト分類関数
def classify_text(text):
    load_model_and_tokenizer()
    inputs = tokenizer(text, return_tensors='pt', truncation=True, padding='max_length', max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        prediction = torch.argmax(logits, dim=1).item()
    return prediction

# 簡易ルート
@app.route("/")
def home():
    return "Hello, Render!"

# 分類エンドポイント
@app.route('/classify', methods=['POST'])
def classify():
    data = request.json
    text = data.get('text', '')
    prediction = classify_text(text)
    return jsonify({'prediction': prediction})

# SQLAlchemy データベース設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///search_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# データベースモデル
class SearchData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)

# データベース初期化
with app.app_context():
    db.create_all()

# Gunicorn用クラス
class GunicornFlaskApp(BaseApplication):
    def __init__(self, app, options=None):
        self.app = app
        self.options = options or {}
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        return self.app

if __name__ == "__main__":
    print("Skipping model download for debugging...")
    print("Flask app is starting...")

    options = {
        "bind": f"0.0.0.0:{os.getenv('PORT', '5000')}",
        "workers": 1,
    }
    GunicornFlaskApp(app, options).run()
