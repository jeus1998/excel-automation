from decimal import Decimal, InvalidOperation
import re


CONTAINER_PATTERN = re.compile(r"^[A-Z]{3}[UJZ][0-9]{7}$")


def normalize_container(value):
    if value is None:
        return ""
    try:
        if value != value:  # NaN
            return ""
    except Exception:
        pass
    return str(value).strip().upper()


def is_valid_container_number(value):
    return bool(CONTAINER_PATTERN.fullmatch(normalize_container(value)))


def parse_amount(value):
    if value is None:
        return None
    try:
        if value != value:
            return None
    except Exception:
        pass
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    raw = str(value).strip().replace(",", "").replace("₩", "").replace("원", "")
    if not raw:
        return None
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    raw = re.sub(r"\s+", "", raw)
    try:
        return Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"금액으로 변환할 수 없습니다: {value}")
