import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # 必要なら

from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models.search_history import SearchHistory
from models.text_evaluation import evaluate_text  # evaluate_text のみインポート
from sqlalchemy import text
from extensions import db

print("✅ main.py が読み込まれました！")

main = Blueprint("main", __name__)

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

@main.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    query = request.form.get("text", "").strip()

    with current_app.app_context():
        # create_app() 側で token 化済みのリストをセットしてある
        offensive_list = current_app.config.get("OFFENSIVE_LIST", [])
        global_whitelist = current_app.config.get("WHITELIST_SET", set())

    # ▼ デバッグ出力例（必要なら）
    # print("[DEBUG] quick_check: len(offensive_list) =", len(offensive_list))
    # if offensive_list:
    #     print("[DEBUG] first item in offensive_list:", offensive_list[0])

    # テキストを判定する
    judgement, detail = evaluate_text(query, offensive_list, global_whitelist)

    # 検索履歴を保存
    SearchHistory.add_or_increment(query)

    return render_template("result.html", query=query, result=judgement, detail=detail)
