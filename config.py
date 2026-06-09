"""アプリケーション設定の読み込み。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app_paths import get_app_dir, get_config_path

DEFAULT_CONFIG_PATH = get_config_path()


@dataclass
class AppConfig:
    root_folder: Path
    filename_contains: str = "診断表"
    recursive: bool = True
    extensions: list[str] = field(default_factory=lambda: [".xls", ".xlsx"])
    database_path: Path = field(default_factory=lambda: Path("data.db"))

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        app_dir = get_app_dir()
        extensions = data.get("extensions", [".xls", ".xlsx"])
        db_path = Path(data.get("database_path", "data.db"))
        if not db_path.is_absolute():
            db_path = app_dir / db_path
        return cls(
            root_folder=Path(data["root_folder"]),
            filename_contains=data.get("filename_contains", "診断表"),
            recursive=bool(data.get("recursive", True)),
            extensions=[str(ext).lower() for ext in extensions],
            database_path=db_path,
        )


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {config_path}\n"
            f"search.exe と同じフォルダに config.json を配置してください。"
        )

    with config_path.open(encoding="utf-8") as fp:
        data = json.load(fp)

    if "root_folder" not in data:
        raise ValueError("設定ファイルに root_folder が指定されていません")

    return AppConfig.from_dict(data)
