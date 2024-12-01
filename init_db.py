from app import db  # Flaskアプリケーションのファイル名がapp.pyである場合

# データベースの初期化
with db.app.app_context():
    db.create_all()

print("Database initialized.")
