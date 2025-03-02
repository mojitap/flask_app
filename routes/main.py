import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # 必要なら

from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models.search_history import SearchHistory
from models.text_evaluation import evaluate_text, load_whitelist
from sqlalchemy import text
from extensions import db

print("✅ main.py が読み込まれました！")

# 先に Blueprint を定義
main = Blueprint("main", __name__)

# カラム一覧を表示するデバッグ用ルート
@main.route("/debug/columns")
def debug_columns():
    rows = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'search_history'
    """)).fetchall()
    print("=== search_history のカラム一覧 ===")
    for r in rows:
        print(r[0])
    return "OK"

@main.route("/")
def home():
    print("✅ / にアクセスされました")
    return render_template("index.html")

whitelist = load_whitelist("data/whitelist.json")

@main.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    query = request.form.get("text", "").strip()

    with current_app.app_context():
        offensive_dict = current_app.config.get("OFFENSIVE_WORDS", {})
        # もし whitelist を使いたいなら
        global_whitelist = load_whitelist("data/whitelist.json")

     judgement, detail = evaluate_text(query, offensive_dict, whitelist=global_whitelist)

    SearchHistory.add_or_increment(query)
    return render_template("result.html", query=query, result=judgement, detail=detail)
