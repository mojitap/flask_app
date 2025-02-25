import os
import json
import requests
from flask import Flask, render_template, redirect, url_for, send_from_directory, session, current_app
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
from requests_oauthlib import OAuth1Session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from extensions import db
from routes.main import main
from routes.auth import auth
from models.user import User

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder="static")
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    # Flask設定
    app.secret_key = os.getenv("SECRET_KEY", "dummy_secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///instance/local.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_AS_ASCII"] = False

    # SQLAlchemy + Migrate
    db.init_app(app)
    migrate = Migrate(app, db)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # Blueprint登録
    app.register_blueprint(main)
    app.register_blueprint(auth)

    # OAuth 初期化
    oauth = OAuth(app)
    oauth.init_app(app)
    app.config["OAUTH_INSTANCE"] = oauth

    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")  # シークレットキー

    # ... DB init, login_manager, blueprint登録など ...

    @app.route("/checkout")
    @login_required
    def checkout():
        return render_template("checkout.html", stripe_public_key=os.getenv("STRIPE_PUBLIC_KEY"))

    @app.route("/create-checkout-session", methods=["POST"])
    @login_required
    def create_checkout_session():
        session = stripe.checkout.Session.create(
            line_items=[{
                "price": "price_1QwIQhP8wMOQp1FurzBAyZhx",
                "quantity": 1
            }],
            mode="subscription",
            success_url="https://mojitap.com/success",
            cancel_url="https://mojitap.com/cancel"
        )
        return jsonify({"id": session.id})

    @app.route("/success")
    @login_required
    def success():
        # current_user.is_premium = True
        # db.session.commit()
        return render_template("success.html")

    @app.route("/cancel")
    @login_required
    def cancel():
        return render_template("cancel.html")

    @app.route("/cancel-subscription", methods=["POST"])
    @login_required
    def cancel_subscription():
        # subscription_id を保存している場合は、Stripe上で削除
        if current_user.stripe_subscription_id:
            stripe.Subscription.delete(current_user.stripe_subscription_id)
        # DB上でも is_premium=False
        current_user.is_premium = False
        db.session.commit()
        flash("プレミアムプランを解約しました。")
        return redirect(url_for("home"))  

    # --- Dropbox からファイルをダウンロードする関数 ---
    def download_file(url, local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ {local_path} をダウンロードしました")
        else:
            print(f"❌ {local_path} のダウンロードに失敗しました: {response.status_code}")

    # Dropboxファイルダウンロード
    dropbox_offensive_words_url = os.getenv("DROPBOX_OFFENSIVE_WORDS_URL")
    dropbox_whitelist_url = os.getenv("DROPBOX_WHITELIST_URL")

    local_offensive_words_path = os.path.join(app.root_path, "data", "offensive_words.json")
    local_whitelist_path = os.path.join(app.root_path, "data", "whitelist.json")

    if dropbox_offensive_words_url:
        download_file(dropbox_offensive_words_url, local_offensive_words_path)

    if dropbox_whitelist_url:
        download_file(dropbox_whitelist_url, local_whitelist_path)

    # offensive_words.json のロード
    try:
        with open(local_offensive_words_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        app.config["OFFENSIVE_WORDS"] = data
        print("✅ `offensive_words.json` をロードしました")
    except FileNotFoundError:
        app.logger.error(f"{local_offensive_words_path} が見つかりません。")
        app.config["OFFENSIVE_WORDS"] = {}

    # OAuth登録
    oauth.register(
        name="google",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"}
    )
    oauth.register(
        name="twitter",
        client_id=os.getenv("TWITTER_API_KEY"),
        client_secret=os.getenv("TWITTER_API_SECRET"),
        request_token_params={"scope": "read write"}
    )

    # 静的ファイル & 利用規約ページなどのルート
    @app.route("/static/<path:filename>")
    def static_files(filename):
        return send_from_directory("static", filename)

    @app.route("/robots.txt")
    def robots():
        return send_from_directory(app.static_folder, "robots.txt")

    # ---- (A) 利用規約の表示 ----
    @app.route("/terms")
    def show_terms():
        terms_path = os.path.join(app.root_path, "terms.txt")
        try:
            with open(terms_path, "r", encoding="utf-8") as f:
                terms_content = f.read()
            return render_template("terms.html", terms_content=terms_content)
        except FileNotFoundError:
            current_app.logger.error(f"{terms_path} が見つかりません。")
            return render_template("terms.html", terms_content="利用規約は現在利用できません。")

    # ---- (B) プライバシーポリシーの表示 ----
    @app.route("/privacy")
    def show_privacy():
        privacy_path = os.path.join(app.root_path, "privacy.txt")
        try:
            with open(privacy_path, "r", encoding="utf-8") as f:
                privacy_content = f.read()
            return render_template("privacy.html", privacy_content=privacy_content)
        except FileNotFoundError:
            current_app.logger.error(f"{privacy_path} が見つかりません。")
            return render_template("privacy.html", privacy_content="プライバシーポリシーは現在利用できません。")

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
