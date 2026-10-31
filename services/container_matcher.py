from collections import Counter, defaultdict
from models.comparison_result import ComparisonResult
from .data_normalizer import is_valid_container_number, normalize_container


def reconcile_containers(reference, comparison, ref_column, cmp_column, ref_header=0, cmp_header=0):
    ref_rows, cmp_rows = _index_rows(reference, ref_column, ref_header), _index_rows(comparison, cmp_column, cmp_header)
    results = []
    keys = list(dict.fromkeys([*ref_rows.keys(), *cmp_rows.keys()]))
    for key in keys:
        left, right = ref_rows.get(key, []), cmp_rows.get(key, [])
        if len(left) > 1 or len(right) > 1:
            reference_row_numbers = ", ".join(str(row_number) for row_number, _ in left) or None
            comparison_row_numbers = ", ".join(str(row_number) for row_number, _ in right) or None
            results.append(ComparisonResult(key, status="중복", reference_row=reference_row_numbers, comparison_row=comparison_row_numbers, detail=f"기준 {len(left)}건, 비교 {len(right)}건; 각 행을 확인하세요"))
        elif left and right:
            results.append(ComparisonResult(key, status="양쪽 파일에 존재", reference_row=left[0][0], comparison_row=right[0][0]))
        elif left:
            results.append(ComparisonResult(key, status="기준 파일에만 존재", reference_row=left[0][0]))
        else:
            results.append(ComparisonResult(key, status="비교 파일에만 존재", comparison_row=right[0][0]))
    return results


def _index_rows(frame, column, header_row):
    rows = defaultdict(list)
    for idx, value in frame[column].items():
        # Excel row number, counting header and zero-based dataframe index.
        if is_valid_container_number(value):
            rows[normalize_container(value)].append((int(idx) + header_row + 2, value))
    return rows
