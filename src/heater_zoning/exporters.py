from io import BytesIO
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .analysis import metrics_dataframe, representative_points_dataframe, zones_dataframe
from .models import AnalysisResult


def beautify_excel(workbook_path: Path):
    workbook = load_workbook(workbook_path)
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    metric_fill = PatternFill("solid", fgColor="FFF2CC")
    point_fill = PatternFill("solid", fgColor="E2F0D9")
    header_font = Font(bold=True, color="000000")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    border = Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        top=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF"),
    )

    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center
            cell.border = border

        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = center
                cell.border = border
                if isinstance(cell.value, (int, float)):
                    cell.number_format = "0.0000" if sheet.title == "评价指标" else "0.000"

        if sheet.title == "评价指标":
            for row in sheet.iter_rows(min_row=2, max_col=2):
                for cell in row:
                    cell.fill = metric_fill

        if "三点" in sheet.title:
            for row in sheet.iter_rows(min_row=2, max_col=3):
                for cell in row:
                    cell.fill = point_fill

        for col_idx, column_cells in enumerate(sheet.columns, start=1):
            max_length = 0
            col_letter = get_column_letter(col_idx)
            for cell in column_cells:
                cell_value = "" if cell.value is None else str(cell.value)
                max_length = max(max_length, len(cell_value))
            sheet.column_dimensions[col_letter].width = min(max_length + 4, 45)

    workbook.save(workbook_path)


def export_analysis_excel(result: AnalysisResult, output_path: Path) -> Path:
    profile_df = result.profile_df
    equal_df = zones_dataframe(
        result.equal_zones,
        "等距分区",
        profile_df["distance_mm"].to_numpy(),
        profile_df["temperature_c"].to_numpy(),
    )
    aligned_df = zones_dataframe(
        result.aligned_zones,
        "模块对齐分区",
        profile_df["distance_mm"].to_numpy(),
        profile_df["temperature_c"].to_numpy(),
    )
    equal_points_df = representative_points_dataframe(
        result.equal_zones,
        profile_df["distance_mm"].to_numpy(),
        profile_df["temperature_c"].to_numpy(),
        "等距分区",
    )
    aligned_points_df = representative_points_dataframe(
        result.aligned_zones,
        profile_df["distance_mm"].to_numpy(),
        profile_df["temperature_c"].to_numpy(),
        "模块对齐分区",
    )
    metrics_df = metrics_dataframe(result.equal_metrics, result.aligned_metrics)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        profile_df.to_excel(writer, sheet_name="原始数据", index=False)
        equal_df.to_excel(writer, sheet_name="等距分区结果", index=False)
        aligned_df.to_excel(writer, sheet_name="模块对齐分区结果", index=False)
        equal_points_df.to_excel(writer, sheet_name="等距分区三点", index=False)
        aligned_points_df.to_excel(writer, sheet_name="模块对齐分区三点", index=False)
        metrics_df.to_excel(writer, sheet_name="评价指标", index=False)

    beautify_excel(output_path)
    return output_path


def export_excel_bytes(result: AnalysisResult) -> bytes:
    temp_path = Path("outputs") / "_preview_export.xlsx"
    export_analysis_excel(result, temp_path)
    return temp_path.read_bytes()

