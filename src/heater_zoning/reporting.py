from dataclasses import dataclass

import pandas as pd

from .analysis import (
    compute_gradient_profile,
    compute_weights,
    metrics_dataframe,
    representative_points_dataframe,
    zones_dataframe,
)
from .config import AnalysisConfig
from .models import AnalysisResult, MethodMetrics, ZoneResult


@dataclass
class ReportFrames:
    profile: pd.DataFrame
    equal_zones: pd.DataFrame
    aligned_zones: pd.DataFrame
    equal_points: pd.DataFrame
    aligned_points: pd.DataFrame
    metrics: pd.DataFrame
    differences: pd.DataFrame
    partition_variable_mapping: pd.DataFrame
    fig3_temperature_boundaries: pd.DataFrame
    fig3_module_layout: pd.DataFrame
    table4_partition_comparison: pd.DataFrame
    paper_partition_details: pd.DataFrame


def build_report_frames(result: AnalysisResult) -> ReportFrames:
    distance = result.profile_df["distance_mm"].to_numpy()
    temperature = result.profile_df["temperature_c"].to_numpy()
    config = AnalysisConfig(**result.config).validate()
    return ReportFrames(
        profile=result.profile_df.copy(),
        equal_zones=zones_dataframe(result.equal_zones, "等距分区", distance, temperature),
        aligned_zones=zones_dataframe(result.aligned_zones, "模块对齐分区", distance, temperature),
        equal_points=representative_points_dataframe(result.equal_zones, distance, temperature, "等距分区", config),
        aligned_points=representative_points_dataframe(result.aligned_zones, distance, temperature, "模块对齐分区", config),
        metrics=metrics_dataframe(result.equal_metrics, result.aligned_metrics),
        differences=build_difference_table(result),
        partition_variable_mapping=build_partition_variable_mapping_table(result),
        fig3_temperature_boundaries=build_fig3_temperature_boundary_data(result),
        fig3_module_layout=build_fig3_module_layout_data(result),
        table4_partition_comparison=build_table4_partition_comparison(result),
        paper_partition_details=build_paper_partition_detail_table(result),
    )


def _paper_methods(result: AnalysisResult):
    return (
        ("Equal-length partitioning", "等距分区", result.equal_zones, result.equal_metrics),
        ("Engineering-constrained partitioning", "模块对齐分区", result.aligned_zones, result.aligned_metrics),
    )


def _zone_label(zone: ZoneResult) -> str:
    return f"Omega_{zone.zone_id}"


def build_partition_variable_mapping_table(result: AnalysisResult) -> pd.DataFrame:
    config = AnalysisConfig(**result.config)
    aligned_zone_count = len(result.aligned_zones)
    return pd.DataFrame(
        [
            {
                "paper_symbol": "s",
                "paper_name": "Coordinate along target heating path",
                "software_field": "distance_mm",
                "software_value": "",
                "unit": "mm",
                "description": "目标温度路径坐标。",
            },
            {
                "paper_symbol": "T_tar(s)",
                "paper_name": "Target temperature distribution",
                "software_field": "temperature_c",
                "software_value": "",
                "unit": "degC",
                "description": "目标温度剖面。",
            },
            {
                "paper_symbol": "L",
                "paper_name": "Length of target heating path",
                "software_field": "total_length",
                "software_value": config.total_length,
                "unit": "mm",
                "description": "目标路径总长度。",
            },
            {
                "paper_symbol": "K",
                "paper_name": "Number of heating zones",
                "software_field": "len(aligned_zones)",
                "software_value": aligned_zone_count,
                "unit": "-",
                "description": "工程约束分区方案的分区数。",
            },
            {
                "paper_symbol": "Omega_k",
                "paper_name": "The k-th heating zone",
                "software_field": "zone_id / start_mm / end_mm",
                "software_value": "",
                "unit": "-",
                "description": "第 k 个加热分区及其左右边界。",
            },
            {
                "paper_symbol": "b_k",
                "paper_name": "Boundary position of the k-th partition",
                "software_field": "start_mm / end_mm",
                "software_value": "",
                "unit": "mm",
                "description": "分区边界坐标。",
            },
            {
                "paper_symbol": "l_m",
                "paper_name": "Length of a heating module",
                "software_field": "module_length",
                "software_value": config.module_length,
                "unit": "mm",
                "description": "单个加热模块长度。",
            },
            {
                "paper_symbol": "d_m",
                "paper_name": "Gap between adjacent modules",
                "software_field": "module_gap",
                "software_value": config.module_gap,
                "unit": "mm",
                "description": "相邻模块间距。",
            },
            {
                "paper_symbol": "s_m",
                "paper_name": "Module pitch",
                "software_field": "module_pitch",
                "software_value": config.module_pitch,
                "unit": "mm",
                "description": "模块节距，s_m = l_m + d_m。",
            },
        ]
    )


