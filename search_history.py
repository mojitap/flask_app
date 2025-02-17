from app import db
# models/search_history.py
from extensions import db

class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    search_term = db.Column(db.String(255), unique=True, nullable=False, index=True)  # カラム名を変更
    count = db.Column(db.Integer, default=1)

    @staticmethod
    def add_or_increment(query):
        # クエリ引数はそのまま利用できますが、検索時は search_term カラムを参照します
        record = SearchHistory.query.filter_by(search_term=query).first()
        if record:
            record.count += 1
        else:
            record = SearchHistory(search_term=query, count=1)
            db.session.add(record)
        db.session.commit()