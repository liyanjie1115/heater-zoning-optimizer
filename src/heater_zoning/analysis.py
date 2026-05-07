import math
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from .config import AnalysisConfig
from .models import AnalysisResult, MethodMetrics, ZoneResult


def calc_install_length(modules: int, module_length: float, module_gap: float) -> float:
    if modules <= 0:
        return 0.0
    return modules * module_length + (modules - 1) * module_gap


def calc_gap_length(modules: int, module_gap: float) -> float:
    return 0.0 if modules <= 1 else (modules - 1) * module_gap


def get_segment_points_with_interpolation(
    dist: np.ndarray, temp: np.ndarray, x0: float, x1: float
) -> Tuple[np.ndarray, np.ndarray]:
    mask = (dist > x0) & (dist < x1)
    inner_x = dist[mask]
    inner_t = temp[mask]

    t0 = np.interp(x0, dist, temp)
    t1 = np.interp(x1, dist, temp)

    x_all = np.concatenate(([x0], inner_x, [x1]))
    t_all = np.concatenate(([t0], inner_t, [t1]))

    order = np.argsort(x_all)
    return x_all[order], t_all[order]


def compute_weights(dist: np.ndarray, temp: np.ndarray, alpha: float) -> np.ndarray:
    grad = np.zeros(len(temp))
    for idx in range(1, len(temp)):
        dx = dist[idx] - dist[idx - 1]
        if dx > 0:
            grad[idx] = abs(temp[idx] - temp[idx - 1]) / dx

    gmax = np.max(grad) if np.max(grad) > 0 else 1.0
    return 1.0 + alpha * (grad / gmax)


def calc_max_fittable_modules(
    zone_size: float,
    is_first_zone: bool,
    is_last_zone: bool,
    config: AnalysisConfig,
) -> int:
    effective_size = zone_size
    if is_first_zone:
        effective_size += config.outer_edge_allow
    if is_last_zone:
        effective_size += config.outer_edge_allow

    if effective_size < config.module_length:
        return 1

    modules = math.floor((effective_size + config.module_gap) / config.module_pitch)
    return max(1, modules)


def compute_actual_overhang(
    zone_size: float, modules: int, is_first_zone: bool, is_last_zone: bool, config: AnalysisConfig
) -> Tuple[float, float, float, float]:
    install_length = calc_install_length(modules, config.module_length, config.module_gap)
    exceed = max(0.0, install_length - zone_size)

    left_overhang = 0.0
    right_overhang = 0.0
    if exceed > 0:
        if is_first_zone and not is_last_zone:
            left_overhang = exceed
        elif is_last_zone and not is_first_zone:
            right_overhang = exceed
        elif is_first_zone and is_last_zone:
            left_overhang = exceed / 2.0
            right_overhang = exceed / 2.0

    return install_length, exceed, left_overhang, right_overhang


def compute_module_positions_in_zone(
    x0: float, x1: float, modules: int, is_first: bool, is_last: bool, config: AnalysisConfig
) -> List[Tuple[float, float]]:
    zone_length = x1 - x0
    install_length = calc_install_length(modules, config.module_length, config.module_gap)

    if is_first and install_length > zone_length:
        start_pos = x1 - install_length
    elif is_last and install_length > zone_length:
        start_pos = x0
    else:
        start_pos = x0 + 0.5 * (zone_length - install_length)

    positions = []
    for idx in range(modules):
        xs = start_pos + idx * config.module_pitch
        xe = xs + config.module_length
        positions.append((xs, xe))
    return positions


def build_equal_edges(total_length: float, zone_count: int) -> np.ndarray:
    return np.linspace(0.0, total_length, zone_count + 1)


