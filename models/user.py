from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    # OAuthで取得するIDが文字列なので、Stringで定義
    id = db.Column(db.String(255), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)

def create_sample_user():
    if not User.query.filter_by(email="sample@example.com").first():
        user = User(id="1", email="sample@example.com")
        db.session.add(user)
        db.session.commit()
