import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # 必要なら

from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from models.search_history import SearchHistory
from models.text_evaluation import load_whitelist
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
    if not query:
        return "<h2>エラー: 検索クエリが空です。</h2>", 400

    # Render.com でダウンロード/ロード済みの辞書を取得
    offensive_dict = current_app.config.get("OFFENSIVE_WORDS", {})
    
    # ホワイトリスト対応で判定する
    judgement, detail = evaluate_text(query, offensive_dict, whitelist=whitelist)

    # 検索履歴を保存
    SearchHistory.add_or_increment(query)

    # テンプレートに渡す変数は judgement, detail でよい
    return render_template("result.html", query=query, result=judgement, detail=detail)
