from flask import Blueprint, render_template, request, current_app
from models.text_evaluation import evaluate_text
from flask_login import login_required

main = Blueprint('main', __name__)

@main.route("/")
def home():
    return render_template("index.html")
    
@main.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    query = request.form.get("text", "").strip()
    if not query:
        return "<h2>エラー: 検索クエリが空です。</h2>", 400

    offensive_words = current_app.config.get("OFFENSIVE_WORDS", [])
    result, detail = evaluate_text(query, offensive_words)
    
    # 感情分析は内部処理として利用する場合でも、
    # テンプレートに渡さなければ表示されません。
    # 例: sentiment_label = cached_analyze_sentiment(query)

    return render_template("result.html", query=query, result=result, detail=detail)
