# models/search_history.py

from extensions import db

class SearchHistory(db.Model):
    __tablename__ = "search_history"
    
    id = db.Column(db.Integer, primary_key=True)
    
    # DB上は "query" だが、Python では "query_" という名前にして衝突を避ける
    query_ = db.Column("query", db.String(255), unique=True, nullable=False, index=True)
    
    count = db.Column(db.Integer, default=1)

    @classmethod
    def add_or_increment(cls, text_):
        # Model.query は衝突しないので、filter_by(query_=...) が使える
        record = cls.query.filter_by(query_=text_).first()
        if record:
            record.count += 1
        else:
            record = cls(query_=text_, count=1)
            db.session.add(record)
        db.session.commit()
