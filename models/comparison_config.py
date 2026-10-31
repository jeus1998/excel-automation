from pydantic import BaseModel, Field, model_validator


class AmountRule(BaseModel):
    value: str
    amount_column: str


class SheetConfig(BaseModel):
    sheet: str
    container_column: str
    carrier_column: str | None = None
    amount_column: str | None = None
    default_amount_column: str | None = None
    amount_rules: list[AmountRule] = Field(default_factory=list)


class ComparisonConfig(BaseModel):
    service: str
    reference: SheetConfig
    comparison: SheetConfig
    approved: bool = False

    @model_validator(mode="after")
    def validate_service_fields(self):
        if self.service not in {"amount_comparison", "container_reconciliation"}:
            raise ValueError("지원하지 않는 서비스입니다.")
        if self.service == "amount_comparison":
            if not self.reference.default_amount_column or not self.comparison.amount_column:
                raise ValueError("금액 비교에 필요한 금액 컬럼을 지정해야 합니다.")
            if self.reference.amount_rules and not self.reference.carrier_column:
                raise ValueError("운송사 조건을 적용하려면 운송사 컬럼이 필요합니다.")
        return self
