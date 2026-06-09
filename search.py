"""設備レコードの検索。"""

from __future__ import annotations

import re
import unicodedata

from parser import EquipmentRecord

SEARCHABLE_FIELDS = (
    "facility_name",
    "equipment_name",
    "manufacturer",
)


def normalize_search_text(text: str) -> str:
    """半角・全角の違いを吸収して比較しやすい形に正規化する。"""
    return unicodedata.normalize("NFKC", str(text)).casefold()


def parse_keywords(query: str) -> list[str]:
    """検索文字列をスペース区切りのキーワードリストに分解する（AND 検索用）。"""
    return [part for part in re.split(r"[\s　]+", query.strip()) if part]


def record_matches(record: EquipmentRecord, keywords: list[str]) -> bool:
    """すべてのキーワードが、いずれかの検索対象項目に含まれるか判定する。"""
    if not keywords:
        return False

    normalized_keywords = [normalize_search_text(keyword) for keyword in keywords]

    for normalized_keyword in normalized_keywords:
        matched = False
        for field_name in SEARCHABLE_FIELDS:
            value = getattr(record, field_name, "")
            if normalized_keyword in normalize_search_text(value):
                matched = True
                break
        if not matched:
            return False
    return True


def search_records(records: list[EquipmentRecord], query: str) -> list[EquipmentRecord]:
    keywords = parse_keywords(query)
    if not keywords:
        return []
    return [record for record in records if record_matches(record, keywords)]
