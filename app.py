from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user
from dotenv import load_dotenv
from routes import main, auth
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

# Google OAuthクライアント登録
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Twitter OAuthクライアント登録
oauth.register(
    name='twitter',
    client_id=os.getenv('TWITTER_CLIENT_ID'),
    client_secret=os.getenv('TWITTER_CLIENT_SECRET'),
    request_token_params={
        'scope': 'read write'
    }
)

# Flask-Login設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    twitter = oauth.twitter.create_client()
    redirect_uri = url_for('authorize_twitter', _external=True)
    return twitter.authorize_redirect(redirect_uri)

@app.route('/authorize/twitter')
def authorize_twitter():
    twitter = oauth.twitter.create_client()
    token = twitter.authorize_access_token()
    user_info = twitter.get('account/verify_credentials.json').json()
    user = User(id=user_info['id_str'])
    login_user(user)
    return redirect('/')

# Blueprint登録
app.register_blueprint(main)
app.register_blueprint(auth, url_prefix="/auth")

# アプリケーションの起動
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
