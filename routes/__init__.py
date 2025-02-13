from flask import Blueprint

# ルートの Blueprint をインポート
from .auth import auth

# Blueprint をエクスポート
__all__ = ["main", "auth"]
