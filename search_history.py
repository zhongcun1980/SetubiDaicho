"""検索履歴の保存と読み込み。"""

from __future__ import annotations

import json
from pathlib import Path

from app_paths import get_app_dir

HISTORY_PATH = get_app_dir() / "search_history.json"
MAX_HISTORY = 30


def load_history() -> list[str]:
    if not HISTORY_PATH.exists():
        return []
    try:
        with HISTORY_PATH.open(encoding="utf-8") as fp:
            data = json.load(fp)
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [str(item) for item in data if str(item).strip()]


def save_history(queries: list[str]) -> None:
    with HISTORY_PATH.open("w", encoding="utf-8") as fp:
        json.dump(queries[:MAX_HISTORY], fp, ensure_ascii=False, indent=2)


def add_history(query: str) -> list[str]:
    normalized = query.strip()
    if not normalized:
        return load_history()

    history = load_history()
    if normalized in history:
        history.remove(normalized)
    history.insert(0, normalized)
    save_history(history[:MAX_HISTORY])
    return history[:MAX_HISTORY]
