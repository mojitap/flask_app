from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'user'  # ✅ テーブル名を明示的に指定
    __table_args__ = {'extend_existing': True}  # ✅ 既存テーブルの拡張を許可

    id = db.Column(db.String(255), primary_key=True)  # ✅ Google / Twitter の ID
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=True)  # ✅ Google / Twitter のアカウント名
    auth_type = db.Column(db.String(50), nullable=False)  # ✅ "google" or "twitter"

    def __init__(self, id, email, name, auth_type):
        self.id = id
        self.email = email
        self.name = name
        self.auth_type = auth_type

    @classmethod
    def get_or_create(cls, id, email, name, auth_type):
        user = cls.query.filter_by(id=id).first()
        if not user:
            user = cls(id=id, email=email, name=name, auth_type=auth_type)
            db.session.add(user)
            db.session.commit()
        return user