def build_fig3_temperature_boundary_data(result: AnalysisResult) -> pd.DataFrame:
    profile = result.profile_df.copy().sort_values("distance_mm").reset_index(drop=True)
    config = AnalysisConfig(**result.config)
    distance = profile["distance_mm"].to_numpy(dtype=float)
    temperature = profile["temperature_c"].to_numpy(dtype=float)
    gradient = compute_gradient_profile(distance, temperature)
    gradient_max = max(float(gradient.max()), 1.0)
    weights = compute_weights(distance, temperature, config.alpha)

    rows = []
    for s_mm, t_tar, grad, weight in zip(distance, temperature, gradient, weights):
        rows.append(
            {
                "row_type": "target_profile",
                "method": "",
                "k": "",
                "Omega_k": "",
                "s_mm": float(s_mm),
                "T_tar_C": float(t_tar),
                "gradient_abs_C_per_mm": float(grad),
                "gradient_norm": float(grad / gradient_max),
                "partition_weight": float(weight),
                "b_left_mm": "",
                "b_right_mm": "",
                "Tbar_k_C": "",
            }
        )

    for paper_method, _, zones, _ in _paper_methods(result):
        for zone in zones:
            rows.append(
                {
                    "row_type": "zone_interval",
                    "method": paper_method,
                    "k": zone.zone_id,
                    "Omega_k": _zone_label(zone),
                    "s_mm": "",
                    "T_tar_C": "",
                    "gradient_abs_C_per_mm": "",
                    "gradient_norm": "",
                    "partition_weight": "",
                    "b_left_mm": zone.start_mm,
                    "b_right_mm": zone.end_mm,
                    "Tbar_k_C": zone.avg_temp_c,
                }
            )
    return pd.DataFrame(rows)


def build_fig3_module_layout_data(result: AnalysisResult) -> pd.DataFrame:
    config = AnalysisConfig(**result.config)
    rows = []
    for paper_method, _, zones, _ in _paper_methods(result):
        for zone in zones:
            for module_index, (start_mm, end_mm) in enumerate(zone.module_positions, start=1):
                rows.append(
                    {
                        "method": paper_method,
                        "k": zone.zone_id,
                        "Omega_k": _zone_label(zone),
                        "module_index": module_index,
                        "module_start_mm": float(start_mm),
                        "module_end_mm": float(end_mm),
                        "module_center_mm": float(0.5 * (start_mm + end_mm)),
                        "module_length_mm": config.module_length,
                        "module_gap_mm": config.module_gap,
                        "zone_start_mm": zone.start_mm,
                        "zone_end_mm": zone.end_mm,
                    }
                )
    return pd.DataFrame(rows)


