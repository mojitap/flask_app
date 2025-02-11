# models パッケージを認識させるためのファイル
# ここで特定のモデルを一括インポートする場合もあり
from .user import User
from .search_history import SearchHistory

__all__ = ["User", "SearchHistory"]