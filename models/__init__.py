# models パッケージを認識させるためのファイル
# ここで特定のモデルを一括インポートする場合もあり
from .user import User
from .search_history import SearchHistory
from .text_evaluation import evaluate_text  # ✅ 追加

__all__ = ["User", "SearchHistory"]
