from flask import Blueprint

# ルートの Blueprint をインポート
from .main import main
from .auth import auth

# Blueprint をエクスポート
__all__ = ["main", "auth"]
