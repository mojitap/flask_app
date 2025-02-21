from extensions import db

class SearchHistory(db.Model):
    __tablename__ = "search_history"  # ✅ 明示的にテーブル名を指定
    id = db.Column(db.Integer, primary_key=True)
    search_query = db.Column(db.String(255), unique=True, nullable=False, index=True)  # ✅ `search_query` に統一
    count = db.Column(db.Integer, default=1)

    @classmethod
    def add_or_increment(cls, query_text):
        """検索履歴を追加 or カウント増加"""
        record = cls.query.filter_by(search_query=query_text).first()  # ✅ 統一
        if record:
            record.count += 1
        else:
            record = cls(search_query=query_text, count=1)  # ✅ 統一
            db.session.add(record)
        db.session.commit()
