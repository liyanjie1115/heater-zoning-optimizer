from __future__ import annotations

from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from .fonts import configure_matplotlib_fonts
from .models import MethodMetrics, ZoneResult


configure_matplotlib_fonts()

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ModuleNotFoundError:
    go = None
    make_subplots = None


def _require_plotly():
    if go is None or make_subplots is None:
        raise ModuleNotFoundError("当前环境未安装 plotly。网页界面需要 plotly，桌面版不依赖它。")


def _zone_boundaries(zones: Sequence[ZoneResult]) -> list[float]:
    boundaries = [zone.start_mm for zone in zones]
    if zones:
        boundaries.append(zones[-1].end_mm)
    return boundaries


def _x_bounds(zones: Sequence[ZoneResult]) -> tuple[float, float]:
    boundaries = _zone_boundaries(zones)
    if not boundaries:
        return 0.0, 1.0
    minimum = min(boundaries)
    maximum = max(boundaries)
    padding = max((maximum - minimum) * 0.03, 8.0)
    return minimum - padding, maximum + padding


def _add_zone_shapes(fig, zones: Sequence[ZoneResult], row: int, color: str):
    for boundary in _zone_boundaries(zones):
        fig.add_vline(
            x=boundary,
            line_width=1,
            line_dash="dash",
            line_color="#94a3b8",
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
                opacity=0.24,
                row=row,
                col=1,
            )


def _normalized_metric_pairs(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics):
    metric_pairs = [
        ("加权拟合", equal_metrics.weighted_fit_error, aligned_metrics.weighted_fit_error, "cost"),
        ("分离度", equal_metrics.e_sep, aligned_metrics.e_sep, "benefit"),
        ("边界贴合", equal_metrics.gradient_capture_score, aligned_metrics.gradient_capture_score, "benefit"),
        ("安装匹配", equal_metrics.heater_mismatch, aligned_metrics.heater_mismatch, "cost"),
        ("综合得分", equal_metrics.composite_score, aligned_metrics.composite_score, "benefit"),
    ]

    labels: list[str] = []
    equal_scores: list[float] = []
    aligned_scores: list[float] = []
    equal_raw_values: list[float] = []
    aligned_raw_values: list[float] = []

    for label, equal_raw, aligned_raw, direction in metric_pairs:
        labels.append(label)
        equal_raw_values.append(equal_raw)
        aligned_raw_values.append(aligned_raw)
        if direction == "cost":
            baseline = max(min(equal_raw, aligned_raw), 1e-9)
            equal_scores.append(baseline / max(equal_raw, 1e-9))
            aligned_scores.append(baseline / max(aligned_raw, 1e-9))
        else:
            baseline = max(equal_raw, aligned_raw, 1e-9)
            equal_scores.append(equal_raw / baseline)
            aligned_scores.append(aligned_raw / baseline)

    return labels, equal_scores, aligned_scores, equal_raw_values, aligned_raw_values