def build_table4_partition_comparison(result: AnalysisResult) -> pd.DataFrame:
    equal_error = float(result.equal_metrics.e_fit)
    rows = []
    for paper_method, method_zh, zones, metrics in _paper_methods(result):
        e_part = float(metrics.e_fit)
        reduction = "" if paper_method == "Equal-length partitioning" else (equal_error - e_part) / max(equal_error, 1e-9) * 100
        zone_count = len(zones)
        compliance = (
            (zone_count - int(metrics.internal_violations)) / zone_count * 100 if zone_count else 0.0
        )
        rows.append(
            {
                "Method": paper_method,
                "方法": method_zh,
                "K": zone_count,
                "E_part": e_part,
                "reduction_%": reduction,
                "compliance_%": compliance,
                "total_modules": metrics.total_modules,
                "total_install_length_mm": metrics.total_install_length_mm,
                "heater_mismatch_mm": metrics.heater_mismatch,
            }
        )
    return pd.DataFrame(rows)


def build_paper_partition_detail_table(result: AnalysisResult) -> pd.DataFrame:
    config = AnalysisConfig(**result.config)
    rows = []
    for paper_method, method_zh, zones, _ in _paper_methods(result):
        for zone in zones:
            rows.append(
                {
                    "method": paper_method,
                    "方法": method_zh,
                    "k": zone.zone_id,
                    "Omega_k": _zone_label(zone),
                    "b_{k-1}_mm": zone.start_mm,
                    "b_k_mm": zone.end_mm,
                    "Delta_s_k_mm": zone.size_mm,
                    "Tbar_k_C": zone.avg_temp_c,
                    "n_k": zone.modules,
                    "l_m_mm": config.module_length,
                    "d_m_mm": config.module_gap,
                    "s_m_mm": config.module_pitch,
                    "L_install_k_mm": zone.install_length_mm,
                    "left_overhang_mm": zone.left_overhang_mm,
                    "right_overhang_mm": zone.right_overhang_mm,
                }
            )
    return pd.DataFrame(rows)


def _winner_name(result: AnalysisResult) -> str:
    equal = result.equal_metrics
    aligned = result.aligned_metrics
    return "等距分区" if equal.composite_score >= aligned.composite_score else "模块对齐分区"


def _score_gap_label(score_gap: float) -> str:
    if score_gap >= 0.08:
        return "差异明显"
    if score_gap >= 0.03:
        return "差异中等"
    return "差异较小"


def build_summary_cards(result: AnalysisResult):
    equal = result.equal_metrics
    aligned = result.aligned_metrics
    winner = _winner_name(result)
    score_gap = abs(equal.composite_score - aligned.composite_score)
    zone_gap = len(result.equal_zones) - len(result.aligned_zones)
    return [
        {"label": "推荐方案", "value": winner, "accent": "neutral"},
        {"label": "推荐把握", "value": _score_gap_label(score_gap), "accent": "green"},
        {"label": "等距分区得分", "value": f"{equal.composite_score:.2f}", "accent": "blue"},
        {"label": "模块对齐得分", "value": f"{aligned.composite_score:.2f}", "accent": "red"},
        {"label": "得分差值", "value": f"{score_gap:.2f}", "accent": "green"},
        {"label": "分区数量差", "value": f"{zone_gap:+d}", "accent": "neutral"},
    ]


def build_recommendation_reasons(result: AnalysisResult) -> list[str]:
    equal_map = result.equal_metrics.metric_value_map()
    aligned_map = result.aligned_metrics.metric_value_map()
    winner = _winner_name(result)
    reasons: list[tuple[float, str]] = []

    for definition in MethodMetrics.metric_definitions():
        if not definition.included_in_score or definition.key == "composite_score":
            continue

        equal_value = float(equal_map[definition.key])
        aligned_value = float(aligned_map[definition.key])
        denom = max(abs(equal_value), abs(aligned_value), 1e-9)
        gap = abs(equal_value - aligned_value) / denom

        if definition.direction == "越大越好":
            better = "等距分区" if equal_value > aligned_value else "模块对齐分区" if aligned_value > equal_value else "持平"
        else:
            better = "等距分区" if equal_value < aligned_value else "模块对齐分区" if aligned_value < equal_value else "持平"

        if better == winner and gap > 0:
            reasons.append((gap, f"{definition.label}更优"))

    reasons.sort(key=lambda item: item[0], reverse=True)
    top_reasons = [text for _, text in reasons[:3]]
    if not top_reasons:
        top_reasons.append("综合得分略占优势")
    return top_reasons


