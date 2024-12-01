from google.cloud import storage
import os
from flask import Flask, redirect, url_for, request, render_template, jsonify
from flask_dance.contrib.google import make_google_blueprint, google
from flask_sqlalchemy import SQLAlchemy
from flask_sitemap import Sitemap
from dotenv import load_dotenv
import spacy
import torch
import re
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from gunicorn.app.base import BaseApplication

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

# GCSから判例データをダウンロードする関数
def download_from_bucket(bucket_name, source_blob_name, destination_file_name):
    """Google Cloud Storageからファイルをダウンロード"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        print(f"Downloaded {source_blob_name} to {destination_file_name}.")
    except Exception as e:
        print(f"Error downloading file from GCS: {e}")
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

# モデルとトークナイザーのグローバル変数
model = None
tokenizer = None

# 前処理関数
def preprocess_text(text):
    text = re.sub(r'[「」]', '', text)
    return text.strip()

# テキスト分類関数
def classify_text(text):
    load_model_and_tokenizer()
    text = preprocess_text(text)
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

# Google OAuth 設定
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

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

# spacy の日本語モデル
nlp = spacy.load("ja_core_news_sm")

# 判例PDFをダウンロードするルート
@app.route('/download-pdf/<filename>', methods=['GET'])
def download_pdf(filename):
    """指定したファイルをGCSからダウンロード"""
    bucket_name = "my-legal-data"
    source_blob_name = f"pdfs/{filename}"  # バケット内のパス
    destination_file_name = f"/tmp/{filename}"  # ローカル保存先

    try:
        download_from_bucket(bucket_name, source_blob_name, destination_file_name)
        return jsonify({"message": f"{filename} downloaded to {destination_file_name}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Sitemap 用ルート
@app.route('/about')
def about():
    return "About Mojitap"

# ヘルスチェックエンドポイント
@app.route('/health')
def health_check():
    return "OK", 200

# 環境変数確認エンドポイント
@app.route("/check-env")
def check_env():
    return jsonify({
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
        "SECRET_KEY": os.getenv("SECRET_KEY")
    })

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
    # download_model_from_gcs()  # コメントアウト
    print("Flask app is starting...")

    options = {
        "bind": "0.0.0.0:5000",
        "workers": 1,
    }
    GunicornFlaskApp(app, options).run()

