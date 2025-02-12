from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from models.text_evaluation import evaluate_text
from models.search_history import SearchHistory

print("✅ main.py が読み込まれました！")

main = Blueprint('main', __name__)

@main.route("/")
def home():
    print("✅ / にアクセスされました")
    return render_template("index.html")

@main.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    """SNSでの表現が問題ないかをチェック"""
    query = request.form.get("text", "").strip()
    if not query:
        return "<h2>エラー: 検索クエリが空です。</h2>", 400

    # 検索履歴の更新
    SearchHistory.add_or_increment(query)

    # 統合された問題単語リストを取得
    offensive_words = current_app.config.get("OFFENSIVE_WORDS", [])

    # テキストを評価
    result = evaluate_text(query, offensive_words)

    return render_template("result.html", query=query, result=result)
