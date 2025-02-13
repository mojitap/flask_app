# routes/__init__.py

from flask import Blueprint
# いま「from .auth import auth」のみだが、
# main.pyのBlueprintオブジェクトも同時にインポートする。
from .main import main    # 追加
from .auth import auth

__all__ = ["main", "auth"]
