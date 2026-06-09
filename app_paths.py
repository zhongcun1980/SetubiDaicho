"""アプリケーションの基準ディレクトリを解決する。"""

from __future__ import annotations

import sys
from pathlib import Path


def get_app_dir() -> Path:
    """実行ファイルと同じフォルダを返す。開発時はプロジェクトフォルダ。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_config_path() -> Path:
    return get_app_dir() / "config.json"
