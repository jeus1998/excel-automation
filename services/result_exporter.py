import pandas as pd


def export_results(results, path, plan=None):
    frame = pd.DataFrame([r.as_dict() for r in results])
    groups = {
        "불일치": ["금액 불일치"], "기준 파일 누락": ["기준 파일 누락", "비교 파일에만 존재"],
        "비교 파일 누락": ["비교 파일 누락", "기준 파일에만 존재"],
        "중복": ["중복"], "데이터 오류": ["데이터 오류", "빈 값"],
    }
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="전체 결과", index=False)
        for sheet, statuses in groups.items():
            (frame[frame["결과"].isin(statuses)] if not frame.empty else frame).to_excel(writer, sheet_name=sheet, index=False)
        pd.DataFrame([plan or {}]).to_excel(writer, sheet_name="AI 작업 계획", index=False)
    return path
