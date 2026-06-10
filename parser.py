"""設備台帳 Excel から帳票ブロックを解析して設備情報を抽出する。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import xlrd

SHEET_PATTERN = re.compile(r"^帳票\d+$")
BLOCK_MARKERS = (
    "機械設備",
    "電気計装設備",
    "建築電気設備",
    "建築",
    "土木",
)
MAX_BLOCK_ROWS = 59


@dataclass
class EquipmentRecord:
    source_file: str
    sheet_name: str
    block_row: int
    excel_row: int
    excel_col: str
    facility_name: str
    equipment_name: str
    major_category: str
    middle_category: str
    install_year: str
    manufacturer: str
    model: str
    specification: str


def col_to_letter(col: int) -> str:
    """0始まりの列番号を Excel 列名 (A, B, ...) に変換する。"""
    index = col + 1
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def normalize(text: str) -> str:
    return re.sub(r"[\s　\r\n]+", "", str(text))


def cell_str(sheet: xlrd.sheet.Sheet, row: int, col: int) -> str:
    if row >= sheet.nrows or col >= sheet.ncols:
        return ""
    value = sheet.cell_value(row, col)
    if value == "":
        return ""
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value).strip()


def is_block_title(text: str) -> bool:
    if "診断表" not in text:
        return False
    return any(marker in text for marker in BLOCK_MARKERS)


def find_blocks(sheet: xlrd.sheet.Sheet) -> list[int]:
    starts: list[int] = []
    for row in range(sheet.nrows):
        text = cell_str(sheet, row, 1)
        if text and is_block_title(text):
            starts.append(row)
    return starts


def row_cells(sheet: xlrd.sheet.Sheet, row: int) -> list[tuple[int, str]]:
    cells: list[tuple[int, str]] = []
    for col in range(sheet.ncols):
        text = cell_str(sheet, row, col)
        if text:
            cells.append((col, text))
    return cells


def value_to_right(
    sheet: xlrd.sheet.Sheet,
    row: int,
    label_col: int,
    *,
    skip_labels: bool = True,
) -> str:
    for col in range(label_col + 1, sheet.ncols):
        text = cell_str(sheet, row, col)
        if not text:
            continue
        if skip_labels and _looks_like_label(text):
            continue
        return text
    return ""


def _looks_like_label(text: str) -> bool:
    normalized = normalize(text)
    label_keywords = (
        "大分類",
        "中分類",
        "小分類",
        "設置年",
        "標準耐用年数",
        "調査年月日",
        "機器名",
        "仕様",
        "メーカー",
        "形式",
    )
    return any(keyword in normalized for keyword in label_keywords)


def find_label_row(
    sheet: xlrd.sheet.Sheet,
    start_row: int,
    end_row: int,
    *keywords: str,
) -> tuple[int, int, str] | None:
    for row in range(start_row, end_row):
        for col, text in row_cells(sheet, row):
            normalized = normalize(text)
            if any(keyword in normalized for keyword in keywords):
                return row, col, text
    return None


def extract_specification(sheet: xlrd.sheet.Sheet, start_row: int, end_row: int) -> str:
    install_row = find_label_row(sheet, start_row, end_row, "設置年")
    install_row_index = install_row[0] if install_row else -1
    for row in range(start_row, end_row):
        for col, text in row_cells(sheet, row):
            if "仕様" not in normalize(text):
                continue
            # 設置年と同じ行の左側「仕様」はセクション見出しなので除外する
            if row == install_row_index and col <= 2:
                continue
            return value_to_right(sheet, row, col, skip_labels=False)
    return ""


def parse_block(
    sheet: xlrd.sheet.Sheet,
    start_row: int,
    *,
    source_file: str,
    sheet_name: str,
) -> EquipmentRecord:
    next_starts = [row for row in find_blocks(sheet) if row > start_row]
    end_row = min(start_row + MAX_BLOCK_ROWS, next_starts[0] if next_starts else sheet.nrows)

    facility_name = cell_str(sheet, start_row + 1, 1)

    equipment_name = ""
    excel_row = start_row + 3
    excel_col = "D"
    equipment_hit = find_label_row(sheet, start_row, end_row, "機器名")
    if equipment_hit:
        row, col, _ = equipment_hit
        equipment_name = value_to_right(sheet, row, col)
        if equipment_name:
            value_col = col + 1
            while value_col < sheet.ncols:
                if cell_str(sheet, row, value_col) == equipment_name:
                    excel_row = row + 1
                    excel_col = col_to_letter(value_col)
                    break
                value_col += 1
            else:
                excel_row = row + 1
                excel_col = col_to_letter(col + 1)

    major_category = ""
    middle_category = ""
    category_hit = find_label_row(sheet, start_row, end_row, "大分類")
    if category_hit:
        row, col, _ = category_hit
        major_category = value_to_right(sheet, row, col)
        middle_hit = find_label_row(sheet, row, row + 1, "中分類")
        if middle_hit:
            middle_row, middle_col, _ = middle_hit
            middle_category = value_to_right(sheet, middle_row, middle_col)

    install_year = ""
    install_hit = find_label_row(sheet, start_row, end_row, "設置年")
    if install_hit:
        row, col, _ = install_hit
        install_year = value_to_right(sheet, row, col)

    manufacturer = ""
    maker_hit = find_label_row(sheet, start_row, end_row, "メーカー")
    if maker_hit:
        row, col, _ = maker_hit
        manufacturer = value_to_right(sheet, row, col)

    model = ""
    model_hit = find_label_row(sheet, start_row, end_row, "形式")
    if model_hit:
        row, col, _ = model_hit
        model = value_to_right(sheet, row, col)

    specification = extract_specification(sheet, start_row, end_row)

    return EquipmentRecord(
        source_file=source_file,
        sheet_name=sheet_name,
        block_row=start_row + 1,
        excel_row=excel_row,
        excel_col=excel_col,
        facility_name=facility_name,
        equipment_name=equipment_name,
        major_category=major_category,
        middle_category=middle_category,
        install_year=install_year,
        manufacturer=manufacturer,
        model=model,
        specification=specification,
    )


def parse_workbook(path: str | Path) -> list[EquipmentRecord]:
    path = Path(path)
    workbook = xlrd.open_workbook(str(path))
    records: list[EquipmentRecord] = []

    for sheet_name in workbook.sheet_names():
        if not SHEET_PATTERN.match(sheet_name):
            continue
        sheet = workbook.sheet_by_name(sheet_name)
        for start_row in find_blocks(sheet):
            records.append(
                parse_block(
                    sheet,
                    start_row,
                    source_file=str(path),
                    sheet_name=sheet_name,
                )
            )

    return records


def parse_files(paths: list[str | Path]) -> list[EquipmentRecord]:
    records: list[EquipmentRecord] = []
    for path in paths:
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
        records.extend(parse_workbook(file_path))
    return records
