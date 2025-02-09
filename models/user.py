from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.String(255), primary_key=True)  # id を文字列型に変更
    email = db.Column(db.String(255), unique=True, nullable=False)

def create_sample_user():
    if not User.query.filter_by(email="sample@example.com").first():
        user = User(id="1", email="sample@example.com")
        db.session.add(user)
        db.session.commit()
