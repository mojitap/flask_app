from extensions import db

class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255), unique=True, nullable=False, index=True)  # ✅ 修正後

    @staticmethod
    def add_or_increment(query_text):
        record = SearchHistory.query.filter_by(query=query_text).first()  # ✅ 変更
        if record:
            record.count += 1
        else:
            record = SearchHistory(query=query_text, count=1)
            db.session.add(record)
        db.session.commit()
