# models/user.py
from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    # OAuthで取得するIDが文字列なので、Stringで定義
    id = db.Column(db.String(255), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    display_name = db.Column(db.String(255))
    provider = db.Column(db.String(50))           # ← 追加
    twitter_screen_name = db.Column(db.String(255))  # ← 追加
    is_premium = db.Column(db.Boolean, default=False)  # 🔹 課金ユーザーは True

    def __repr__(self):
        return f"<User id={self.id} email={self.email} display_name={self.display_name}>"

def create_sample_user():
    if not User.query.filter_by(email="sample@example.com").first():
        user = User(id="1", email="sample@example.com", display_name="SampleUser")
        db.session.add(user)
        db.session.commit()
