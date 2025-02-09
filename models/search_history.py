from app import db

class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255), unique=True, nullable=False)
    count = db.Column(db.Integer, default=1)

    @staticmethod
    def add_or_increment(query):
        entry = SearchHistory.query.filter_by(query=query).first()
        if entry:
            entry.count += 1
        else:
            entry = SearchHistory(query=query, count=1)
            db.session.add(entry)
        db.session.commit()