from pathlib import Path
import posixpath
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import pandas as pd

SUPPORTED = {".xlsx", ".xlsm", ".xls"}
PREVIEW_SCAN_ROWS = 200
PREVIEW_ROWS = 8
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _engine(path):
    return "xlrd" if Path(path).suffix.lower() == ".xls" else "openpyxl"


def load_workbook(path):
    """Read sheet names, header candidates, and small previews without loading full data."""
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError("지원하지 않는 파일 형식입니다. xlsx, xlsm, xls 파일을 선택하세요.")
    with pd.ExcelFile(path, engine=_engine(path)) as book:
        return {name: inspect_sheet(book, name) for name in book.sheet_names}


def inspect_sheet(book, name):
    raw = pd.read_excel(book, sheet_name=name, header=None, nrows=PREVIEW_SCAN_ROWS)
    if raw.empty:
        return _metadata(raw, 0)
    return _metadata(raw, _guess_header_row(raw))


def _metadata(raw, header_row, hidden_rows=None):
    hidden_rows_checked = hidden_rows is not None
    hidden_rows = hidden_rows or set()
    if raw.empty:
        return {"header_row": 0, "max_header_row": 0, "columns": [], "column_positions": [],
                "preview": pd.DataFrame(), "rows": None, "data": None, "loaded": False,
                "hidden_rows_checked": hidden_rows_checked, "hidden_data_rows": 0}
    header_values = raw.iloc[header_row].tolist()
    positions, columns = [], []
    for position, value in enumerate(header_values):
        name = str(value).strip() if not pd.isna(value) else ""
        if not name or name.startswith("Unnamed:"):
            continue
        positions.append(position)
        columns.append(name)
    visible_preview_rows = [
        index for index in range(header_row + 1, len(raw))
        if index + 1 not in hidden_rows
    ][:PREVIEW_ROWS]
    preview = raw.iloc[visible_preview_rows, positions].copy()
    preview.columns = columns
    preview.index = range(len(preview))
    return {
        "header_row": header_row,
        "max_header_row": max(0, len(raw) - 1),
        "columns": columns,
        "column_positions": positions,
        "preview": preview,
        "rows": None,
        "data": None,
        "loaded": False,
        "hidden_rows_checked": hidden_rows_checked,
        "hidden_data_rows": sum(row_number > header_row + 1 for row_number in hidden_rows),
    }


def _guess_header_row(raw):
    """Prefer an early, dense row of distinct text labels over later data rows."""
    best_row, best_score = 0, float("-inf")
    for row_index, row in raw.iterrows():
        values = [value for value in row.tolist() if not pd.isna(value)]
        if len(values) < 2:
            continue
        strings = [value for value in values if isinstance(value, str) and value.strip()]
        unique_ratio = len({str(value).strip().casefold() for value in values}) / len(values)
        text_ratio = len(strings) / len(values)
        score = len(values) + 0.9 * text_ratio + 0.45 * unique_ratio - 0.012 * row_index
        if score > best_score:
            best_row, best_score = int(row_index), score
    return best_row


def hidden_row_numbers(path, sheet_name):
    """Return original Excel row numbers hidden in one sheet, without opening Excel."""
    path = Path(path)
    if path.suffix.lower() == ".xls":
        import xlrd
        book = xlrd.open_workbook(str(path), formatting_info=True, on_demand=True)
        sheet = book.sheet_by_name(sheet_name)
        return {index + 1 for index, info in sheet.rowinfo_map.items() if info.hidden}
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        return set()
    with ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationships = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels.findall(f"{{{PKG_REL_NS}}}Relationship")}
        sheet_path = None
        for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
            if sheet.attrib.get("name") == sheet_name:
                target = relationships[sheet.attrib[f"{{{DOC_REL_NS}}}id"]]
                sheet_path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
                break
        if sheet_path is None:
            raise KeyError(f"시트를 찾을 수 없습니다: {sheet_name}")
        root = ET.fromstring(archive.read(sheet_path))
    return {
        int(row.attrib["r"])
        for row in root.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row")
        if row.attrib.get("hidden", "0").casefold() in {"1", "true"}
    }


def load_sheet(path, sheet_name, header_row):
    """Rebuild one sheet's header and visible preview after sheet/header selection."""
    path = Path(path)
    hidden = hidden_row_numbers(path, sheet_name)
    with pd.ExcelFile(path, engine=_engine(path)) as book:
        raw = pd.read_excel(book, sheet_name=sheet_name, header=None, nrows=PREVIEW_SCAN_ROWS)
        chosen_header = min(max(0, header_row), max(0, len(raw) - 1))
        return _metadata(raw, chosen_header, hidden)


def load_sheet_data(path, sheet_name, header_row, visible_only=False):
    """Read one selected sheet, optionally excluding rows hidden in the saved workbook."""
    path = Path(path)
    hidden = hidden_row_numbers(path, sheet_name)
    frame = pd.read_excel(path, sheet_name=sheet_name, header=header_row, engine=_engine(path))
    frame = frame.loc[:, ~frame.columns.astype(str).str.startswith("Unnamed:")]
    frame.columns = [str(column).strip() for column in frame.columns]
    if visible_only:
        visible_mask = [(int(index) + header_row + 2) not in hidden for index in frame.index]
        frame = frame.loc[visible_mask]
    return {
        "header_row": header_row,
        "max_header_row": PREVIEW_SCAN_ROWS - 1,
        "columns": list(frame.columns),
        "column_positions": [],
        "preview": frame.head(PREVIEW_ROWS),
        "rows": len(frame),
        "data": frame,
        "loaded": True,
        "hidden_rows_checked": True,
        "hidden_data_rows": sum(row_number > header_row + 1 for row_number in hidden),
        "visible_only": visible_only,
    }


def load_column_values(path, sheet_name, header_row, column_position, visible_only=True):
    """Read distinct values from one selected column in the chosen row scope."""
    path = Path(path)
    hidden = hidden_row_numbers(path, sheet_name)
    frame = pd.read_excel(path, sheet_name=sheet_name, header=header_row,
                          usecols=[column_position], engine=_engine(path))
    return sorted({
        str(value).strip() for index, value in frame.iloc[:, 0].items()
        if str(value).strip() and (not visible_only or (int(index) + header_row + 2) not in hidden)
    }, key=str.casefold)
