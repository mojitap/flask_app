import os
import logging
import json
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from textblob import TextBlob
import re

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(app.static_folder, "robots.txt")

# 環境変数の読み込み (.env)
load_dotenv()

# Flask アプリケーションの設定
app = Flask(__name__)
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

# OAuth設定
oauth = OAuth(app)
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
    client_kwargs={"scope": "openid email profile"}
)
oauth.register(
    name="twitter",
    client_id=os.getenv("TWITTER_CLIENT_ID"),
    client_secret=os.getenv("TWITTER_CLIENT_SECRET"),
    authorize_url="https://twitter.com/i/oauth2/authorize",
    access_token_url="https://api.twitter.com/2/oauth2/token",
    api_base_url="https://api.twitter.com/2/",
    client_kwargs={"scope": "tweet.read users.read offline.access"}
)

# 攻撃的な単語リストをロード
JSON_PATH = os.path.join(os.path.dirname(__file__), "offensive_words.json")
with open(JSON_PATH, "r", encoding="utf-8") as f:
    offensive_words = json.load(f)

# 🔹 ルート
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
    user_info = oauth.google.get("userinfo").json()
    user = User(id=user_info["email"])
    login_user(user)
    return redirect("/")

@app.route("/login/twitter")
def login_twitter():
    redirect_uri = url_for("authorize_twitter", _external=True)
    return oauth.twitter.authorize_redirect(redirect_uri)

@app.route("/authorize/twitter")
def authorize_twitter():
    token = oauth.twitter.authorize_access_token()
    user_info = oauth.twitter.get("users/me?user.fields=username").json()
    username = user_info["data"]["username"]
    user = User(id=username)
    login_user(user)
    return redirect("/")

@app.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect("/")

# キャッシュ用の辞書（グローバル）
search_cache = {}

@app.route("/search", methods=["POST"])
@login_required
def search():
    query = request.form.get("query", "").strip()
    if not query:
        return jsonify({"error": "検索クエリが空です。"})

    # キャッシュを利用した感情解析
    if query in search_cache:
        sentiment = search_cache[query]["sentiment"]
        warnings = search_cache[query]["warnings"]
    else:
        # 感情解析と攻撃的単語のチェックを実施
        sentiment = TextBlob(query).sentiment.polarity
        warnings = []

        # 攻撃的な単語の直接一致を確認
        for word in offensive_words.get("direct_insults", []):
            if word in query:
                warnings.append(f"一致: {word}")

        # 攻撃的なフレーズの部分一致を確認
        for phrase in offensive_words.get("aggressive_phrases", []):
            if re.search(re.escape(phrase), query):
                warnings.append(f"部分一致: {phrase}")

        # 文脈解析（感情解析結果の判定）
        if sentiment < -0.3:
            sentiment_label = "否定的"
            warnings.append("文脈解析: 攻撃的または否定的な表現が含まれています。")
        elif sentiment > 0.3:
            sentiment_label = "肯定的"
        else:
            sentiment_label = "中立的"

        # キャッシュに結果を保存
        search_cache[query] = {"sentiment": sentiment_label, "warnings": warnings}

    # レスポンスを返す
    return jsonify({
        "query": query,
        "sentiment": search_cache[query]["sentiment"],
        "warnings": search_cache[query]["warnings"],
        "note": "この検索結果は必ずしも正確とは限りません。必要に応じて専門家にご相談ください。"
    })

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
