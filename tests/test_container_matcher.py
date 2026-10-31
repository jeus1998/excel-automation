import pandas as pd

from services.container_matcher import reconcile_containers


def test_reconcile_statuses_duplicates_and_filters_non_container_values():
    left = pd.DataFrame({"id": ["SKLU0520719", "TGHU1234567", "MSCU1234567", "MSCU1234567", None, "not a container"]})
    right = pd.DataFrame({"id": [" SKLU0520719 ", "CSQU7654321", "MSCU1234567", " ", "bad"]})
    results = {r.container_number: r for r in reconcile_containers(left, right, "id", "id")}
    assert results["SKLU0520719"].status == "양쪽 파일에 존재"
    assert results["SKLU0520719"].reference_row == 2
    assert results["SKLU0520719"].comparison_row == 2
    assert results["TGHU1234567"].status == "기준 파일에만 존재"
    assert results["CSQU7654321"].status == "비교 파일에만 존재"
    assert results["MSCU1234567"].status == "중복"
    assert results["MSCU1234567"].reference_row == "4, 5"
    assert results["MSCU1234567"].comparison_row == "4"
    assert "not a container" not in results
    assert "" not in results
