from extensions import db

class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255), unique=True, nullable=False, index=True)  # ✅ `search_term` → `query` に修正
    count = db.Column(db.Integer, default=1)  # ✅ デフォルト値追加

    @staticmethod
    def add_or_increment(query):
        record = SearchHistory.query.filter_by(query=query).first()
        if record:
            record.count += 1
        else:
            record = SearchHistory(query=query, count=1)
            db.session.add(record)
        db.session.commit()
