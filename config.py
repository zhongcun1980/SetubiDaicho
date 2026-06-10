"""アプリケーション設定の読み込み。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
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


def _escape_backslashes_in_json_strings(text: str) -> str:
    """JSON 文字列内の未エスケープ \\ を \\\\ に補正する（Windows パス用）。"""
    out: list[str] = []
    in_string = False
    i = 0
    while i < len(text):
        char = text[i]
        if not in_string:
            out.append(char)
            if char == '"':
                in_string = True
            i += 1
            continue

        if char == '"':
            out.append(char)
            in_string = False
            i += 1
            continue

        if char != "\\":
            out.append(char)
            i += 1
            continue

        if i + 1 >= len(text):
            out.append("\\\\")
            i += 1
            continue

        next_char = text[i + 1]
        if next_char == "u":
            hex_part = text[i + 2 : i + 6]
            if len(hex_part) == 4 and all(ch in "0123456789abcdefABCDEF" for ch in hex_part):
                out.append(text[i : i + 6])
                i += 6
                continue
            out.append("\\\\")
            i += 1
            continue

        if next_char in '"\\/':
            out.append(char)
            out.append(next_char)
            i += 2
            continue

        out.append("\\\\")
        i += 1

    return "".join(out)


def _load_config_data(text: str, config_path: Path) -> dict:
    try:
        return json.loads(text)
    except JSONDecodeError as first_error:
        try:
            return json.loads(_escape_backslashes_in_json_strings(text))
        except JSONDecodeError as second_error:
            raise ValueError(
                f"設定ファイルの形式が正しくありません: {config_path}\n"
                "フォルダパスは次のいずれかの形式で指定できます。\n"
                "  C:/Users/設備台帳\n"
                "  C:\\Users\\設備台帳\n"
                f"詳細: {second_error}"
            ) from first_error


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(
            f"設定ファイルが見つかりません: {config_path}\n"
            f"search.exe と同じフォルダに config.json を配置してください。"
        )

    text = config_path.read_text(encoding="utf-8")
    data = _load_config_data(text, config_path)

    if "root_folder" not in data:
        raise ValueError("設定ファイルに root_folder が指定されていません")

    return AppConfig.from_dict(data)
