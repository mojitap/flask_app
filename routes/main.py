from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from models.text_evaluation import evaluate_text
from models.search_history import SearchHistory  # インポート
from models.text_evaluation import contains_surname

main = Blueprint('main', __name__)

@main.route("/")
def home():
    return render_template("index.html")

# 使用例
text = "サンプル文章に安威という名前が含まれています。"
surnames = load_surnames()
# evaluate_text の中で苗字をチェック
found, surname = contains_surname(text, load_surnames())
if found:
    return f"この文章には特定の苗字 '{surname}' が含まれています。", surname
    
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