def build_module_edges(total_length: float, pitch: float) -> np.ndarray:
    n_full = int(total_length // pitch)
    edges = [idx * pitch for idx in range(n_full + 1)]
    if edges[-1] < total_length:
        edges.append(total_length)
    return np.array(edges)


def segment_cost_on_edges(
    dist: np.ndarray, temp: np.ndarray, weights: np.ndarray, x0: float, x1: float
) -> Tuple[float, float]:
    seg_x, seg_t = get_segment_points_with_interpolation(dist, temp, x0, x1)
    if len(seg_t) < 2:
        return np.inf, float("nan")

    seg_w = np.interp(seg_x, dist, weights)
    mean_t = float(np.sum(seg_w * seg_t) / np.sum(seg_w))
    cost = float(np.sum(seg_w * (seg_t - mean_t) ** 2))
    return cost, mean_t


def build_zone_result(
    idx: int,
    total_zones: int,
    x0: float,
    x1: float,
    avg_temp: float,
    dist: np.ndarray,
    temp: np.ndarray,
    config: AnalysisConfig,
) -> ZoneResult:
    size = x1 - x0
    is_first = idx == 0
    is_last = idx == total_zones - 1
    modules = calc_max_fittable_modules(size, is_first, is_last, config)
    install_length, exceed, left_overhang, right_overhang = compute_actual_overhang(
        size, modules, is_first, is_last, config
    )
    segment_x, segment_t = get_segment_points_with_interpolation(dist, temp, x0, x1)
    module_positions = compute_module_positions_in_zone(x0, x1, modules, is_first, is_last, config)

    return ZoneResult(
        zone_id=idx + 1,
        start_mm=float(x0),
        end_mm=float(x1),
        size_mm=float(size),
        modules=modules,
        avg_temp_c=float(avg_temp),
        install_length_mm=float(install_length),
        body_length_mm=float(modules * config.module_length),
        gap_length_mm=float(calc_gap_length(modules, config.module_gap)),
        exceed_length_mm=float(exceed),
        left_overhang_mm=float(left_overhang),
        right_overhang_mm=float(right_overhang),
        is_first=is_first,
        is_last=is_last,
        segment_x=segment_x.tolist(),
        segment_t=segment_t.tolist(),
        module_positions=module_positions,
    )


def build_equal_zones(
    dist: np.ndarray, temp: np.ndarray, config: AnalysisConfig
) -> List[ZoneResult]:
    edges = build_equal_edges(config.total_length, config.equal_zone_count)
    zones = []
    for idx in range(config.equal_zone_count):
        x0, x1 = float(edges[idx]), float(edges[idx + 1])
        _, seg_t = get_segment_points_with_interpolation(dist, temp, x0, x1)
        zones.append(
            build_zone_result(
                idx=idx,
                total_zones=config.equal_zone_count,
                x0=x0,
                x1=x1,
                avg_temp=float(np.mean(seg_t)),
                dist=dist,
                temp=temp,
                config=config,
            )
        )
    return zones


def optimal_partition_aligned(
    dist: np.ndarray, temp: np.ndarray, weights: np.ndarray, config: AnalysisConfig
) -> Tuple[np.ndarray, List[Tuple[int, int]], List[List[float]]]:
    edges = build_module_edges(config.total_length, config.module_pitch)
    edge_count = len(edges)

    dp = np.full((config.max_zones + 1, edge_count), np.inf)
    split = np.full((config.max_zones + 1, edge_count), -1, dtype=int)
    dp[0, 0] = 0.0

    cost_table = [[np.inf] * edge_count for _ in range(edge_count)]
    mean_table = [[float("nan")] * edge_count for _ in range(edge_count)]

    for start_idx in range(edge_count - 1):
        for end_idx in range(start_idx + 1, edge_count):
            x0, x1 = edges[start_idx], edges[end_idx]
            if (x1 - x0) < config.min_zone_size:
                continue
            cost, mean_t = segment_cost_on_edges(dist, temp, weights, float(x0), float(x1))
            cost_table[start_idx][end_idx] = cost
            mean_table[start_idx][end_idx] = mean_t

    for zone_count in range(1, config.max_zones + 1):
        for end_idx in range(1, edge_count):
            for start_idx in range(end_idx):
                if np.isinf(cost_table[start_idx][end_idx]):
                    continue
                total_cost = dp[zone_count - 1, start_idx] + cost_table[start_idx][end_idx]
                if total_cost < dp[zone_count, end_idx]:
                    dp[zone_count, end_idx] = total_cost
                    split[zone_count, end_idx] = start_idx

    final_edge = edge_count - 1
    best_zone_count = int(np.argmin(dp[1:, final_edge]) + 1)
    zone_indexes = []
    current_end = final_edge
    current_k = best_zone_count
    while current_k > 0:
        current_start = int(split[current_k, current_end])
        zone_indexes.append((current_start, current_end))
        current_end = current_start
        current_k -= 1

    zone_indexes.reverse()
    return edges, zone_indexes, mean_table


def build_aligned_zones(
    dist: np.ndarray, temp: np.ndarray, config: AnalysisConfig
) -> List[ZoneResult]:
    weights = compute_weights(dist, temp, config.alpha)
    edges, zone_indexes, mean_table = optimal_partition_aligned(dist, temp, weights, config)
    total = len(zone_indexes)
    zones = []
    for idx, (start_idx, end_idx) in enumerate(zone_indexes):
        x0, x1 = float(edges[start_idx]), float(edges[end_idx])
        zones.append(
            build_zone_result(
                idx=idx,
                total_zones=total,
                x0=x0,
                x1=x1,
                avg_temp=float(mean_table[start_idx][end_idx]),
                dist=dist,
                temp=temp,
                config=config,
            )
        )
    return zones


def evaluate_zoning_quality(
    dist: np.ndarray, temp: np.ndarray, zones: Sequence[ZoneResult], config: AnalysisConfig
) -> MethodMetrics:
    zone_means = []
    zone_sizes = []
    fit_error = 0.0
    heater_errors = []
    internal_violations = 0

    for zone in zones:
        _, seg_t = get_segment_points_with_interpolation(dist, temp, zone.start_mm, zone.end_mm)
        mean = float(np.mean(seg_t))
        zone_means.append(mean)
        zone_sizes.append(zone.size_mm)
        fit_error += float(np.sum((seg_t - mean) ** 2))

        effective_size = zone.size_mm
        if zone.is_first:
            effective_size += config.outer_edge_allow
        if zone.is_last:
            effective_size += config.outer_edge_allow

        if zone.install_length_mm > effective_size + 1e-9:
            internal_violations += 1
        heater_errors.append(abs(zone.size_mm - zone.install_length_mm))

    n_points = len(temp)
    zone_count = len(zones)
    e_fit = fit_error / n_points if n_points else float("inf")
    e_sep = (
        float(np.mean([abs(zone_means[idx + 1] - zone_means[idx]) for idx in range(zone_count - 1)]))
        if zone_count > 1
        else 0.0
    )
    size_compliance = (
        sum(1 for size in zone_sizes if size >= config.min_zone_size) / zone_count if zone_count else 0.0
    )
    heater_mismatch = float(np.mean(heater_errors)) if heater_errors else float("inf")
    cv = float(np.std(zone_sizes) / np.mean(zone_sizes)) if zone_count > 1 else 0.0

    s_fit = math.exp(-e_fit / 1000.0)
    s_sep = e_sep / (max(zone_means) - min(zone_means) + 1e-6) if len(zone_means) > 1 else 0.0
    s_heater = math.exp(-heater_mismatch / 10.0)
    s_balance = 1.0 / (1.0 + cv)
    penalty = 0.15 * internal_violations
    composite = max(0.0, 0.35 * s_fit + 0.25 * s_sep + 0.2 * s_heater + 0.2 * s_balance - penalty)

    return MethodMetrics(
        e_fit=float(e_fit),
        e_sep=float(e_sep),
        size_compliance=float(size_compliance),
        heater_mismatch=float(heater_mismatch),
        balance_score=float(s_balance),
        internal_violations=internal_violations,
        composite_score=float(composite),
        total_modules=int(sum(zone.modules for zone in zones)),
        total_install_length_mm=float(sum(zone.install_length_mm for zone in zones)),
        total_body_length_mm=float(sum(zone.body_length_mm for zone in zones)),
        total_gap_length_mm=float(sum(zone.gap_length_mm for zone in zones)),
        total_left_overhang_mm=float(sum(zone.left_overhang_mm for zone in zones)),
        total_right_overhang_mm=float(sum(zone.right_overhang_mm for zone in zones)),
    )


def representative_points_dataframe(zones: Sequence[ZoneResult], dist: np.ndarray, temp: np.ndarray, method_name: str) -> pd.DataFrame:
    rows = []
    for zone in zones:
        zone_length = zone.end_mm - zone.start_mm
        points = {
            "左点": zone.start_mm + 0.30 * zone_length,
            "中点": zone.start_mm + 0.50 * zone_length,
            "右点": zone.end_mm - 0.30 * zone_length,
        }
        for point_name, x_pos in points.items():
            rows.append(
                {
                    "方法": method_name,
                    "分区编号": zone.zone_id,
                    "点位名称": point_name,
                    "坐标_mm": float(x_pos),
                    "温度_C": float(np.interp(x_pos, dist, temp)),
                    "分区起点_mm": zone.start_mm,
                    "分区终点_mm": zone.end_mm,
                    "分区长度_mm": zone.size_mm,
                }
            )
    return pd.DataFrame(rows)


def zones_dataframe(zones: Sequence[ZoneResult], method_name: str, dist: np.ndarray, temp: np.ndarray) -> pd.DataFrame:
    rows = []
    for zone in zones:
        midpoint = 0.5 * (zone.start_mm + zone.end_mm)
        midpoint_temp = float(np.interp(midpoint, dist, temp))
        positions_text = "; ".join(
            f"M{idx + 1}:[{start:.1f},{end:.1f}]"
            for idx, (start, end) in enumerate(zone.module_positions)
        )
        rows.append(
            {
                "方法": method_name,
                "分区编号": zone.zone_id,
                "起点_mm": zone.start_mm,
                "终点_mm": zone.end_mm,
                "中点_mm": midpoint,
                "中点温度_C": midpoint_temp,
                "分区长度_mm": zone.size_mm,
                "模块数": zone.modules,
                "模块长度_mm": zone.body_length_mm / zone.modules if zone.modules else 0.0,
                "模块间距_mm": zone.gap_length_mm / (zone.modules - 1) if zone.modules > 1 else 0.0,
                "模块本体总长_mm": zone.body_length_mm,
                "模块间距总长_mm": zone.gap_length_mm,
                "安装总长_mm": zone.install_length_mm,
                "左侧外伸_mm": zone.left_overhang_mm,
                "右侧外伸_mm": zone.right_overhang_mm,
                "模块实际位置": positions_text,
                "分区平均温度_C": zone.avg_temp_c,
            }
        )
    return pd.DataFrame(rows)


def metrics_dataframe(equal_metrics: MethodMetrics, aligned_metrics: MethodMetrics) -> pd.DataFrame:
    rows = equal_metrics.to_display_rows("等距分区") + aligned_metrics.to_display_rows("模块对齐分区")
    return pd.DataFrame(rows)


def analyze_profile(profile_df: pd.DataFrame, config: AnalysisConfig) -> AnalysisResult:
    config.validate()

    profile_df = profile_df.copy().sort_values("distance_mm").reset_index(drop=True)
    dist = profile_df["distance_mm"].to_numpy(dtype=float)
    temp = profile_df["temperature_c"].to_numpy(dtype=float)

    if dist[0] > 0:
        raise ValueError("输入数据必须从 0 mm 开始。")
    if dist[-1] < config.total_length:
        raise ValueError("输入数据末端必须覆盖到总长度。")

    equal_zones = build_equal_zones(dist, temp, config)
    aligned_zones = build_aligned_zones(dist, temp, config)
    equal_metrics = evaluate_zoning_quality(dist, temp, equal_zones, config)
    aligned_metrics = evaluate_zoning_quality(dist, temp, aligned_zones, config)

    return AnalysisResult(
        profile_df=profile_df,
        config=config.to_dict(),
        equal_zones=equal_zones,
        aligned_zones=aligned_zones,
        equal_metrics=equal_metrics,
        aligned_metrics=aligned_metrics,
    )

