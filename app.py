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
