"""設備台帳 MVP - Excel から抽出した設備情報を一覧表示する。"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from config import DEFAULT_CONFIG_PATH, load_config
from database import load_records, register_records
from excel_jump import jump_to_excel
from loader import LoadResult, load_from_config
from parser import EquipmentRecord
from column_layout import DEFAULT_WIDTHS, MIN_COLUMN_WIDTH, load_column_layout, save_column_layout
from search import search_records
from search_history import add_history, load_history

COLUMNS = (
    ("facility_name", "施設名", 140),
    ("equipment_name", "機器名", 160),
    ("major_category", "大分類", 120),
    ("middle_category", "中分類", 140),
    ("install_year", "設置年", 70),
    ("manufacturer", "メーカー名", 140),
    ("model", "形式", 120),
    ("specification", "仕様", 280),
)

COLUMN_HEADINGS = {col_id: heading for col_id, heading, _ in COLUMNS}
HEADING_DRAG_THRESHOLD = 8
HEADING_BG = "#e8f5e9"
HEADING_BG_ACTIVE = "#c8e6c9"
ROW_BG_ODD = "#ffffff"
ROW_BG_EVEN = "#f2f2f2"
TREE_STYLE = "Equipment.Treeview"
ROW_TAG_ODD = "row_odd"
ROW_TAG_EVEN = "row_even"
ALL_FACILITIES = "（すべて）"


class EquipmentListApp(tk.Tk):
    def __init__(self, config_path: Path) -> None:
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)
        self.load_result = LoadResult(records=load_records(self.config.database_path))
        self.records_by_id: dict[str, EquipmentRecord] = {}
        self.displayed_records: list[EquipmentRecord] = []
        self.sort_column: str | None = None
        self.sort_reverse = False
        self.column_order = [col_id for col_id, _, _ in COLUMNS]
        self._heading_press_col: str | None = None
        self._heading_press_x = 0
        self._heading_dragging = False

        self.title("設備台帳")
        self.geometry("1280x720")
        self.minsize(900, 500)

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._configure_tree_style()
        self._build_ui()

    def _configure_tree_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(
            TREE_STYLE,
            background="white",
            fieldbackground="white",
            rowheight=22,
        )
        style.configure(
            f"{TREE_STYLE}.Heading",
            background=HEADING_BG,
            foreground="#2e7d32",
            font=("", 9, "bold"),
            relief="flat",
        )
        style.map(
            f"{TREE_STYLE}.Heading",
            background=[("active", HEADING_BG_ACTIVE), ("pressed", HEADING_BG_ACTIVE)],
        )
        style.map(
            TREE_STYLE,
            background=[("selected", "#b8d4f0")],
            foreground=[("selected", "black")],
        )

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(12, 10, 12, 6))
        header.pack(fill=tk.X)

        search_row = ttk.Frame(header)
        search_row.pack(fill=tk.X)

        ttk.Label(search_row, text="検索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_combo = ttk.Combobox(
            search_row,
            textvariable=self.search_var,
            values=load_history(),
            width=60,
        )
        self.search_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6))
        self.search_combo.bind("<Return>", self._on_search)
        self.search_combo.bind("<<ComboboxSelected>>", self._on_history_selected)

        ttk.Button(search_row, text="検索", command=self._on_search).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(search_row, text="クリア", command=self._on_clear_search).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Button(search_row, text="登録", command=self._on_register).pack(side=tk.RIGHT)

        result_row = ttk.Frame(header)
        result_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(result_row, text="施設名:").pack(side=tk.LEFT)
        self.facility_var = tk.StringVar(value=ALL_FACILITIES)
        self.facility_combo = ttk.Combobox(
            result_row,
            textvariable=self.facility_var,
            width=28,
            state="readonly",
        )
        self.facility_combo.pack(side=tk.LEFT, padx=(4, 0))
        self.facility_combo.bind("<<ComboboxSelected>>", self._on_facility_selected)
        self._refresh_facility_combo(preserve_selection=False)
        self.result_count_var = tk.StringVar(value="")
        ttk.Label(result_row, textvariable=self.result_count_var).pack(side=tk.RIGHT)

        table_frame = ttk.Frame(self, padding=(12, 0, 12, 6))
        table_frame.pack(fill=tk.BOTH, expand=True)

        column_ids = [col_id for col_id, _, _ in COLUMNS]
        self.tree = ttk.Treeview(
            table_frame,
            columns=column_ids,
            show="headings",
            selectmode="browse",
            style=TREE_STYLE,
        )

        saved_order, saved_widths = load_column_layout()
        self.column_order = saved_order
        for col_id, _, _ in COLUMNS:
            width = saved_widths.get(col_id, DEFAULT_WIDTHS[col_id])
            self.tree.column(
                col_id,
                width=width,
                minwidth=MIN_COLUMN_WIDTH,
                stretch=False,
                anchor=tk.W,
            )

        self._apply_column_layout()
        self.tree.tag_configure(ROW_TAG_ODD, background=ROW_BG_ODD)
        self.tree.tag_configure(ROW_TAG_EVEN, background=ROW_BG_EVEN)

        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_open_excel)
        self.tree.bind("<Return>", self._on_open_excel)
        self.tree.bind("<ButtonPress-1>", self._on_tree_press, add="+")
        self.tree.bind("<B1-Motion>", self._on_tree_drag, add="+")
        self.tree.bind("<ButtonRelease-1>", self._on_tree_release, add="+")

        self.search_combo.focus_set()

    def _sort_key(self, record: EquipmentRecord, column: str) -> str | tuple[int, int | str]:
        value = getattr(record, column, "")
        if column == "install_year":
            text = str(value).strip()
            if text.isdigit():
                return (0, int(text))
            return (1, text)
        return str(value)

    def _sorted_records(self, records: list[EquipmentRecord]) -> list[EquipmentRecord]:
        if not self.sort_column:
            return list(records)
        return sorted(
            records,
            key=lambda record: self._sort_key(record, self.sort_column),
            reverse=self.sort_reverse,
        )

    def _apply_column_layout(self) -> None:
        self.tree["displaycolumns"] = self.column_order
        self._update_headings()

    def _heading_text(self, col_id: str) -> str:
        text = COLUMN_HEADINGS[col_id]
        if col_id == self.sort_column:
            text += " ▼" if self.sort_reverse else " ▲"
        return text

    def _update_headings(self) -> None:
        for col_id in self.column_order:
            self.tree.heading(
                col_id,
                text=self._heading_text(col_id),
                anchor=tk.W,
            )

    def _column_id_at(self, x: int) -> str | None:
        column = self.tree.identify_column(x)
        if not column or column == "#0":
            return None
        index = int(column[1:]) - 1
        if 0 <= index < len(self.column_order):
            return self.column_order[index]
        return None

    def _on_tree_press(self, event: tk.Event) -> None:
        if self.tree.identify_region(event.x, event.y) != "heading":
            return
        col_id = self._column_id_at(event.x)
        if col_id is None:
            return
        self._heading_press_col = col_id
        self._heading_press_x = event.x
        self._heading_dragging = False

    def _on_tree_drag(self, event: tk.Event) -> None:
        if self._heading_press_col is None:
            return
        if abs(event.x - self._heading_press_x) >= HEADING_DRAG_THRESHOLD:
            self._heading_dragging = True
            self.tree.configure(cursor="hand2")

    def _on_tree_release(self, event: tk.Event) -> None:
        if self._heading_press_col is None:
            return

        self.tree.configure(cursor="")
        try:
            if self._heading_dragging and self.tree.identify_region(event.x, event.y) == "heading":
                target_col = self._column_id_at(event.x)
                if target_col and target_col != self._heading_press_col:
                    self._reorder_column(self._heading_press_col, target_col)
            elif not self._heading_dragging and self.tree.identify_region(event.x, event.y) == "heading":
                self._on_sort_column(self._heading_press_col)
        finally:
            self._heading_press_col = None
            self._heading_dragging = False
            if self.tree.identify_region(event.x, event.y) == "heading":
                self._save_column_layout()

    def _reorder_column(self, source_id: str, target_id: str) -> None:
        order = self.column_order.copy()
        order.remove(source_id)
        order.insert(order.index(target_id), source_id)
        self.column_order = order
        self._apply_column_layout()
        self._save_column_layout()

    def _current_column_widths(self) -> dict[str, int]:
        return {
            col_id: int(self.tree.column(col_id, option="width"))
            for col_id, _, _ in COLUMNS
        }

    def _save_column_layout(self) -> None:
        save_column_layout(self.column_order, self._current_column_widths())

    def _on_close(self) -> None:
        self._save_column_layout()
        self.destroy()

    def _render_table(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.records_by_id.clear()
        sorted_records = self._sorted_records(self.displayed_records)
        for index, record in enumerate(sorted_records, start=1):
            item_id = str(index)
            row_tag = ROW_TAG_ODD if index % 2 == 1 else ROW_TAG_EVEN
            self.records_by_id[item_id] = record
            self.tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=self._record_values(record),
                tags=(row_tag,),
            )
        self._update_headings()

    def _populate_table(self, records: list[EquipmentRecord]) -> None:
        self.displayed_records = list(records)
        self._render_table()

    def _on_sort_column(self, column: str) -> None:
        if not self.displayed_records:
            return
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        self._render_table()

    def _refresh_history_combo(self, history: list[str] | None = None) -> None:
        items = history if history is not None else load_history()
        self.search_combo["values"] = items

    def _facility_names(self) -> list[str]:
        names = {
            record.facility_name.strip()
            for record in self.load_result.records
            if record.facility_name.strip()
        }
        return sorted(names)

    def _refresh_facility_combo(self, *, preserve_selection: bool = True) -> None:
        values = [ALL_FACILITIES, *self._facility_names()]
        current = self.facility_var.get()
        self.facility_combo["values"] = values
        if preserve_selection and current in values:
            self.facility_var.set(current)
        else:
            self.facility_var.set(ALL_FACILITIES)

    def _selected_facility(self) -> str:
        facility = self.facility_var.get().strip()
        if facility == ALL_FACILITIES:
            return ""
        return facility

    def _records_for_facility(self, records: list[EquipmentRecord]) -> list[EquipmentRecord]:
        facility = self._selected_facility()
        if not facility:
            return records
        return [record for record in records if record.facility_name == facility]

    def _update_result_count(self, count: int) -> None:
        self.result_count_var.set(f"検索結果: {count} 件")

    def _apply_filters(self, *, save_history: bool = False) -> None:
        query = self.search_var.get()
        facility = self._selected_facility()
        records = self._records_for_facility(self.load_result.records)

        if query.strip():
            results = search_records(records, query)
            if save_history:
                self._refresh_history_combo(add_history(query))
        elif facility:
            results = records
        else:
            results = []

        self._populate_table(results)
        if results or facility or query.strip():
            self._update_result_count(len(results))
        else:
            self.result_count_var.set("")

    def _on_search(self, _event: tk.Event | None = None) -> None:
        self._apply_filters(save_history=True)

    def _on_facility_selected(self, _event: tk.Event | None = None) -> None:
        self._apply_filters()

    def _on_history_selected(self, _event: tk.Event | None = None) -> None:
        selected = self.search_var.get().strip()
        if not selected:
            return
        self._apply_filters()

    def _on_clear_search(self) -> None:
        self.search_var.set("")
        self.facility_var.set(ALL_FACILITIES)
        self._populate_table([])
        self.result_count_var.set("")
        self.search_combo.focus_set()

    @staticmethod
    def _record_values(record: EquipmentRecord) -> tuple[str, ...]:
        return (
            record.facility_name,
            record.equipment_name,
            record.major_category,
            record.middle_category,
            record.install_year,
            record.manufacturer,
            record.model,
            record.specification,
        )

    def _on_open_excel(self, _event: tk.Event | None = None) -> None:
        item_id = self.tree.focus()
        if not item_id or item_id not in self.records_by_id:
            return

        record = self.records_by_id[item_id]
        try:
            jump_to_excel(record)
        except Exception as exc:
            messagebox.showerror(
                "Excel ジャンプエラー",
                (
                    f"{record.equipment_name}\n"
                    f"{Path(record.source_file).name} / {record.sheet_name} / "
                    f"{record.excel_col}{record.excel_row}\n\n"
                    f"{exc}"
                ),
            )

    def _on_register(self) -> None:
        self.configure(cursor="wait")
        self.update_idletasks()
        try:
            try:
                load_result = load_from_config(self.config)
            except FileNotFoundError as exc:
                messagebox.showerror("読み込みエラー", str(exc))
                return

            if not load_result.excel_files:
                messagebox.showwarning(
                    "対象ファイルなし",
                    "条件に一致する Excel ファイルが見つかりませんでした。",
                )
                return

            if not load_result.records:
                messagebox.showwarning("登録不可", "設備データが見つかりませんでした。")
                return

            try:
                result = register_records(load_result.records, self.config.database_path)
            except Exception as exc:
                messagebox.showerror("登録エラー", f"SQLite への登録に失敗しました。\n{exc}")
                return

            self.load_result = load_result
            self._refresh_facility_combo()
            self._apply_filters()

            message = (
                f"{result.registered_count} 件を登録しました。\n"
                f"Excelファイル: {len(load_result.excel_files)} 件\n"
                f"データベース: {result.database_path}"
            )
            if load_result.errors:
                message += f"\n\nExcel読み込みエラー: {len(load_result.errors)} 件"
            if result.errors:
                message += f"\n\n登録エラー: {len(result.errors)} 件"
            if load_result.errors or result.errors:
                messagebox.showwarning("登録完了（一部エラー）", message)
            else:
                messagebox.showinfo("登録完了", message)
        finally:
            self.configure(cursor="")


def main() -> None:
    try:
        load_config()
    except (FileNotFoundError, ValueError) as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("起動エラー", str(exc))
        root.destroy()
        return

    app = EquipmentListApp(DEFAULT_CONFIG_PATH)
    app.mainloop()


if __name__ == "__main__":
    main()
