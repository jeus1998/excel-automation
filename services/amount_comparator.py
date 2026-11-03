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
        if len(lrows) > 1 or len(rrows) > 1:
            detail = f"{key} · 기준 {len(lrows)}건, 비교 {len(rrows)}건 중복"
            # Keep each source occurrence on its own result row. This makes the
            # source file and exact Excel row clear without packing row numbers
            # into a single cell.
            for row_number, record in lrows:
                carrier, selected = _reference_context(record, ref)
                row = ComparisonResult(
                    key, carrier=carrier, applied_amount_column=selected,
                    reference_row=row_number, status="중복", detail=detail,
                )
                try:
                    row.reference_amount = parse_amount(record[selected]) if selected else None
                except (ValueError, TypeError, KeyError):
                    row.reference_amount = None
                results.append(row)
            for index, (row_number, record) in enumerate(rrows):
                context_record = lrows[min(index, len(lrows) - 1)][1] if lrows else None
                carrier, selected = _reference_context(context_record, ref)
                row = ComparisonResult(
                    key, carrier=carrier, applied_amount_column=selected,
                    comparison_row=row_number, status="중복", detail=detail,
                )
                try:
                    row.comparison_amount = parse_amount(record[cmp.amount_column])
                except (ValueError, TypeError, KeyError):
                    row.comparison_amount = None
                results.append(row)
            continue
        row = ComparisonResult(key)
        row.reference_row = lrows[0][0] if lrows else None
        row.comparison_row = rrows[0][0] if rrows else None
        if not lrows:
            row.status = "기준 파일 누락"
            if rrows:
                try:
                    row.comparison_amount = parse_amount(rrows[0][1][cmp.amount_column])
                except (ValueError, TypeError, KeyError):
                    row.comparison_amount = None
        elif not rrows:
            row.status = "비교 파일 누락"
            _, lrecord = lrows[0]
            row.carrier, row.applied_amount_column = _reference_context(lrecord, ref)
            try:
                row.reference_amount = parse_amount(lrecord[row.applied_amount_column])
            except (ValueError, TypeError, KeyError):
                row.reference_amount = None
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


def _reference_context(record, ref):
    if record is None:
        return "", ""
    carrier = str(record.get(ref.carrier_column, "") or "") if ref.carrier_column else ""
    selected = ref.default_amount_column
    for rule in ref.amount_rules:
        if carrier.strip() == rule.value.strip():
            selected = rule.amount_column
            break
    return carrier, selected


def _group(frame, column, header):
    grouped = defaultdict(list)
    for idx, record in frame.iterrows():
        value = record[column]
        if is_valid_container_number(value):
            key = normalize_container(value)
            grouped[key].append((int(idx) + header + 2, record))
    return grouped
