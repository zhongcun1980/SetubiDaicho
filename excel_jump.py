"""Excel の該当セルへジャンプする。"""

from __future__ import annotations

from pathlib import Path

from parser import EquipmentRecord


def jump_to_excel(record: EquipmentRecord) -> None:
    """設備レコードの Excel ファイルを開き、機器名セルへ移動する。"""
    file_path = Path(record.source_file)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel ファイルが見つかりません:\n{file_path}")

    cell_address = f"{record.excel_col}{record.excel_row}"
    absolute_path = str(file_path.resolve())

    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "Excel 連携には pywin32 が必要です。\n"
            "pip install pywin32 を実行してください。"
        ) from exc

    try:
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = True
        workbook = excel.Workbooks.Open(absolute_path)
        worksheet = workbook.Worksheets(record.sheet_name)
        worksheet.Activate()
        worksheet.Range(cell_address).Select()

        window = excel.ActiveWindow
        if window is not None:
            # 機器名の1行上を画面上端にし、選択セルは上端から1行下に表示する
            window.ScrollRow = max(1, record.excel_row - 1)
            window.Activate()
    except Exception as exc:
        raise RuntimeError(
            f"Excel のセル {cell_address} へジャンプできませんでした。\n"
            f"ファイル: {file_path.name}\n"
            f"シート: {record.sheet_name}\n"
            f"{exc}"
        ) from exc
