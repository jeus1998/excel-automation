from collections import defaultdict
from models.comparison_result import ComparisonResult
from .data_normalizer import is_valid_container_number, normalize_container, parse_amount


def compare_amounts(reference, comparison, plan, ref_header=0, cmp_header=0):
    ref, cmp = plan.reference, plan.comparison
    left = _group(reference, ref.container_column, ref_header)
    right = _group(comparison, cmp.container_column, cmp_header)
    keys = list(dict.fromkeys([*left.keys(), *right.keys()]))
    results = []
    for key in keys:
        lrows, rrows = left.get(key, []), right.get(key, [])
        row = ComparisonResult(key)
        row.reference_row = lrows[0][0] if lrows else None
        row.comparison_row = rrows[0][0] if rrows else None
        if len(lrows) > 1 or len(rrows) > 1:
            row.reference_row = ", ".join(str(row_number) for row_number, _ in lrows) or None
            row.comparison_row = ", ".join(str(row_number) for row_number, _ in rrows) or None
            row.status = "중복"; row.detail = f"기준 {len(lrows)}건, 비교 {len(rrows)}건; 각 행을 확인하세요"
        elif not lrows:
            row.status = "기준 파일 누락"
        elif not rrows:
            row.status = "비교 파일 누락"
        else:
            _, lrecord = lrows[0]; _, rrecord = rrows[0]
            carrier = str(lrecord.get(ref.carrier_column, "") or "") if ref.carrier_column else ""
            row.carrier = carrier
            selected = ref.default_amount_column
            for rule in ref.amount_rules:
                if carrier.strip() == rule.value.strip():
                    selected = rule.amount_column
                    break
            row.applied_amount_column = selected
            try:
                row.reference_amount = parse_amount(lrecord[selected])
                row.comparison_amount = parse_amount(rrecord[cmp.amount_column])
                if row.reference_amount is None or row.comparison_amount is None:
                    row.status = "데이터 오류"; row.detail = "금액이 비어 있습니다. 0원과 구분됩니다."
                else:
                    row.difference = row.comparison_amount - row.reference_amount
                    row.status = "금액 일치" if row.difference == 0 else "금액 불일치"
            except (ValueError, TypeError) as exc:
                row.status = "데이터 오류"; row.detail = str(exc)
        results.append(row)
    return results


def _group(frame, column, header):
    grouped = defaultdict(list)
    for idx, record in frame.iterrows():
        value = record[column]
        if is_valid_container_number(value):
            key = normalize_container(value)
            grouped[key].append((int(idx) + header + 2, record))
    return grouped
