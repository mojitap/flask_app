from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from models.text_evaluation import evaluate_text, contains_surname
from models.search_history import SearchHistory  # インポート

print("✅ main.py が実行されました")  # ← デバッグ用

main = Blueprint('main', __name__)

@main.route("/")
def home():
    print("✅ / にアクセスされました")  # ← デバッグ用
    return render_template("index.html")

@main.route("/check_surname", methods=["POST"])
def check_surname():
    """ユーザーの入力した文章から特定の苗字を検出する"""
    query = request.form.get("text", "").strip()
    if not query:
        return "<h2>エラー: 文章が入力されていません。</h2>", 400

    # 苗字リストを取得
    surnames = current_app.config.get("SURNAMES", [])

    # 文章内に苗字が含まれているかチェック
    found, surname = contains_surname(query, surnames)
    if found:
        return f"この文章には特定の苗字 '{surname}' が含まれています。"
    else:
        return "この文章には特定の苗字は含まれていません。"

@main.route("/quick_check", methods=["POST"])
@login_required
def quick_check():
    print("✅ /quick_check にアクセス")  # ← デバッグ用
    """SNSでの表現が問題ないかを簡単にチェックする"""
    query = request.form.get("text", "").strip()
    if not query:
        return "<h2>エラー: 検索クエリが空です。</h2>", 400

    # 検索履歴の更新
    SearchHistory.add_or_increment(query)

    # offensive_words のリストを取得
    offensive_words = current_app.config.get("OFFENSIVE_WORDS", [])

    # テキストを評価
    result, detail = evaluate_text(query, offensive_words)

    return render_template("result.html", query=query, result=result, detail=detail)
