from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from extensions import db  # extensions.py から db をインポート
from flask_login import LoginManager, login_user
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv
from routes import main, auth
from authlib.integrations.flask_client import OAuth
import os
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from models.user import User

# 環境変数の読み込み
load_dotenv()

# Flask アプリケーションの設定
app = Flask(__name__, static_folder="static")

app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///instance/local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ✅ **ルートを適切な位置に移動**
@app.route("/")
def home():
    print("✅ / にアクセスされました")  # デバッグ用
    return render_template("index.html")  # ✅ ここで index.html を正しくレンダリング

# OAuth クライアント初期化
oauth = OAuth(app)

# Google OAuth 登録
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Twitter OAuth 登録
oauth.register(
    name='twitter',
    client_id=os.getenv('TWITTER_API_KEY'),
    client_secret=os.getenv('TWITTER_API_SECRET'),
    request_token_params={'scope': 'read write'}
)

# Flask-Login 設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

# 静的ファイルの配信ルート
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Google 認証ルート
@app.route("/login/google")
def login_google():
    redirect_uri = url_for("authorize_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

# Google 認証ルートの例
@app.route("/authorize/google")
def authorize_google():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo").json()
    email = user_info["email"]
    user = User.query.get(email)
    if not user:
        user = User(id=email, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect("/")

# Twitter 認証ルート
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

@app.route('/authorize/twitter')
def authorize_twitter():
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    if not oauth_verifier:
        return "Error: OAuth verifier is missing.", 400
    
    twitter = OAuth1Session(
        client_key=os.getenv('TWITTER_API_KEY'),
        client_secret=os.getenv('TWITTER_API_SECRET'),
        resource_owner_key=oauth_token,
        verifier=oauth_verifier
    )
    access_token_url = "https://api.twitter.com/oauth/access_token"
    tokens = twitter.fetch_access_token(access_token_url)
    
    user_info_url = "https://api.twitter.com/1.1/account/verify_credentials.json"
    user_info = twitter.get(user_info_url).json()
    twitter_id = user_info.get('id_str')
    if not twitter_id:
        return "Error: Unable to retrieve Twitter user ID", 400
    
    email = user_info.get('email', f"{twitter_id}@twitter.com")
    user = User.query.get(twitter_id)
    if not user:
        user = User(id=twitter_id, email=email)
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect("/")

def update_offensive_words():
    from models.search_history import SearchHistory
    popular_queries = SearchHistory.query.filter(SearchHistory.count >= 10).all()
    print("Offensive words updated based on popular queries.")

scheduler = BackgroundScheduler()
scheduler.add_job(func=update_offensive_words, trigger="interval", hours=24)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# Blueprint 登録
app.register_blueprint(main)
app.register_blueprint(auth, url_prefix="/auth")

# データ読み込み
JSON_PATH = os.path.join(app.root_path, "data", "offensive_words.json")
try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        offensive_words = json.load(f)
    app.config["OFFENSIVE_WORDS"] = offensive_words
except FileNotFoundError:
    app.logger.error(f"{JSON_PATH} が見つかりませんでした。")
    app.config["OFFENSIVE_WORDS"] = []

# 利用規約ページのルート
@app.route("/terms")
def show_terms():
    terms_path = os.path.join(app.root_path, "terms.txt")
    try:
        with open(terms_path, "r", encoding="utf-8") as f:
            terms_content = f.read()
        return render_template("terms.html", terms_content=terms_content)
    except FileNotFoundError:
        app.logger.error(f"利用規約ファイルが見つかりません: {terms_path}")
        return render_template("terms.html", terms_content="利用規約は現在利用できません。")

# データベース初期化
db.init_app(app)

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
