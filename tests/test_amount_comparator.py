from decimal import Decimal
import pandas as pd

from models.comparison_config import ComparisonConfig
from services.amount_comparator import compare_amounts
from services.data_normalizer import parse_amount, normalize_container, is_valid_container_number


def test_amount_rules_difference_rows_and_filters_non_container_values():
    left = pd.DataFrame({
        "id": ["SKLU0520719", "TGHU1234567", "MSCU1234567", "invalid"],
        "carrier": ["special", "other", "other", "other"],
        "invoice": ["1,200", "bad", 0, 500],
        "pay": [1000, 3, 0, 500],
    })
    right = pd.DataFrame({"id": ["SKLU0520719", "TGHU1234567", "MSCU1234567", "bad"], "amount": [1250, 3, 0, 500]})
    config = ComparisonConfig.model_validate({
        "service": "amount_comparison",
        "reference": {"sheet": "s", "container_column": "id", "carrier_column": "carrier", "default_amount_column": "pay", "amount_rules": [{"value": "special", "amount_column": "invoice"}]},
        "comparison": {"sheet": "s", "container_column": "id", "amount_column": "amount"},
    })
    got = {r.container_number: r for r in compare_amounts(left, right, config)}
    assert got["SKLU0520719"].difference == Decimal("50")
    assert got["SKLU0520719"].status == "금액 불일치"
    assert got["SKLU0520719"].reference_amount == Decimal("1200")
    assert got["SKLU0520719"].comparison_amount == Decimal("1250")
    assert got["SKLU0520719"].reference_row == 2
    assert got["SKLU0520719"].comparison_row == 2
    assert got["TGHU1234567"].status == "금액 일치"
    assert got["MSCU1234567"].reference_amount == Decimal("0")
    assert "invalid" not in got and "bad" not in got


def test_normalization_and_container_pattern():
    assert normalize_container(" ab- 12 ") == "AB- 12"
    assert is_valid_container_number("sklu0520719")
    assert not is_valid_container_number("SKLU052071")
    assert not is_valid_container_number("SKLU05207191")
    assert not is_valid_container_number("SKLU-0520719")
    assert parse_amount("(1,250.50)") == Decimal("-1250.50")
    assert parse_amount(0) == Decimal("0")
    assert parse_amount("") is None


def test_duplicate_result_lists_every_source_row():
    left = pd.DataFrame({"id": ["SKLU0520719", "SKLU0520719"], "carrier": ["A", "A"], "amount": [10, 11]})
    right = pd.DataFrame({"id": ["SKLU0520719", "SKLU0520719", "SKLU0520719"], "amount": [12, 13, 14]})
    config = ComparisonConfig.model_validate({
        "service": "amount_comparison",
        "reference": {"sheet": "s", "container_column": "id", "carrier_column": "carrier", "default_amount_column": "amount"},
        "comparison": {"sheet": "s", "container_column": "id", "amount_column": "amount"},
    })
    results = compare_amounts(left, right, config)
    assert len(results) == 5
    assert all(result.status == "중복" for result in results)
    assert [result.reference_row for result in results] == [2, 3, None, None, None]
    assert [result.comparison_row for result in results] == [None, None, 2, 3, 4]
    assert [result.reference_amount for result in results[:2]] == [Decimal("10"), Decimal("11")]
    assert [result.comparison_amount for result in results[2:]] == [Decimal("12"), Decimal("13"), Decimal("14")]
    assert all(result.carrier == "A" for result in results)
    assert all(result.applied_amount_column == "amount" for result in results)
    assert all(result.detail == "SKLU0520719 · 기준 2건, 비교 3건 중복" for result in results)


def test_missing_file_status_still_shows_available_amount_and_row():
    left = pd.DataFrame({
        "id": ["SKLU0520719"], "carrier": ["광양트랙타"], "charge": [85000],
    })
    right = pd.DataFrame({"id": ["TGHU1234567"], "amount": [92000]})
    config = ComparisonConfig.model_validate({
        "service": "amount_comparison",
        "reference": {
            "sheet": "기준", "container_column": "id", "carrier_column": "carrier",
            "default_amount_column": "charge",
        },
        "comparison": {"sheet": "비교", "container_column": "id", "amount_column": "amount"},
    })

    results = {result.container_number: result for result in compare_amounts(left, right, config)}
    missing_comparison = results["SKLU0520719"]
    assert missing_comparison.status == "비교 파일 누락"
    assert missing_comparison.reference_row == 2
    assert missing_comparison.reference_amount == Decimal("85000")
    assert missing_comparison.carrier == "광양트랙타"
    assert missing_comparison.applied_amount_column == "charge"

    missing_reference = results["TGHU1234567"]
    assert missing_reference.status == "기준 파일 누락"
    assert missing_reference.comparison_row == 2
    assert missing_reference.comparison_amount == Decimal("92000")
