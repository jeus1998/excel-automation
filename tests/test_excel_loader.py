import pandas as pd

from services.excel_loader import load_column_values, load_sheet, load_sheet_data, load_workbook


def test_detects_header_after_title_rows_and_allows_override(tmp_path):
    path = tmp_path / "variable_header.xlsx"
    rows = [
        ["일보 자료", None, None],
        [None, None, None],
        ["컨테이너 번호", "운송사", "하불액"],
        ["ABCU1234567", "A사", "1,200"],
        ["DEFU1234567", "B사", "900"],
    ]
    pd.DataFrame(rows).to_excel(path, sheet_name="일보", header=False, index=False)

    loaded = load_workbook(path)["일보"]
    assert loaded["header_row"] == 2
    assert loaded["columns"] == ["컨테이너 번호", "운송사", "하불액"]
    assert loaded["data"] is None  # File selection only inspects the preview.
    assert len(loaded["preview"]) == 2

    manually_selected = load_sheet(path, "일보", 2)
    assert manually_selected["columns"] == loaded["columns"]
    full = load_sheet_data(path, "일보", 2)
    assert full["loaded"] and len(full["data"]) == 2
    assert load_column_values(path, "일보", 2, 1) == ["A사", "B사"]
