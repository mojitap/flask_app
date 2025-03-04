# models/user.py
from flask_login import UserMixin
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = "user"
    __table_args__ = {"extend_existing": True}

    # OAuthで取得するIDが文字列なので、Stringで定義
    id = db.Column(db.String(255), primary_key=True)
    email = db.Column(db.String(255), nullable=True)
    display_name = db.Column(db.String(255), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    twitter_screen_name = db.Column(db.String(255), nullable=True)
    line_user_id = db.Column(db.String(255), nullable=True)  # ✅ LINE内部ID
    line_display_name = db.Column(db.String(255), nullable=True)  # ✅ LINE表示名
    
    def __repr__(self):
        return f"<User id={self.id} email={self.email} display_name={self.display_name}>"

def create_sample_user():
    if not User.query.filter_by(email="sample@example.com").first():
        user = User(id="1", email="sample@example.com", display_name="SampleUser")
        db.session.add(user)
        db.session.commit()
