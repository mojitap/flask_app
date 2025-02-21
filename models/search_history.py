from extensions import db

class SearchHistory(db.Model):
    __tablename__ = "search_history"
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(255), unique=True, nullable=False, index=True)  # ✅ 修正済み
    count = db.Column(db.Integer, default=1)  # ✅ デフォルト値追加

    @classmethod
    def add_or_increment(cls, query_text):
        """検索履歴を追加 or カウント増加"""
        record = cls.query.filter(cls.search_query == query_text).first()
        if record:
            record.count += 1
        else:
            record = cls(query=query_text, count=1)
            db.session.add(record)
        db.session.commit()
