from dataclasses import dataclass

import numpy as np
import pandas as pd

from .analysis import metrics_dataframe, representative_points_dataframe, zones_dataframe
from .models import AnalysisResult


@dataclass
class ReportFrames:
    profile: pd.DataFrame
    equal_zones: pd.DataFrame
    aligned_zones: pd.DataFrame
    equal_points: pd.DataFrame
    aligned_points: pd.DataFrame
    metrics: pd.DataFrame


def build_report_frames(result: AnalysisResult) -> ReportFrames:
    distance = result.profile_df["distance_mm"].to_numpy()
    temperature = result.profile_df["temperature_c"].to_numpy()
    return ReportFrames(
        profile=result.profile_df.copy(),
        equal_zones=zones_dataframe(result.equal_zones, "等距分区", distance, temperature),
        aligned_zones=zones_dataframe(result.aligned_zones, "模块对齐分区", distance, temperature),
        equal_points=representative_points_dataframe(result.equal_zones, distance, temperature, "等距分区"),
        aligned_points=representative_points_dataframe(result.aligned_zones, distance, temperature, "模块对齐分区"),
        metrics=metrics_dataframe(result.equal_metrics, result.aligned_metrics),
    )


def build_summary_cards(result: AnalysisResult):
    equal = result.equal_metrics
    aligned = result.aligned_metrics
    winner = "等距分区" if equal.composite_score >= aligned.composite_score else "模块对齐分区"
    return [
        {"label": "推荐方案", "value": winner, "accent": "neutral"},
        {"label": "等距分区得分", "value": f"{equal.composite_score:.3f}", "accent": "blue"},
        {"label": "模块对齐得分", "value": f"{aligned.composite_score:.3f}", "accent": "red"},
        {"label": "得分差值", "value": f"{abs(equal.composite_score - aligned.composite_score):.3f}", "accent": "green"},
    ]


def build_zone_summary_table(result: AnalysisResult) -> pd.DataFrame:
    rows = []
    for method_name, zones in (("等距分区", result.equal_zones), ("模块对齐分区", result.aligned_zones)):
        for zone in zones:
            rows.append(
                {
                    "方案": method_name,
                    "分区": f"Z{zone.zone_id}",
                    "范围(mm)": f"{zone.start_mm:.1f} - {zone.end_mm:.1f}",
                    "长度(mm)": round(zone.size_mm, 3),
                    "平均温度(°C)": round(zone.avg_temp_c, 3),
                    "模块数": zone.modules,
                    "安装长度(mm)": round(zone.install_length_mm, 3),
                    "左外伸(mm)": round(zone.left_overhang_mm, 3),
                    "右外伸(mm)": round(zone.right_overhang_mm, 3),
                }
            )
    return pd.DataFrame(rows)

