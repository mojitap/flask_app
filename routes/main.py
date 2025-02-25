import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # 必要なら

from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from models.user import User
from models.search_history import SearchHistory
from models.text_evaluation import evaluate_text, load_whitelist
from sqlalchemy import text
from extensions import db

print("✅ main.py が読み込まれました！")

# 先に Blueprint を定義
main = Blueprint("main", __name__)

# ホワイトリストのロード
whitelist = load_whitelist("data/whitelist.json")

# 🔹 テキストのリスク判定関数
def check_text_risk(text):
    offensive_dict = current_app.config.get("OFFENSIVE_WORDS", {})
    judgement, detail = evaluate_text(text, offensive_dict, whitelist=whitelist)
    return judgement, detail

@main.route("/")
def home():
    print("✅ / にアクセスされました")
    return render_template("index.html")

@main.route("/quick_check", methods=["POST"])
@login_required  # 🔹 ログイン必須
def quick_check():
    if not current_user.is_premium:
        flash("検索結果を表示するにはプレミアムプランに加入してください！")
        return redirect(url_for("checkout"))  # 🔹 課金ページへリダイレクト

    text = request.form.get("text", "").strip()
    
    # 🔹 ここで「テキストを分析する関数」を呼び出す
    judgement, detail = check_text_risk(text)

    # 🔹 検索履歴を保存
    SearchHistory.add_or_increment(text)

    return render_template("result.html", query=text, result=judgement, detail=detail)
