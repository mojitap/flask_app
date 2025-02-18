from extensions import db

class SearchHistory(db.Model):
    __tablename__ = 'search_history'
    id = db.Column(db.Integer, primary_key=True)
    search_query = db.Column(db.String(255), unique=True, nullable=False, index=True)
    count = db.Column(db.Integer, default=1)

    @staticmethod
    def add_or_increment(query_text):
        record = SearchHistory.query.filter_by(search_query=query_text).first()
        if record:
            record.count += 1
        else:
            record = SearchHistory(search_query=query_text, count=1)
            db.session.add(record)
        db.session.commit()
