import pytest
from services.task_plan_validator import validate_plan


def test_plan_rejects_unknown_sheet_and_column():
    plan = {"service": "container_reconciliation", "reference": {"sheet": "missing", "container_column": "id"}, "comparison": {"sheet": "ok", "container_column": "id"}}
    with pytest.raises(ValueError, match="시트를 찾을 수 없습니다"):
        validate_plan(plan, {"ref": {"columns": ["id"]}}, {"ok": {"columns": ["id"]}})
