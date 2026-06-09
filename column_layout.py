"""一覧の列順・列幅の保存と読み込み。"""

from __future__ import annotations

import json
from pathlib import Path

from app_paths import get_app_dir

LAYOUT_PATH = get_app_dir() / "column_layout.json"

DEFAULT_ORDER = [
    "facility_name",
    "equipment_name",
    "major_category",
    "middle_category",
    "install_year",
    "manufacturer",
    "model",
    "specification",
]

MIN_COLUMN_WIDTH = 40

DEFAULT_WIDTHS = {
    "facility_name": 140,
    "equipment_name": 160,
    "major_category": 120,
    "middle_category": 140,
    "install_year": 70,
    "manufacturer": 140,
    "model": 120,
    "specification": 280,
}


def _normalize_order(order: list[str]) -> list[str]:
    if set(order) != set(DEFAULT_ORDER):
        return DEFAULT_ORDER.copy()
    return order


def _normalize_widths(widths: dict[str, int]) -> dict[str, int]:
    result = DEFAULT_WIDTHS.copy()
    for col_id, width in widths.items():
        if col_id in result and isinstance(width, int) and width > 0:
            result[col_id] = width
    return result


def load_column_layout() -> tuple[list[str], dict[str, int]]:
    if not LAYOUT_PATH.exists():
        return DEFAULT_ORDER.copy(), DEFAULT_WIDTHS.copy()
    try:
        with LAYOUT_PATH.open(encoding="utf-8") as fp:
            data = json.load(fp)
    except (json.JSONDecodeError, OSError):
        return DEFAULT_ORDER.copy(), DEFAULT_WIDTHS.copy()

    order = _normalize_order(data.get("column_order", DEFAULT_ORDER))
    widths = _normalize_widths(data.get("column_widths", {}))
    return order, widths


def save_column_layout(column_order: list[str], column_widths: dict[str, int]) -> None:
    data = {
        "column_order": _normalize_order(column_order),
        "column_widths": _normalize_widths(column_widths),
    }
    with LAYOUT_PATH.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
