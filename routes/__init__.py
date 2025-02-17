from flask import Blueprint

# ルートの Blueprint をインポート
from routes.auth import auth  # ✅

# Blueprint をエクスポート
__all__ = ["main", "auth"]
