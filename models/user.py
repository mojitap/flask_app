from extensions import db

class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.String(255), primary_key=True)  # ✅ TwitterのIDは文字列
    email = db.Column(db.String(255), unique=True, nullable=False)
    auth_type = db.Column(db.String(50), nullable=False)  # ✅ "google" or "twitter"
    profile_image_url = db.Column(db.String(500), nullable=True)  # ✅ Twitterアイコン用

    def __init__(self, id, email, auth_type, profile_image_url=None):
        self.id = id
        self.email = email
        self.auth_type = auth_type
        self.profile_image_url = profile_image_url

    @classmethod
    def get_or_create(cls, id, email, auth_type, profile_image_url=None):
        user = cls.query.filter_by(id=id).first()
        if not user:
            user = cls(id=id, email=email, auth_type=auth_type, profile_image_url=profile_image_url)
            db.session.add(user)
            db.session.commit()
        return user
