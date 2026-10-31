from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ComparisonResult:
    container_number: str
    carrier: str = ""
    applied_amount_column: str = ""
    reference_amount: Decimal | None = None
    comparison_amount: Decimal | None = None
    difference: Decimal | None = None
    status: str = ""
    reference_row: int | str | None = None
    comparison_row: int | str | None = None
    detail: str = ""

    def as_dict(self):
        return {
            "컨테이너 번호": self.container_number, "운송사": self.carrier,
            "적용 금액 컬럼": self.applied_amount_column,
            "기준 금액": str(self.reference_amount) if self.reference_amount is not None else None,
            "비교 금액": str(self.comparison_amount) if self.comparison_amount is not None else None,
            "차액": str(self.difference) if self.difference is not None else None,
            "결과": self.status, "기준 행 번호": self.reference_row,
            "비교 행 번호": self.comparison_row, "상세": self.detail,
        }
