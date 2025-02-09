from flask import Blueprint, render_template, request
from flask_login import login_required
from models.sentiment import cached_analyze_sentiment
from models.text_evaluation import evaluate_text

main = Blueprint("main", __name__)

@main.route("/")
def home():
    return render_template("index.html")

@main.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    query = request.form.get("text", "").strip()
    if not query:
        return "<h2>エラー: 検索クエリが空です。</h2>", 400

    # 攻撃的な表現を評価
    result, detail = evaluate_text(query)

    # 感情分析
    sentiment_label = cached_analyze_sentiment(query)

    return render_template(
        "result.html", query=query, result=result, detail=detail, sentiment_label=sentiment_label
    )