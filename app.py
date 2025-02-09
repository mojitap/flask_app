from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
from routes import main, auth  # Blueprintをインポート

# Flask アプリケーションの設定
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

# データベース設定
db = SQLAlchemy(app)

# Flask-Login設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"  # 認証用のルートを指定

# Blueprint登録
app.register_blueprint(main)
app.register_blueprint(auth, url_prefix="/auth")  # 認証用のBlueprint

# 環境変数の読み込み
load_dotenv()

# アプリケーションの起動
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
