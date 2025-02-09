from flask import Blueprint, redirect, url_for, request, session
from flask_login import login_user, logout_user
from authlib.integrations.flask_client import OAuth
from app import app  # Flaskインスタンスを利用
from models.user import User

auth = Blueprint("auth", __name__)
oauth = OAuth(app)

# Googleの設定
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@auth.route("/login/google")
def login_google():
    redirect_uri = url_for("auth.authorize_google", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route("/authorize/google")
def authorize_google():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo").json()
    user = User.get_or_create(user_info["email"])
    login_user(user)
    return redirect("/")

@auth.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect("/")