def build_recommendation_summary(result: AnalysisResult) -> dict[str, object]:
    equal = result.equal_metrics
    aligned = result.aligned_metrics
    winner = _winner_name(result)
    loser_score = aligned.composite_score if winner == "等距分区" else equal.composite_score
    winner_score = equal.composite_score if winner == "等距分区" else aligned.composite_score
    score_gap = winner_score - loser_score

    return {
        "winner": winner,
        "message": (
            f"当前推荐 {winner}。综合得分高出 {score_gap:.2f}。"
            "建议先按该方案落图，再结合安装误差、模块数和外伸长度确认是否符合现场偏好。"
        ),
        "reasons": build_recommendation_reasons(result),
    }


def build_decision_overview(result: AnalysisResult) -> list[dict[str, str]]:
    winner = _winner_name(result)
    reasons = build_recommendation_reasons(result)
    core_win_count = 0
    risk_count = 0
    equal_map = result.equal_metrics.metric_value_map()
    aligned_map = result.aligned_metrics.metric_value_map()

    for definition in MethodMetrics.metric_definitions():
        if not definition.included_in_score or definition.key == "composite_score":
            continue

        equal_value = float(equal_map[definition.key])
        aligned_value = float(aligned_map[definition.key])
        if definition.direction == "越大越好":
            better = "等距分区" if equal_value > aligned_value else "模块对齐分区" if aligned_value > equal_value else "持平"
        else:
            better = "等距分区" if equal_value < aligned_value else "模块对齐分区" if aligned_value < equal_value else "持平"

        if better == winner:
            core_win_count += 1

    if max(result.equal_metrics.internal_violations, result.aligned_metrics.internal_violations) > 0:
        risk_count += 1
    if min(result.equal_metrics.size_compliance, result.aligned_metrics.size_compliance) < 1.0:
        risk_count += 1
    if abs(result.equal_metrics.composite_score - result.aligned_metrics.composite_score) < 0.03:
        risk_count += 1

    return [
        {"label": "关键评分项胜出", "value": f"{core_win_count} 项", "meta": "、".join(reasons)},
        {"label": "需重点复核项", "value": f"{risk_count} 项", "meta": ""},
        {
            "label": "推荐方案分区数",
            "value": str(len(result.equal_zones) if winner == "等距分区" else len(result.aligned_zones)),
            "meta": "",
        },
    ]


def build_config_snapshot(result: AnalysisResult) -> list[dict[str, str]]:
    config = AnalysisConfig(**result.config)
    return [
        {"label": "总长度", "value": f"{config.total_length:.2f} mm"},
        {"label": "最大分区数", "value": str(config.max_zones)},
        {"label": "等距分区数", "value": str(config.equal_zone_count)},
        {"label": "模块长度", "value": f"{config.module_length:.2f} mm"},
        {"label": "模块间距", "value": f"{config.module_gap:.2f} mm"},
        {"label": "边缘外伸余量", "value": f"{config.outer_edge_allow:.2f} mm"},
        {"label": "梯度权重 α", "value": f"{config.alpha:.2f}"},
    ]


