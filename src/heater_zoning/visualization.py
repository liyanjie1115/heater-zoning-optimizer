from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib.figure import Figure
from plotly.subplots import make_subplots

from .models import MethodMetrics, ZoneResult


def _zone_boundaries(zones: Sequence[ZoneResult]):
    boundaries = []
    for zone in zones:
        boundaries.append(zone.start_mm)
    if zones:
        boundaries.append(zones[-1].end_mm)
    return boundaries


def _add_zone_shapes(fig, zones: Sequence[ZoneResult], row: int, color: str):
    boundaries = _zone_boundaries(zones)
    for boundary in boundaries:
        fig.add_vline(
            x=boundary,
            line_width=1,
            line_dash="dash",
            line_color="#9ca3af",
            row=row,
            col=1,
        )

    for zone in zones:
        for start, end in zone.module_positions:
            fig.add_shape(
                type="rect",
                x0=start,
                x1=end,
                y0=zone.avg_temp_c - 4,
                y1=zone.avg_temp_c + 4,
                line={"color": color, "width": 1.2},
                fillcolor=color,
                opacity=0.25,
                row=row,
                col=1,
            )


def build_temperature_comparison_figure(
    profile_df: pd.DataFrame, equal_zones: Sequence[ZoneResult], aligned_zones: Sequence[ZoneResult]
) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=("等距分区", "模块对齐最优分区"),
    )

    for row_idx, zones, color in ((1, equal_zones, "#2563eb"), (2, aligned_zones, "#dc2626")):
        fig.add_trace(
            go.Scatter(
                x=profile_df["distance_mm"],
                y=profile_df["temperature_c"],
                mode="lines+markers",
                name="原始温度",
                line={"color": "#111827", "width": 2},
                marker={"size": 6},
                showlegend=row_idx == 1,
            ),
            row=row_idx,
            col=1,
        )
        for zone in zones:
            fig.add_trace(
                go.Scatter(
                    x=[zone.start_mm, zone.end_mm],
                    y=[zone.avg_temp_c, zone.avg_temp_c],
                    mode="lines",
                    line={"color": color, "width": 4},
                    name=f"Z{zone.zone_id}",
                    showlegend=False,
                    hovertemplate=(
                        f"Z{zone.zone_id}<br>"
                        f"范围: {zone.start_mm:.1f}-{zone.end_mm:.1f} mm<br>"
                        f"模块数: {zone.modules}<br>"
                        f"安装长度: {zone.install_length_mm:.1f} mm<extra></extra>"
                    ),
                ),
                row=row_idx,
                col=1,
            )
        _add_zone_shapes(fig, zones, row_idx, color)

    fig.update_layout(
        height=760,
        margin={"l": 30, "r": 20, "t": 70, "b": 30},
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    fig.update_xaxes(title_text="距离 (mm)", gridcolor="#e5e7eb", zeroline=False, row=2, col=1)
    fig.update_yaxes(title_text="温度 (°C)", gridcolor="#e5e7eb", zeroline=False)
    return fig


def build_module_layout_figure(equal_zones: Sequence[ZoneResult], aligned_zones: Sequence[ZoneResult]) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.16,
        subplot_titles=("等距分区模块布局", "模块对齐分区模块布局"),
    )

    for row_idx, zones, color in ((1, equal_zones, "#2563eb"), (2, aligned_zones, "#dc2626")):
        total = len(zones)
        for boundary in _zone_boundaries(zones):
            fig.add_vline(x=boundary, line_width=1, line_dash="dash", line_color="#cbd5e1", row=row_idx, col=1)

        for idx, zone in enumerate(zones, start=1):
            y = total - idx + 1
            fig.add_shape(
                type="rect",
                x0=zone.start_mm,
                x1=zone.end_mm,
                y0=y - 0.35,
                y1=y + 0.35,
                line={"color": "#9ca3af", "width": 1, "dash": "dash"},
                fillcolor="rgba(0,0,0,0)",
                row=row_idx,
                col=1,
            )
            for start, end in zone.module_positions:
                fig.add_shape(
                    type="rect",
                    x0=start,
                    x1=end,
                    y0=y - 0.18,
                    y1=y + 0.18,
                    line={"color": color, "width": 1},
                    fillcolor=color,
                    opacity=0.32,
                    row=row_idx,
                    col=1,
                )
            fig.add_trace(
                go.Scatter(
                    x=[zone.start_mm],
                    y=[y],
                    mode="markers+text",
                    text=[f"Z{zone.zone_id} | {zone.modules} 模块"],
                    textposition="middle left",
                    marker={"size": 8, "color": color},
                    showlegend=False,
                    hovertemplate=(
                        f"Z{zone.zone_id}<br>"
                        f"范围: {zone.start_mm:.1f}-{zone.end_mm:.1f} mm<br>"
                        f"左外伸: {zone.left_overhang_mm:.1f} mm<br>"
                        f"右外伸: {zone.right_overhang_mm:.1f} mm<extra></extra>"
                    ),
                ),
                row=row_idx,
                col=1,
            )

    fig.update_layout(height=620, margin={"l": 30, "r": 20, "t": 70, "b": 30}, paper_bgcolor="white", plot_bgcolor="white")
    fig.update_xaxes(title_text="距离 (mm)", gridcolor="#e5e7eb", zeroline=False, row=2, col=1)
    fig.update_yaxes(showticklabels=False, gridcolor="#f3f4f6", zeroline=False)
    return fig


