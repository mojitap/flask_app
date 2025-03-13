import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # 必要なら

from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from models.search_history import SearchHistory
# ここで evaluate_text のみを import
from models.text_evaluation import evaluate_text
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
        # 形態素解析済みの offensive_list
        offensive_list = current_app.config.get("OFFENSIVE_LIST", [])
        # whitelist
        global_whitelist = current_app.config.get("WHITELIST_SET", set())

    # ▼ デバッグ出力
    print("[DEBUG] quick_check: offensive_dict keys =", offensive_dict.keys() if isinstance(offensive_dict, dict) else "No dict")
    if isinstance(offensive_dict, dict) and "offensive" in offensive_dict:
        print("[DEBUG] first 10 words from offensive:", offensive_dict["offensive"][:10])
    else:
        print("[DEBUG] 'offensive' key not found in offensive_dict")
        
    # テキストを判定する
    judgement, detail = evaluate_text(query, offensive_list, global_whitelist)

    # 検索履歴を保存
    SearchHistory.add_or_increment(query)

    # 判定結果を result.html に渡してレンダリング
    return render_template("result.html", query=query, result=judgement, detail=detail)
