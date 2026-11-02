from __future__ import annotations

from pathlib import Path

from .base import Page, ParsedDocument, ParseError

DELIMITER = " | "


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return " ".join(str(value).split())


def _lines_from_rows(rows: list[list[str]]) -> list[str]:
    lines: list[str] = []
    for row in rows:
        cells = [cell for cell in row if cell]
        if cells:
            lines.append(DELIMITER.join(cells))
    return lines


def _parse_xlsx(path: Path) -> list[Page]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ParseError(f"source.missing_dependency: openpyxl for {path.name}") from exc
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 - openpyxl raises many types
        raise ParseError(f"source.invalid_table: {path.name} is not a readable xlsx") from exc
    pages: list[Page] = []
    for index, sheet in enumerate(workbook.worksheets):
        rows = [[_cell(value) for value in row] for row in sheet.iter_rows(values_only=True)]
        lines = _lines_from_rows(rows)
        if not lines:
            continue
        pages.append(Page(number=index, lines=[sheet.title, *lines]))
    return pages


def _parse_xls(path: Path) -> list[Page]:
    try:
        import xlrd
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ParseError(f"source.missing_dependency: xlrd for {path.name}") from exc
    try:
        workbook = xlrd.open_workbook(str(path))
    except Exception as exc:  # noqa: BLE001 - xlrd raises its own errors
        raise ParseError(f"source.invalid_table: {path.name} is not a readable xls") from exc
    pages: list[Page] = []
    for index, sheet in enumerate(workbook.sheets()):
        rows = [sheet.row_values(row) for row in range(sheet.nrows)]
        lines = _lines_from_rows([[_cell(value) for value in row] for row in rows])
        if not lines:
            continue
        pages.append(Page(number=index, lines=[sheet.name, *lines]))
    return pages


def parse(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        pages = _parse_xlsx(path)
    elif suffix == ".xls":
        pages = _parse_xls(path)
    else:
        raise ParseError(f"source.unsupported_format: {suffix or 'unknown'} for {path.name}")
    if not pages:
        raise ParseError(f"text.empty: no rows in {path.name}")
    return ParsedDocument(pages=pages, parser="table.v1")
