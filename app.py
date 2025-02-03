import os
import logging
import requests
import gzip
import shutil
import tarfile
import torch
import json
import threading
import time
import spacy
import psycopg2

from flask import Flask, request, jsonify, redirect, url_for, render_template
from flask_login import current_user, LoginManager, login_user, logout_user, login_required, UserMixin
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from transformers import AutoModelForSequenceClassification, AutoTokenizer

# 🔹 環境変数の読み込み (.env)
load_dotenv()

# 🔹 メモリ使用量を最適化（キャッシュ制限）
os.environ["HF_HOME"] = "./cache"
os.environ["TRANSFORMERS_CACHE"] = "./cache"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

torch.set_num_threads(1)  # スレッド数を制限しメモリ節約

# 🔹 ログ設定
logging.basicConfig(level=logging.DEBUG)

# 🔹 SpaCy 日本語モデルのロード
logging.info("Loading SpaCy model (ja_core_news_sm)...")
nlp = spacy.load("ja_core_news_sm")
logging.info("SpaCy model loaded.")

# 🔹 Flask アプリケーションの作成
app = Flask(__name__)

# Flask-Loginの設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # ログインページのエンドポイント名を指定

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    """ユーザーをIDでロードする"""
    return User(user_id)

# ✅ current_user をテンプレートで使用可能にする
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# 🔹 `offensive_words.json` のパス
JSON_PATH = os.path.join(os.path.dirname(__file__), "offensive_words.json")

def load_offensive_words():
    """`offensive_words.json` をロード"""
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            words_data = json.load(f)
        return words_data.get("words", []), words_data.get("phrases", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return [], []

# ✅ `offensive_words.json` の初期ロード
offensive_words, offensive_phrases = load_offensive_words()

# 🔹 量子化モデルの初期化
quantized_model = None
tokenizer = None

def load_model():
    """量子化モデルを1回だけロードする"""
    global quantized_model, tokenizer

    if quantized_model is None or tokenizer is None:
        model_name = "prajjwal1/bert-tiny"

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(model_name)

        # ✅ モデルの量子化
        quantized_model = torch.quantization.quantize_dynamic(
            model, {torch.nn.Linear}, dtype=torch.qint8
        )
        logging.info("✅ モデル量子化完了！")

# 🔹 データベース設定
db_url = os.getenv("DATABASE_URL", "sqlite:///database.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255), unique=True, nullable=False)
    count = db.Column(db.Integer, default=1)

    @staticmethod
    def add_or_increment(query):
        """検索履歴をDBに追加する or カウントを増やす"""
        search_entry = SearchHistory.query.filter_by(query=query).first()
        if search_entry:
            search_entry.count += 1
        else:
            search_entry = SearchHistory(query=query, count=1)
            db.session.add(search_entry)
        db.session.commit()

def update_offensive_words_from_search():
    """10回以上検索された単語を `offensive_words.json` に追加"""
    threshold = 10
    words_to_add = db.session.query(SearchHistory).filter(SearchHistory.count >= threshold).all()

    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            words_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        words_data = {"words": [], "phrases": []}

    existing_words = set(words_data["words"])

    for word_entry in words_to_add:
        if word_entry.query not in existing_words:
            words_data["words"].append(word_entry.query)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(words_data, f, ensure_ascii=False, indent=4)

    logging.info("✅ `offensive_words.json` を更新しました！")

# 環境変数からDropbox URLを取得
DROPBOX_DIFFERENCE_URL = os.getenv("DROPBOX_DIFFERENCE_URL")
DROPBOX_MODEL_URL = os.getenv("DROPBOX_MODEL_URL")
DROPBOX_OFFENSIVE_WORDS_URL = os.getenv("DROPBOX_OFFENSIVE_WORDS_URL")

# ログ設定
logging.basicConfig(level=logging.INFO)

def download_file(url, output_path):
    """
    Dropboxからファイルをダウンロードする汎用関数。
    """
    try:
        if not url:
            raise ValueError(f"URLが指定されていません: {output_path}")

        logging.info(f"Downloading file from {url} to {output_path}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # ファイルを書き込み
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logging.info(f"✅ ダウンロード完了: {output_path}")
        return output_path
    except Exception as e:
        logging.error(f"❌ ダウンロード失敗 ({output_path}): {e}")
        return None

def download_offensive_words():
    """
    `offensive_words.json` をDropboxからダウンロード。
    """
    output_path = os.path.join(os.path.dirname(__file__), "offensive_words.json")
    return download_file(DROPBOX_OFFENSIVE_WORDS_URL, output_path)

def download_difference_file():
    """
    `difference.txt.gz` をDropboxからダウンロード。
    """
    output_path = os.path.join(os.path.dirname(__file__), "scrape_scripts", "difference.txt.gz")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)  # フォルダがなければ作成
    return download_file(DROPBOX_DIFFERENCE_URL, output_path)

def download_model_file():
    """
    `model.safetensors.gz` をDropboxからダウンロード。
    """
    output_path = os.path.join(os.path.dirname(__file__), "models", "model.safetensors.gz")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)  # フォルダがなければ作成
    return download_file(DROPBOX_MODEL_URL, output_path)

# 実行例
if __name__ == "__main__":
    download_offensive_words()
    download_difference_file()
    download_model_file()

# 🔹 DB初期化
with app.app_context():
    db.create_all()

# ✅ Render の Cronジョブが有効なら 24時間ごとに `offensive_words.json` を更新
def scheduled_update():
    while True:
        update_offensive_words_from_search()
        time.sleep(86400)  # 24時間ごと

threading.Thread(target=scheduled_update, daemon=True).start()

# 🔹 Flaskルート
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    global quantized_model, tokenizer
    load_model()

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            return render_template("search.html", error="検索クエリが空です。")

        # ✅ 検索履歴に保存
        SearchHistory.add_or_increment(query)

        try:
            inputs = tokenizer(query, max_length=128, truncation=True, padding="max_length", return_tensors="pt")
            with torch.no_grad():
                outputs = quantized_model(**inputs)
                predictions = torch.argmax(outputs.logits, dim=1).item()
            return render_template("result.html", result=f"判定結果: {predictions}")
        except Exception as e:
            logging.error(f"検索処理中にエラー: {e}")
            return render_template("search.html", error="検索処理中にエラーが発生しました。")

    return render_template("search.html")

@app.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    user_text = request.form.get("text", "")
    for word in offensive_words:
        if word in user_text:
            return jsonify({
                "result": f"この文章には問題があります: '{word}' が含まれています。",
                "caution": "注意: 法的判断を下すものではありません。専門家に相談してください。"
            })
    return jsonify({"result": "この文章は問題ありません。"})

@app.route("/terms")
@login_required
def show_terms():
    terms_content = "ここに利用規約の内容を記載します。"
    return render_template("terms.html", terms_content=terms_content)

# 🔹 アプリ起動
if __name__ == "__main__":
    load_model()
    app.run(debug=False, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
