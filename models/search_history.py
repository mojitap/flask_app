# models/search_history.py
from extensions import db

class SearchHistory(db.Model):
    __tablename__ = "search_history"
    id = db.Column(db.Integer, primary_key=True)
    search_query = db.Column(db.String(255), unique=True, nullable=False, index=True)
    count = db.Column(db.Integer, default=1)

    @classmethod
    def add_or_increment(cls, query_text):
        record = cls.query.filter_by(search_query=query_text).first()
        if record:
            record.count += 1
        else:
            record = cls(search_query=query_text, count=1)
            db.session.add(record)
        db.session.commit()
