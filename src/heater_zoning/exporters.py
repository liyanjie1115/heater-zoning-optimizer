from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .fonts import configure_matplotlib_fonts
from .models import AnalysisResult
from .reporting import build_report_frames, build_summary_cards, build_zone_summary_table
from .visualization import (
    build_metrics_bar_matplotlib,
    build_metrics_radar_matplotlib,
    build_module_layout_matplotlib,
    build_temperature_comparison_matplotlib,
)


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
    frames = build_report_frames(result)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        frames.profile.to_excel(writer, sheet_name="原始数据", index=False)
        frames.equal_zones.to_excel(writer, sheet_name="等距分区结果", index=False)
        frames.aligned_zones.to_excel(writer, sheet_name="模块对齐分区结果", index=False)
        frames.equal_points.to_excel(writer, sheet_name="等距分区三点", index=False)
        frames.aligned_points.to_excel(writer, sheet_name="模块对齐分区三点", index=False)
        frames.metrics.to_excel(writer, sheet_name="评价指标", index=False)

    beautify_excel(output_path)
    return output_path


def _table_figure(dataframe: pd.DataFrame, title: str):
    rows = min(len(dataframe), 16)
    height = max(3.8, 0.45 * rows + 1.6)
    fig, axis = plt.subplots(figsize=(11.69, height))
    fig.patch.set_facecolor("white")
    axis.axis("off")
    axis.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=12)
    table = axis.table(
        cellText=dataframe.head(16).values,
        colLabels=list(dataframe.columns),
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#d9eaf7")
            cell.set_text_props(weight="bold")
        cell.set_edgecolor("#cbd5e1")
    fig.tight_layout()
    return fig


def _summary_figure(result: AnalysisResult):
    cards = build_summary_cards(result)
    summary_df = build_zone_summary_table(result)
    fig, axes = plt.subplots(2, 1, figsize=(11.69, 8.27), gridspec_kw={"height_ratios": [1.2, 3.0]})
    fig.patch.set_facecolor("white")

    axes[0].axis("off")
    axes[0].text(0.0, 1.0, "Heater Zoning Optimizer 摘要", fontsize=18, fontweight="bold", va="top")
    y = 0.72
    for card in cards:
        axes[0].text(0.0, y, f"{card['label']}: {card['value']}", fontsize=12, va="top")
        y -= 0.18

    axes[1].axis("off")
    axes[1].set_title("分区汇总", loc="left", fontsize=13, fontweight="bold", pad=10)
    table = axes[1].table(
        cellText=summary_df.values,
        colLabels=list(summary_df.columns),
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.45)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#d9eaf7")
            cell.set_text_props(weight="bold")
        cell.set_edgecolor("#cbd5e1")

    fig.tight_layout()
    return fig


def export_summary_pdf(result: AnalysisResult, output_path: Path) -> Path:
    frames = build_report_frames(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    figures = [
        _summary_figure(result),
        build_temperature_comparison_matplotlib(result.profile_df, result.equal_zones, result.aligned_zones),
        build_module_layout_matplotlib(result.equal_zones, result.aligned_zones),
        build_metrics_bar_matplotlib(result.equal_metrics, result.aligned_metrics),
        build_metrics_radar_matplotlib(result.equal_metrics, result.aligned_metrics),
        _table_figure(frames.metrics, "评价指标"),
        _table_figure(frames.equal_zones, "等距分区结果"),
        _table_figure(frames.aligned_zones, "模块对齐分区结果"),
    ]

    with PdfPages(output_path) as pdf:
        for figure in figures:
            pdf.savefig(figure, bbox_inches="tight")
            plt.close(figure)

    return output_path


configure_matplotlib_fonts()
