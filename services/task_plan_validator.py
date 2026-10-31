from models.comparison_config import ComparisonConfig


def validate_plan(plan, reference_sheets, comparison_sheets):
    config = ComparisonConfig.model_validate(plan)
    _validate_side(config.reference, reference_sheets)
    _validate_side(config.comparison, comparison_sheets)
    return config


def _validate_side(side, sheets):
    if side.sheet not in sheets:
        raise ValueError(f"시트를 찾을 수 없습니다: {side.sheet}")
    columns = sheets[side.sheet]["columns"]
    requested = [side.container_column, side.carrier_column, side.amount_column, side.default_amount_column]
    requested += [rule.amount_column for rule in side.amount_rules]
    for column in filter(None, requested):
        if column not in columns:
            raise ValueError(f"'{side.sheet}' 시트에 컬럼 '{column}'이(가) 없습니다.")
