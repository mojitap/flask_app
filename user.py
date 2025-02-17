# models/user.py
from flask_login import UserMixin
from extensions import db  # extensions.py から db をインポートする

# db = SQLAlchemy()  <- この行を削除します

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(255), primary_key=True)  # ここではメールアドレスや Twitter の id などを利用
    email = db.Column(db.String(255), unique=True, nullable=False)

def create_sample_user():
    if not User.query.filter_by(email="sample@example.com").first():
        user = User(id="1", email="sample@example.com")
        db.session.add(user)
        db.session.commit()