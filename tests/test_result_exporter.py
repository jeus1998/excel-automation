from pathlib import Path
from models.comparison_result import ComparisonResult
from services.result_exporter import export_results
import pandas as pd


def test_export_creates_expected_sheets(tmp_path: Path):
    path = tmp_path / "out.xlsx"
    export_results([ComparisonResult("X", status="금액 불일치")], path, {"service": "test"})
    book = pd.ExcelFile(path)
    assert book.sheet_names == ["전체 결과", "불일치", "기준 파일 누락", "비교 파일 누락", "중복", "데이터 오류", "AI 작업 계획"]
    assert len(pd.read_excel(path, sheet_name="불일치")) == 1
