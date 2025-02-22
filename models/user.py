from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'user'  # ✅ テーブル名を明示的に指定
    __table_args__ = {'extend_existing': True}  # ✅ 既存テーブルの拡張を許可

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)

def create_sample_user():
    if not User.query.filter_by(email="sample@example.com").first():
        user = User(id="1", email="sample@example.com")
        db.session.add(user)
        db.session.commit()