def build_temperature_comparison_figure(
    profile_df: pd.DataFrame, equal_zones: Sequence[ZoneResult], aligned_zones: Sequence[ZoneResult]
) -> "go.Figure":
    _require_plotly()
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=("等距分区", "模块对齐最优分区"),
    )

    x_min = float(profile_df["distance_mm"].min())
    x_max = float(profile_df["distance_mm"].max())
    x_padding = max((x_max - x_min) * 0.03, 8.0)

    for row_idx, zones, color in ((1, equal_zones, "#2563eb"), (2, aligned_zones, "#dc2626")):
        fig.add_trace(
            go.Scatter(
                x=profile_df["distance_mm"],
                y=profile_df["temperature_c"],
                mode="lines+markers",
                name="原始温度",
                line={"color": "#0f172a", "width": 2},
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
        height=780,
        margin={"l": 40, "r": 24, "t": 72, "b": 40},
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    fig.update_xaxes(
        title_text="距离 (mm)",
        gridcolor="#e5e7eb",
        zeroline=False,
        row=2,
        col=1,
        range=[x_min - x_padding, x_max + x_padding],
    )
    fig.update_yaxes(title_text="温度 (°C)", gridcolor="#e5e7eb", zeroline=False)
    return fig


def build_module_layout_figure(equal_zones: Sequence[ZoneResult], aligned_zones: Sequence[ZoneResult]) -> "go.Figure":
    _require_plotly()
    max_rows = max(len(equal_zones), len(aligned_zones), 1)
    row_height = max(180, 56 * max_rows)
    total_height = max(520, min(980, row_height * 2 + 110))
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.14,
        subplot_titles=("等距分区模块排布", "模块对齐分区模块排布"),
    )

    x_lower, x_upper = _x_bounds(list(equal_zones) + list(aligned_zones))

    for row_idx, zones, color in ((1, equal_zones, "#2563eb"), (2, aligned_zones, "#dc2626")):
        total = max(len(zones), 1)
        for boundary in _zone_boundaries(zones):
            fig.add_vline(x=boundary, line_width=1, line_dash="dash", line_color="#cbd5e1", row=row_idx, col=1)

        for idx, zone in enumerate(zones, start=1):
            y = total - idx + 1
            fig.add_shape(
                type="rect",
                x0=zone.start_mm,
                x1=zone.end_mm,
                y0=y - 0.34,
                y1=y + 0.34,
                line={"color": "#94a3b8", "width": 1, "dash": "dash"},
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
                    opacity=0.30,
                    row=row_idx,
                    col=1,
                )

            label_x = min(
                max(zone.start_mm + 4.0, x_lower + 6.0),
                zone.end_mm - 6.0 if zone.end_mm - zone.start_mm > 16 else zone.start_mm + 4.0,
            )
            fig.add_trace(
                go.Scatter(
                    x=[label_x],
                    y=[y + 0.26],
                    mode="text",
                    text=[f"Z{zone.zone_id} | {zone.modules} 模块"],
                    textposition="middle left",
                    textfont={"size": 12, "color": "#0f172a"},
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

        fig.update_yaxes(
            range=[0.4, total + 0.8],
            row=row_idx,
            col=1,
            showticklabels=False,
            gridcolor="#f3f4f6",
            zeroline=False,
        )

    fig.update_layout(
        height=total_height,
        margin={"l": 40, "r": 24, "t": 72, "b": 42},
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    fig.update_xaxes(title_text="距离 (mm)", gridcolor="#e5e7eb", zeroline=False, row=2, col=1, range=[x_lower, x_upper])
    return fig


def build_metrics_bar_figure(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> "go.Figure":
    _require_plotly()
    labels, equal_values, aligned_values, equal_raw_values, aligned_raw_values = _normalized_metric_pairs(
        equal_metrics, aligned_metrics
    )

    fig = go.Figure()
    fig.add_bar(
        name="等距分区",
        x=labels,
        y=equal_values,
        customdata=np.column_stack((equal_raw_values, equal_values)),
        marker_color="#2563eb",
        hovertemplate="原始值: %{customdata[0]:.2f}<br>归一化得分: %{customdata[1]:.2f}<extra></extra>",
    )
    fig.add_bar(
        name="模块对齐分区",
        x=labels,
        y=aligned_values,
        customdata=np.column_stack((aligned_raw_values, aligned_values)),
        marker_color="#dc2626",
        hovertemplate="原始值: %{customdata[0]:.2f}<br>归一化得分: %{customdata[1]:.2f}<extra></extra>",
    )
    fig.update_layout(
        barmode="group",
        height=460,
        margin={"l": 40, "r": 24, "t": 40, "b": 60},
        paper_bgcolor="white",
        plot_bgcolor="white",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0.0},
    )
    fig.update_xaxes(tickangle=-12)
    fig.update_yaxes(title_text="归一化对比得分", range=[0.0, 1.05], gridcolor="#e5e7eb", zeroline=False)
    return fig


def build_metrics_radar_figure(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> "go.Figure":
    _require_plotly()
    max_sep = max(equal_metrics.e_sep, aligned_metrics.e_sep, 1e-6)
    max_fit = max(equal_metrics.weighted_fit_error, aligned_metrics.weighted_fit_error, 1e-6)
    labels = ["加权拟合", "分离性", "梯度贴合", "安装匹配", "均衡性", "尺寸合规"]

    equal_values = [
        1.0 - equal_metrics.weighted_fit_error / max_fit,
        equal_metrics.e_sep / max_sep,
        equal_metrics.gradient_capture_score,
        float(np.exp(-equal_metrics.heater_mismatch / 16.0)),
        equal_metrics.balance_score,
        equal_metrics.size_compliance,
    ]
    aligned_values = [
        1.0 - aligned_metrics.weighted_fit_error / max_fit,
        aligned_metrics.e_sep / max_sep,
        aligned_metrics.gradient_capture_score,
        float(np.exp(-aligned_metrics.heater_mismatch / 16.0)),
        aligned_metrics.balance_score,
        aligned_metrics.size_compliance,
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=equal_values, theta=labels, fill="toself", name="等距分区", line={"color": "#2563eb"}))
    fig.add_trace(
        go.Scatterpolar(r=aligned_values, theta=labels, fill="toself", name="模块对齐分区", line={"color": "#dc2626"})
    )
    fig.update_layout(
        height=620,
        margin={"l": 52, "r": 52, "t": 36, "b": 36},
        paper_bgcolor="white",
        polar={"radialaxis": {"visible": True, "range": [0, 1]}},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.06, "x": 0.0},
    )
    return fig


def _apply_matplotlib_style(fig: Figure):
    fig.patch.set_facecolor("#ffffff")
    for axis in fig.axes:
        axis.set_facecolor("#ffffff")
        axis.grid(True, alpha=0.22, color="#cbd5e1")
        for spine in axis.spines.values():
            spine.set_color("#cbd5e1")


def build_temperature_comparison_matplotlib(
    profile_df: pd.DataFrame, equal_zones: Sequence[ZoneResult], aligned_zones: Sequence[ZoneResult]
) -> Figure:
    fig, axes = plt.subplots(2, 1, figsize=(13.2, 8.6), sharex=True)
    x_min = float(profile_df["distance_mm"].min())
    x_max = float(profile_df["distance_mm"].max())
    x_padding = max((x_max - x_min) * 0.03, 8.0)

    for axis, title, zones, color, fill in (
        (axes[0], "等距分区", equal_zones, "#2563eb", "#bfdbfe"),
        (axes[1], "模块对齐最优分区", aligned_zones, "#dc2626", "#fecaca"),
    ):
        axis.plot(
            profile_df["distance_mm"],
            profile_df["temperature_c"],
            color="#0f172a",
            marker="o",
            linewidth=1.8,
            markersize=4,
        )
        for boundary in _zone_boundaries(zones):
            axis.axvline(boundary, linestyle="--", color="#94a3b8", linewidth=1.0, alpha=0.9)
        for zone in zones:
            axis.hlines(zone.avg_temp_c, zone.start_mm, zone.end_mm, colors=color, linewidth=3.0)
            for start, end in zone.module_positions:
                axis.axvspan(start, end, ymin=0, ymax=1, color=fill, alpha=0.34)
        axis.set_title(title, loc="left", fontsize=12, fontweight="bold")
        axis.set_ylabel("温度 (°C)")
        axis.set_xlim(x_min - x_padding, x_max + x_padding)
    axes[1].set_xlabel("距离 (mm)")
    fig.subplots_adjust(left=0.07, right=0.985, top=0.95, bottom=0.08, hspace=0.24)
    _apply_matplotlib_style(fig)
    return fig


def build_module_layout_matplotlib(equal_zones: Sequence[ZoneResult], aligned_zones: Sequence[ZoneResult]) -> Figure:
    max_rows = max(len(equal_zones), len(aligned_zones), 1)
    figure_height = max(7.2, min(13.6, 4.6 + max_rows * 0.72))
    fig, axes = plt.subplots(2, 1, figsize=(13.6, figure_height), sharex=True)
    x_lower, x_upper = _x_bounds(list(equal_zones) + list(aligned_zones))

    for axis, title, zones, color, fill in (
        (axes[0], "等距分区模块排布", equal_zones, "#2563eb", "#bfdbfe"),
        (axes[1], "模块对齐分区模块排布", aligned_zones, "#dc2626", "#fecaca"),
    ):
        total = max(len(zones), 1)
        for boundary in _zone_boundaries(zones):
            axis.axvline(boundary, linestyle="--", color="#cbd5e1", linewidth=1.0)
        for index, zone in enumerate(zones, start=1):
            y = total - index + 1
            axis.add_patch(
                plt.Rectangle(
                    (zone.start_mm, y - 0.28),
                    zone.size_mm,
                    0.56,
                    fill=False,
                    edgecolor="#64748b",
                    linestyle="--",
                    linewidth=1.0,
                )
            )
            for start, end in zone.module_positions:
                axis.add_patch(
                    plt.Rectangle((start, y - 0.18), end - start, 0.36, facecolor=fill, edgecolor=color, linewidth=1.0)
                )

            label_x = zone.start_mm + min(max(zone.size_mm * 0.03, 3.0), 10.0)
            axis.text(label_x, y + 0.34, f"Z{zone.zone_id} | {zone.modules} 模块", fontsize=9, color="#0f172a", clip_on=False)

        axis.set_title(title, loc="left", fontsize=12, fontweight="bold")
        axis.set_yticks([])
        axis.set_ylim(0.35, total + 0.85)
        axis.set_xlim(x_lower, x_upper)
    axes[1].set_xlabel("距离 (mm)")
    fig.subplots_adjust(left=0.06, right=0.985, top=0.95, bottom=0.08, hspace=0.30)
    _apply_matplotlib_style(fig)
    return fig


def build_metrics_bar_matplotlib(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> Figure:
    labels, equal_values, aligned_values, _, _ = _normalized_metric_pairs(equal_metrics, aligned_metrics)
    x = np.arange(len(labels))
    width = 0.35

    fig, axis = plt.subplots(figsize=(10.8, 5.6))
    axis.bar(x - width / 2, equal_values, width=width, color="#2563eb", label="等距分区")
    axis.bar(x + width / 2, aligned_values, width=width, color="#dc2626", label="模块对齐分区")
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=10)
    axis.set_ylim(0.0, 1.05)
    axis.set_ylabel("归一化对比得分")
    axis.legend(frameon=False, loc="upper right")
    axis.set_title("关键指标对比", loc="left", fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.08, right=0.985, top=0.92, bottom=0.18)
    _apply_matplotlib_style(fig)
    return fig


def build_metrics_radar_matplotlib(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> Figure:
    max_sep = max(equal_metrics.e_sep, aligned_metrics.e_sep, 1e-6)
    max_fit = max(equal_metrics.weighted_fit_error, aligned_metrics.weighted_fit_error, 1e-6)
    labels = ["加权拟合", "分离性", "梯度贴合", "安装匹配", "均衡性", "尺寸合规"]

    equal_values = [
        1.0 - equal_metrics.weighted_fit_error / max_fit,
        equal_metrics.e_sep / max_sep,
        equal_metrics.gradient_capture_score,
        float(np.exp(-equal_metrics.heater_mismatch / 16.0)),
        equal_metrics.balance_score,
        equal_metrics.size_compliance,
    ]
    aligned_values = [
        1.0 - aligned_metrics.weighted_fit_error / max_fit,
        aligned_metrics.e_sep / max_sep,
        aligned_metrics.gradient_capture_score,
        float(np.exp(-aligned_metrics.heater_mismatch / 16.0)),
        aligned_metrics.balance_score,
        aligned_metrics.size_compliance,
    ]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    equal_values += equal_values[:1]
    aligned_values += aligned_values[:1]

    fig = plt.figure(figsize=(7.0, 6.4))
    axis = fig.add_subplot(111, polar=True)
    axis.plot(angles, equal_values, color="#2563eb", linewidth=2, label="等距分区")
    axis.fill(angles, equal_values, color="#2563eb", alpha=0.16)
    axis.plot(angles, aligned_values, color="#dc2626", linewidth=2, label="模块对齐分区")
    axis.fill(angles, aligned_values, color="#dc2626", alpha=0.16)
    axis.set_xticks(angles[:-1])
    axis.set_xticklabels(labels)
    axis.tick_params(axis="x", pad=10)
    axis.set_ylim(0, 1.0)
    axis.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.28, 1.18))
    axis.set_title("质量雷达图", loc="left", fontsize=12, fontweight="bold", pad=22)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.90, bottom=0.08)
    _apply_matplotlib_style(fig)
    return fig


def figure_to_html(fig: "go.Figure") -> str:
    _require_plotly()
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"displayModeBar": False, "responsive": True},
        default_width="100%",
    )