def build_metrics_bar_figure(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> go.Figure:
    labels = ["E_fit", "E_sep", "综合得分", "安装误差", "均衡性"]
    equal_values = [
        equal_metrics.e_fit,
        equal_metrics.e_sep,
        equal_metrics.composite_score,
        equal_metrics.heater_mismatch,
        equal_metrics.balance_score,
    ]
    aligned_values = [
        aligned_metrics.e_fit,
        aligned_metrics.e_sep,
        aligned_metrics.composite_score,
        aligned_metrics.heater_mismatch,
        aligned_metrics.balance_score,
    ]

    fig = go.Figure()
    fig.add_bar(name="等距分区", x=labels, y=equal_values, marker_color="#2563eb")
    fig.add_bar(name="模块对齐分区", x=labels, y=aligned_values, marker_color="#dc2626")
    fig.update_layout(
        barmode="group",
        height=420,
        margin={"l": 30, "r": 20, "t": 40, "b": 30},
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    fig.update_yaxes(gridcolor="#e5e7eb", zeroline=False)
    return fig


def build_metrics_radar_figure(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> go.Figure:
    labels = ["拟合性", "分离性", "安装匹配", "均衡性", "尺寸合规"]
    max_sep = max(equal_metrics.e_sep, aligned_metrics.e_sep, 1e-6)

    equal_values = [
        float(np.exp(-equal_metrics.e_fit / 1000.0)),
        equal_metrics.e_sep / max_sep,
        float(np.exp(-equal_metrics.heater_mismatch / 10.0)),
        equal_metrics.balance_score,
        equal_metrics.size_compliance,
    ]
    aligned_values = [
        float(np.exp(-aligned_metrics.e_fit / 1000.0)),
        aligned_metrics.e_sep / max_sep,
        float(np.exp(-aligned_metrics.heater_mismatch / 10.0)),
        aligned_metrics.balance_score,
        aligned_metrics.size_compliance,
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=equal_values, theta=labels, fill="toself", name="等距分区", line={"color": "#2563eb"}))
    fig.add_trace(go.Scatterpolar(r=aligned_values, theta=labels, fill="toself", name="模块对齐分区", line={"color": "#dc2626"}))
    fig.update_layout(
        height=520,
        margin={"l": 30, "r": 30, "t": 30, "b": 30},
        paper_bgcolor="white",
        polar={"radialaxis": {"visible": True, "range": [0, 1]}},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    return fig


def _apply_matplotlib_style(fig: Figure):
    fig.patch.set_facecolor("#f8fafc")
    for axis in fig.axes:
        axis.set_facecolor("white")
        axis.grid(True, alpha=0.25, color="#cbd5e1")
        for spine in axis.spines.values():
            spine.set_color("#cbd5e1")


def build_temperature_comparison_matplotlib(
    profile_df: pd.DataFrame, equal_zones: Sequence[ZoneResult], aligned_zones: Sequence[ZoneResult]
) -> Figure:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    for axis, title, zones, color, fill in (
        (axes[0], "等距分区", equal_zones, "#2563eb", "#bfdbfe"),
        (axes[1], "模块对齐最优分区", aligned_zones, "#dc2626", "#fecaca"),
    ):
        axis.plot(profile_df["distance_mm"], profile_df["temperature_c"], color="#0f172a", marker="o", linewidth=1.8, markersize=4)
        for boundary in _zone_boundaries(zones):
            axis.axvline(boundary, linestyle="--", color="#94a3b8", linewidth=1.0, alpha=0.9)
        for zone in zones:
            axis.hlines(zone.avg_temp_c, zone.start_mm, zone.end_mm, colors=color, linewidth=3.0)
            for start, end in zone.module_positions:
                axis.axvspan(start, end, ymin=0, ymax=1, color=fill, alpha=0.35)
        axis.set_title(title, loc="left", fontsize=12, fontweight="bold")
        axis.set_ylabel("温度 (°C)")
    axes[1].set_xlabel("距离 (mm)")
    fig.tight_layout()
    _apply_matplotlib_style(fig)
    return fig


def build_module_layout_matplotlib(equal_zones: Sequence[ZoneResult], aligned_zones: Sequence[ZoneResult]) -> Figure:
    fig, axes = plt.subplots(2, 1, figsize=(12, 6), sharex=True)
    for axis, title, zones, color, fill in (
        (axes[0], "等距分区模块布局", equal_zones, "#2563eb", "#bfdbfe"),
        (axes[1], "模块对齐分区模块布局", aligned_zones, "#dc2626", "#fecaca"),
    ):
        total = len(zones)
        for boundary in _zone_boundaries(zones):
            axis.axvline(boundary, linestyle="--", color="#cbd5e1", linewidth=1.0)
        for index, zone in enumerate(zones, start=1):
            y = total - index + 1
            axis.add_patch(plt.Rectangle((zone.start_mm, y - 0.28), zone.size_mm, 0.56, fill=False, edgecolor="#64748b", linestyle="--", linewidth=1.0))
            for start, end in zone.module_positions:
                axis.add_patch(plt.Rectangle((start, y - 0.18), end - start, 0.36, facecolor=fill, edgecolor=color, linewidth=1.0))
            axis.text(zone.start_mm + 1.0, y + 0.35, f"Z{zone.zone_id} | {zone.modules} 模块", fontsize=9, color="#0f172a")
        axis.set_title(title, loc="left", fontsize=12, fontweight="bold")
        axis.set_yticks([])
    axes[1].set_xlabel("距离 (mm)")
    fig.tight_layout()
    _apply_matplotlib_style(fig)
    return fig


def build_metrics_bar_matplotlib(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> Figure:
    labels = ["E_fit", "E_sep", "综合得分", "安装误差", "均衡性"]
    equal_values = [equal_metrics.e_fit, equal_metrics.e_sep, equal_metrics.composite_score, equal_metrics.heater_mismatch, equal_metrics.balance_score]
    aligned_values = [aligned_metrics.e_fit, aligned_metrics.e_sep, aligned_metrics.composite_score, aligned_metrics.heater_mismatch, aligned_metrics.balance_score]
    x = np.arange(len(labels))
    width = 0.35

    fig, axis = plt.subplots(figsize=(7.5, 4.5))
    axis.bar(x - width / 2, equal_values, width=width, color="#2563eb", label="等距分区")
    axis.bar(x + width / 2, aligned_values, width=width, color="#dc2626", label="模块对齐分区")
    axis.set_xticks(x)
    axis.set_xticklabels(labels)
    axis.legend(frameon=False, loc="upper right")
    axis.set_title("关键指标对比", loc="left", fontsize=12, fontweight="bold")
    fig.tight_layout()
    _apply_matplotlib_style(fig)
    return fig


def build_metrics_radar_matplotlib(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> Figure:
    labels = ["拟合性", "分离性", "安装匹配", "均衡性", "尺寸合规"]
    max_sep = max(equal_metrics.e_sep, aligned_metrics.e_sep, 1e-6)
    equal_values = [
        float(np.exp(-equal_metrics.e_fit / 1000.0)),
        equal_metrics.e_sep / max_sep,
        float(np.exp(-equal_metrics.heater_mismatch / 10.0)),
        equal_metrics.balance_score,
        equal_metrics.size_compliance,
    ]
    aligned_values = [
        float(np.exp(-aligned_metrics.e_fit / 1000.0)),
        aligned_metrics.e_sep / max_sep,
        float(np.exp(-aligned_metrics.heater_mismatch / 10.0)),
        aligned_metrics.balance_score,
        aligned_metrics.size_compliance,
    ]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    equal_values += equal_values[:1]
    aligned_values += aligned_values[:1]

    fig = plt.figure(figsize=(5.4, 5.0))
    axis = fig.add_subplot(111, polar=True)
    axis.plot(angles, equal_values, color="#2563eb", linewidth=2, label="等距分区")
    axis.fill(angles, equal_values, color="#2563eb", alpha=0.16)
    axis.plot(angles, aligned_values, color="#dc2626", linewidth=2, label="模块对齐分区")
    axis.fill(angles, aligned_values, color="#dc2626", alpha=0.16)
    axis.set_xticks(angles[:-1])
    axis.set_xticklabels(labels)
    axis.set_ylim(0, 1.0)
    axis.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.25, 1.12))
    axis.set_title("质量雷达图", loc="left", fontsize=12, fontweight="bold", pad=20)
    fig.tight_layout()
    _apply_matplotlib_style(fig)
    return fig


def figure_to_html(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False, "responsive": True})
