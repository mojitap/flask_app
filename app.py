import os
import logging
import spacy
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from flask import make_response
from flask_sqlalchemy import SQLAlchemy
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv
from textblob import TextBlob
from rapidfuzz import fuzz
import jaconv
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# 環境変数の読み込み (.env)
load_dotenv()

# spaCy の日本語モデルをロード
nlp = spacy.load("ja_core_news_sm")

# Flask アプリケーションの設定
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ログ設定
logging.basicConfig(level=logging.INFO)

# データベース設定
db = SQLAlchemy(app)

# Flask-Login設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login_google"

# ユーザークラス
class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# OAuthの初期化
oauth = OAuth(app)

# Googleの設定
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Twitter OAuth 設定（/authorize/twitter）
@app.route('/authorize/twitter')
def authorize_twitter():
    twitter = OAuth1Session(
        client_key=os.getenv('TWITTER_API_KEY'),
        client_secret=os.getenv('TWITTER_API_SECRET'),
        resource_owner_key=request.args.get('oauth_token'),
        verifier=request.args.get('oauth_verifier')
    )
    access_token_url = "https://api.twitter.com/oauth/access_token"
    tokens = twitter.fetch_access_token(access_token_url)
    
    # ユーザー情報を取得
    user_info_url = "https://api.twitter.com/1.1/account/verify_credentials.json"
    user_info = twitter.get(user_info_url).json()
    
    # ユーザー情報を処理
    user = User(id=user_info['id_str'])
    login_user(user)
    return redirect(url_for('home'))

# 攻撃的な単語リストをロード
JSON_PATH = os.path.join(os.path.dirname(__file__), "data", "offensive_words.json")
with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)
    offensive_words = data.get("categories", {}).get("insults", [])

