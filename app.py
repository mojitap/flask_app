import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
from routes import main, auth  # Blueprintをインポート

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

# Blueprint登録
app.register_blueprint(main)  # メインのルート
app.register_blueprint(auth)  # 認証用ルート

# 環境変数の読み込み
load_dotenv()

# アプリケーションの起動
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