def build_analysis_notes(result: AnalysisResult) -> list[dict[str, str]]:
    notes: list[dict[str, str]] = []
    equal = result.equal_metrics
    aligned = result.aligned_metrics
    winner = _winner_name(result)
    score_gap = abs(equal.composite_score - aligned.composite_score)

    if score_gap < 0.03:
        notes.append(
            {
                "level": "warn",
                "title": "推荐差距较小",
                "text": "两种方案综合得分接近，建议结合模块数、外伸长度和施工偏好再决定。",
            }
        )
    else:
        notes.append(
            {
                "level": "info",
                "title": "推荐差距明确",
                "text": f"{winner} 在综合得分上优势较清晰，适合作为默认方案进入下一步。",
            }
        )

    winner_metrics = aligned if winner == "模块对齐分区" else equal
    loser_metrics = equal if winner == "模块对齐分区" else aligned
    if winner_metrics.heater_mismatch > loser_metrics.heater_mismatch:
        notes.append(
            {
                "level": "warn",
                "title": "安装误差不是最优",
                "text": f"{winner} 的综合得分更高，但安装长度误差并非最优，建议复核安装容差。",
            }
        )

    if max(equal.internal_violations, aligned.internal_violations) > 0:
        notes.append(
            {
                "level": "warn",
                "title": "存在内部违规",
                "text": "至少有一个方案存在安装长度超出有效分区尺寸的情况，建议检查对应分区。",
            }
        )

    if min(equal.size_compliance, aligned.size_compliance) < 1.0:
        notes.append(
            {
                "level": "warn",
                "title": "尺寸未完全合规",
                "text": "部分分区未完全满足最小尺寸要求，需要结合指标表确认影响范围。",
            }
        )

    if len(notes) < 3:
        notes.append(
            {
                "level": "info",
                "title": "建议阅读顺序",
                "text": "先看推荐结论，再看归一化指标对比，最后用原始指标明细确认数值差异。",
            }
        )

    return notes


def build_zone_summary_table(result: AnalysisResult) -> pd.DataFrame:
    rows = []
    for method_name, zones in (("等距分区", result.equal_zones), ("模块对齐分区", result.aligned_zones)):
        for zone in zones:
            rows.append(
                {
                    "方案": method_name,
                    "分区": f"Z{zone.zone_id}",
                    "范围(mm)": f"{zone.start_mm:.2f} - {zone.end_mm:.2f}",
                    "长度(mm)": round(zone.size_mm, 2),
                    "平均温度(°C)": round(zone.avg_temp_c, 2),
                    "模块数": zone.modules,
                    "安装长度(mm)": round(zone.install_length_mm, 2),
                    "左外伸(mm)": round(zone.left_overhang_mm, 2),
                    "右外伸(mm)": round(zone.right_overhang_mm, 2),
                }
            )
    return pd.DataFrame(rows).round(2)


def build_difference_table(result: AnalysisResult) -> pd.DataFrame:
    equal_map = result.equal_metrics.metric_value_map()
    aligned_map = result.aligned_metrics.metric_value_map()
    rows = []
    for definition in MethodMetrics.metric_definitions():
        equal_value = float(equal_map[definition.key])
        aligned_value = float(aligned_map[definition.key])
        absolute_gap = aligned_value - equal_value

        if definition.direction == "越大越好":
            better = "等距分区" if equal_value > aligned_value else "模块对齐分区" if aligned_value > equal_value else "持平"
            relative_gap = 0.0 if abs(equal_value) < 1e-9 else absolute_gap / abs(equal_value)
        elif definition.direction == "越小越好":
            better = "等距分区" if equal_value < aligned_value else "模块对齐分区" if aligned_value < equal_value else "持平"
            relative_gap = 0.0 if abs(equal_value) < 1e-9 else -absolute_gap / abs(equal_value)
        else:
            better = "按项目判断"
            relative_gap = 0.0 if abs(equal_value) < 1e-9 else absolute_gap / abs(equal_value)

        rows.append(
            {
                "指标": definition.label,
                "指标方向": definition.direction,
                "等距分区": equal_value,
                "模块对齐分区": aligned_value,
                "绝对差值(模块对齐-等距)": absolute_gap,
                "相对变化": relative_gap,
                "更优方案": better,
            }
        )
    return pd.DataFrame(rows)
