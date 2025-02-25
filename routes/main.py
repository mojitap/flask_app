import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # 必要なら

# ★ ここを修正 ★
from flask import Blueprint, render_template, request, current_app, flash, redirect, url_for
from flask_login import login_required, current_user

from models.user import User
from models.search_history import SearchHistory
from models.text_evaluation import evaluate_text, load_whitelist
from sqlalchemy import text
from extensions import db

print("✅ main.py が読み込まれました！")

main = Blueprint("main", __name__)

whitelist = load_whitelist("data/whitelist.json")

def check_text_risk(text):
    """テキストを評価する補助関数"""
    offensive_dict = current_app.config.get("OFFENSIVE_WORDS", {})
    judgement, detail = evaluate_text(text, offensive_dict, whitelist=whitelist)
    return judgement, detail

@main.route("/")
def home():
    print("✅ / にアクセスされました")
    return render_template("index.html")

@main.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    # ★ current_user や flash, redirect, url_for を使うには import が必要 ★

    # もしプレミアムユーザーだけに検索結果を表示したいなら:
    if not current_user.is_premium:
        flash("検索結果を表示するにはプレミアムプランに加入してください！")
        # checkout ルートは app.py で @app.route("/checkout") となっている想定
        return redirect(url_for("checkout"))  # エンドポイント名が checkout なら OK

    text = request.form.get("text", "").strip()
    if not text:
        flash("テキストが空です。")
        return redirect(url_for("main.home"))  # Blueprint 内の home() なら "main.home"

    # テキストを分析
    judgement, detail = check_text_risk(text)

    # 検索履歴を保存
    SearchHistory.add_or_increment(text)

    return render_template("result.html", query=text, result=judgement, detail=detail)