# ルート定義
@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(app.static_folder, "robots.txt")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login/google")
def login_google():
    redirect_uri = url_for("authorize_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route("/authorize/google")
def authorize_google():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo").json()
    user = User(id=user_info["email"])
    login_user(user)
    return redirect("/")

@app.route('/login/twitter')
def login_twitter():
    twitter = OAuth1Session(
        client_key=os.getenv('TWITTER_API_KEY'),
        client_secret=os.getenv('TWITTER_API_SECRET'),
        callback_uri=url_for('authorize_twitter', _external=True)
    )
    request_token_url = "https://api.twitter.com/oauth/request_token"
    response = twitter.fetch_request_token(request_token_url)
    oauth_token = response.get('oauth_token')
    redirect_url = f"https://api.twitter.com/oauth/authorize?oauth_token={oauth_token}"
    return redirect(redirect_url)

@app.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect("/")

# キャッシュ用の辞書（グローバル）
search_cache = {}

@app.route('/quick_check', methods=['POST'])
@login_required
def quick_check():
    query = request.form.get("text", "").strip()
    if not query:
        return make_response("<h2>エラー: 検索クエリが空です。</h2>", 400)

    # evaluate_text 関数で評価
    result, detail = evaluate_text(query, offensive_words)

    # TextBlob による感情分析
    sentiment = TextBlob(query).sentiment.polarity
    if sentiment < -0.3:
        sentiment_label = "否定的"
    elif sentiment > 0.3:
        sentiment_label = "肯定的"
    else:
        sentiment_label = "中立的"

    # 検索結果の日本語形式でのレスポンス
    result_message = ""
    if result == "この文章は名誉毀損や誹謗中傷に該当する可能性があります。":
        result_message = "一致: この文章は名誉毀損や誹謗中傷に該当する可能性があります。"
    elif result == "一部の表現が問題となる可能性があります。":
        result_message = "部分一致: 一部の表現が問題となる可能性があります。"
    elif result == "文脈が攻撃的であるかを判定し、追加の注意喚起を表示。":
        result_message = f"文脈解析: {detail}"
    else:
        result_message = "問題ありません。"

    # HTML形式で返す
    response_html = f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <title>検索結果</title>
        </head>
        <body>
            <h2>検索結果</h2>
            <p><strong>クエリ:</strong> {query}</p>
            <p><strong>評価:</strong> {result_message}</p>
            <p><strong>感情分析:</strong> {sentiment_label}</p>
        </body>
    </html>
    """
    response = make_response(response_html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response

# 前処理と類似表現検出

def normalize_text(text):
    # 全角を半角に変換（カナ・数字・英字）
    text = jaconv.z2h(text, kana=True, digit=True, ascii=True)
    # 例：カタカナをひらがなに変換
    text = jaconv.kata2hira(text)
    return text

def get_lemmas(text):
    doc = nlp(text)
    lemmas = [token.lemma_ for token in doc]
    return " ".join(lemmas)

def check_partial_match(text, offensive_words, threshold=80):
    for word in offensive_words:
        score = fuzz.partial_ratio(word, text)
        if score >= threshold:
            return True, word, score
    return False, None, None

def check_exact_match(text, offensive_words):
    for word in offensive_words:
        if word in text:
            return True, word
    return False, None

def check_offensive_expression(text, offensive_words, threshold=80):
    normalized_text = normalize_text(text)
    lemmas_text = get_lemmas(normalized_text)
    return check_partial_match(lemmas_text, offensive_words, threshold)

def contextual_analysis(text):
    # 例：感嘆符が多い場合を疑わしいとする
    exclamation_count = text.count("!")
    if exclamation_count > 3:
        return True, "感嘆符が多すぎます"
    return False, None

def evaluate_text(text, offensive_words):
    # 入力テキストと offensive_words の各単語を正規化して比較する
    normalized_text = normalize_text(text)
    norm_offensive_words = [normalize_text(word) for word in offensive_words]

    # 1. 完全一致判定
    exact, word = check_exact_match(normalized_text, norm_offensive_words)
    if exact:
        # 一致の場合のメッセージ
        return "この文章は名誉毀損や誹謗中傷に該当する可能性があります。", word

    # 2. 部分一致判定
    partial, word, score = check_partial_match(normalized_text, norm_offensive_words)
    if partial:
        # 部分一致の場合のメッセージ
        return "一部の表現が問題となる可能性があります。", word

    # 3. 文脈解析
    context_flag, reason = contextual_analysis(text)
    if context_flag:
        # 文脈解析の場合のメッセージ
        return "文脈が攻撃的であるかを判定し、追加の注意喚起を表示。", reason

    return "問題ありません", None

# 感情分類モデル関連

def load_sentiment_model():
    model_name = "cl-tohoku/bert-base-japanese"  # 適宜変更してください
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    quantized_model = torch.quantization.quantize_dynamic(
        model, {torch.nn.Linear}, dtype=torch.qint8
    )
    return tokenizer, quantized_model

def analyze_sentiment_with_model(text, tokenizer, model):
    inputs = tokenizer(text, max_length=128, truncation=True, padding="max_length", return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
        prediction = torch.argmax(outputs.logits, dim=1).item()
    return prediction

@app.route("/terms")
def show_terms():
    terms_path = os.path.join(os.path.dirname(__file__), "terms.txt")
    try:
        with open(terms_path, "r", encoding="utf-8") as f:
            terms_content = f.read()
        return render_template("terms.html", terms_content=terms_content)
    except FileNotFoundError:
        logging.error("利用規約ファイルが見つかりません。")
        return render_template("terms.html", terms_content="利用規約は現在利用できません。")

# データベースモデル
class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255), unique=True, nullable=False)
    count = db.Column(db.Integer, default=1)

    @staticmethod
    def add_or_increment(query):
        entry = SearchHistory.query.filter_by(query=query).first()
        if entry:
            entry.count += 1
        else:
            entry = SearchHistory(query=query, count=1)
            db.session.add(entry)
        db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
