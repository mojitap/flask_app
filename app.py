from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
from routes import main, auth  # Blueprintをインポート
from authlib.integrations.flask_client import OAuth
import os
from models.user import db, User

# 環境変数の読み込み
load_dotenv()

# Flask アプリケーションの設定
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

# データベース設定
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# データベース初期化
db.init_app(app)

# OAuth クライアント初期化
oauth = OAuth(app)

# Flask-Login設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # 認証用のルートを指定

@login_manager.user_loader
def load_user(user_id):
    """ユーザーIDからユーザーをロードする関数"""
    return User.query.get(int(user_id))  # user_idでDBからユーザーを取得

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

# Blueprint登録
app.register_blueprint(main)
app.register_blueprint(auth, url_prefix="/auth")  # 認証用のBlueprint

# アプリケーションの起動
if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()  # テーブル作成
            from models.user import create_sample_user
            create_sample_user()  # サンプルユーザー作成
            print("データベースの初期化が完了しました。")
        except Exception as e:
            print(f"データベースの初期化中にエラーが発生しました: {e}")
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
