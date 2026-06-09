"""設定に基づいて Excel ファイルを探索し、設備情報を一括読み込みする。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from config import AppConfig
from parser import EquipmentRecord, parse_workbook


@dataclass
class LoadResult:
    records: list[EquipmentRecord] = field(default_factory=list)
    excel_files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def discover_excel_files(config: AppConfig) -> list[Path]:
    root = config.root_folder
    if not root.exists():
        raise FileNotFoundError(f"読み込み対象フォルダが見つかりません: {root}")

    extensions = {ext.lower() for ext in config.extensions}
    keyword = config.filename_contains
    files: list[Path] = []

    iterator = root.rglob("*") if config.recursive else root.glob("*")
    for path in iterator:
        if not path.is_file():
            continue
        if path.suffix.lower() not in extensions:
            continue
        if keyword and keyword not in path.name:
            continue
        files.append(path)

    return sorted(files, key=lambda p: str(p).lower())


def load_from_config(config: AppConfig) -> LoadResult:
    result = LoadResult()
    result.excel_files = discover_excel_files(config)

    for excel_path in result.excel_files:
        try:
            result.records.extend(parse_workbook(excel_path))
        except Exception as exc:
            result.errors.append(f"{excel_path}: {exc}")

    return result
