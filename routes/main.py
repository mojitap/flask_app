# routes/main.py
import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # 必要なら

from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from models.search_history import SearchHistory
from ..models.text_evaluation import evaluate_text

print("✅ main.py が読み込まれました！")

main = Blueprint("main", __name__)

@main.route("/")
def home():
    print("✅ / にアクセスされました")
    return render_template("index.html")

@main.route("/quick_check", methods=["POST"])
@login_required  # 認証不要なら外す
def quick_check():
    query = request.form.get("text", "").strip()
    if not query:
        return "<h2>エラー: 検索クエリが空です。</h2>", 400

    # 検索履歴を保存など
    SearchHistory.add_or_increment(query)

    # 辞書を取得
    offensive_dict = current_app.config.get("OFFENSIVE_WORDS", {})
    result, detail = evaluate_text(query, offensive_dict)

    return render_template("result.html", query=query, result=result, detail=detail)
