"""設備情報の SQLite 登録。"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from parser import EquipmentRecord

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    facility_name TEXT NOT NULL DEFAULT '',
    equipment_name TEXT NOT NULL DEFAULT '',
    major_category TEXT NOT NULL DEFAULT '',
    middle_category TEXT NOT NULL DEFAULT '',
    install_year TEXT NOT NULL DEFAULT '',
    manufacturer TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    specification TEXT NOT NULL DEFAULT '',
    source_file TEXT NOT NULL,
    source_file_name TEXT NOT NULL DEFAULT '',
    sheet_name TEXT NOT NULL,
    block_row INTEGER NOT NULL,
    excel_row INTEGER NOT NULL,
    excel_col TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    UNIQUE(source_file, sheet_name, block_row)
);
"""


@dataclass
class RegisterResult:
    registered_count: int
    database_path: Path
    errors: list[str]


def init_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


def register_records(records: list[EquipmentRecord], db_path: Path) -> RegisterResult:
    init_database(db_path)
    imported_at = datetime.now().isoformat(timespec="seconds")
    errors: list[str] = []
    registered_count = 0

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM equipment")
        for record in records:
            try:
                conn.execute(
                    """
                    INSERT INTO equipment (
                        facility_name,
                        equipment_name,
                        major_category,
                        middle_category,
                        install_year,
                        manufacturer,
                        model,
                        specification,
                        source_file,
                        source_file_name,
                        sheet_name,
                        block_row,
                        excel_row,
                        excel_col,
                        imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.facility_name,
                        record.equipment_name,
                        record.major_category,
                        record.middle_category,
                        record.install_year,
                        record.manufacturer,
                        record.model,
                        record.specification,
                        record.source_file,
                        Path(record.source_file).name,
                        record.sheet_name,
                        record.block_row,
                        record.excel_row,
                        record.excel_col,
                        imported_at,
                    ),
                )
                registered_count += 1
            except sqlite3.Error as exc:
                errors.append(
                    f"{Path(record.source_file).name} / {record.sheet_name} / "
                    f"行{record.block_row}: {exc}"
                )
        conn.commit()

    return RegisterResult(
        registered_count=registered_count,
        database_path=db_path,
        errors=errors,
    )


def count_records(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()
    return int(row[0]) if row else 0


def load_records(db_path: Path) -> list[EquipmentRecord]:
    if not db_path.exists():
        return []

    init_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                facility_name,
                equipment_name,
                major_category,
                middle_category,
                install_year,
                manufacturer,
                model,
                specification,
                source_file,
                sheet_name,
                block_row,
                excel_row,
                excel_col
            FROM equipment
            ORDER BY id
            """
        ).fetchall()

    return [
        EquipmentRecord(
            facility_name=row["facility_name"],
            equipment_name=row["equipment_name"],
            major_category=row["major_category"],
            middle_category=row["middle_category"],
            install_year=row["install_year"],
            manufacturer=row["manufacturer"],
            model=row["model"],
            specification=row["specification"],
            source_file=row["source_file"],
            sheet_name=row["sheet_name"],
            block_row=row["block_row"],
            excel_row=row["excel_row"],
            excel_col=row["excel_col"],
        )
        for row in rows
    ]
