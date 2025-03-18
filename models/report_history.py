from extensions import db
from datetime import datetime

class ReportHistory(db.Model):
    __tablename__ = "report_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    text_content = db.Column(db.String(500), nullable=False)
    judgement = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 必要なら user_id, ip_address など追加してもOK
    # e.g. user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
