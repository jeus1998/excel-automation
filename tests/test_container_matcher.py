import pandas as pd

from services.container_matcher import reconcile_containers


def test_reconcile_statuses_duplicates_and_filters_non_container_values():
    left = pd.DataFrame({"id": ["SKLU0520719", "TGHU1234567", "MSCU1234567", "MSCU1234567", None, "not a container"]})
    right = pd.DataFrame({"id": [" SKLU0520719 ", "CSQU7654321", "MSCU1234567", " ", "bad"]})
    rows = reconcile_containers(left, right, "id", "id")
    results = {r.container_number: [item for item in rows if item.container_number == r.container_number] for r in rows}
    assert results["SKLU0520719"][0].status == "양쪽 파일에 존재"
    assert results["SKLU0520719"][0].reference_row == 2
    assert results["SKLU0520719"][0].comparison_row == 2
    assert results["TGHU1234567"][0].status == "기준 파일에만 존재"
    assert results["CSQU7654321"][0].status == "비교 파일에만 존재"
    duplicate_rows = results["MSCU1234567"]
    assert len(duplicate_rows) == 3
    assert [row.reference_row for row in duplicate_rows] == [4, 5, None]
    assert [row.comparison_row for row in duplicate_rows] == [None, None, 4]
    assert all(row.detail == "MSCU1234567 · 기준 2건, 비교 1건 중복" for row in duplicate_rows)
    assert "not a container" not in results
    assert "" not in results
