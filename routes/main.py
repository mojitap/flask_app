import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # ✅ `flask_app` を Python パスに追加

from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from models.text_evaluation import evaluate_text  # ← ここで 'models' が見つかるようになる！
from models.search_history import SearchHistory

print("✅ main.py が読み込まれました！")

main = Blueprint('main', __name__)

@main.route("/")
def home():
    print("✅ / にアクセスされました")
    return render_template("index.html")

# 使用例
def contains_surname(text, surnames):
    for surname in surnames:
        if surname in text:
            return True, surname  # ✅ 関数内にあるからOK
    return False, None  # ここも関数内に入れる
    
@main.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    query = request.form.get("text", "").strip()
    if not query:
        return "<h2>エラー: 検索クエリが空です。</h2>", 400

    # 検索履歴の更新
    SearchHistory.add_or_increment(query)
    
    # 苗字チェックは evaluate_text に統合されている
    offensive_words = current_app.config.get("OFFENSIVE_WORDS", [])
    result, detail = evaluate_text(query, offensive_words)
    return render_template("result.html", query=query, result=result, detail=detail)
    
    # その他の評価
    offensive_words = current_app.config.get("OFFENSIVE_WORDS", [])
    result, detail = evaluate_text(query, offensive_words)
    return render_template("result.html", query=query, result=result, detail=detail)
