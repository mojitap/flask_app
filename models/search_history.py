from extensions import db

class SearchHistory(db.Model):
    __tablename__ = "search_history"
    id = db.Column(db.Integer, primary_key=True)
    search_query = db.Column(db.String(255), unique=True, nullable=False, index=True)  # ✅ `query` → `search_query` に統一
    count = db.Column(db.Integer, default=1)

    @classmethod
    def add_or_increment(cls, query_text):
        """検索履歴を追加 or カウント増加"""
        record = cls.query.filter_by(search_query=query_text).first()  # ✅ 修正（`query` → `search_query`）
        if record:
            record.count += 1
        else:
            record = cls(search_query=query_text, count=1)  # ✅ 修正（`query` → `search_query`）
            db.session.add(record)
        db.session.commit()
