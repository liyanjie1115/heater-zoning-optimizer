from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import pandas as pd


@dataclass(frozen=True)
class MetricDefinition:
    key: str
    label: str
    direction: str
    included_in_score: bool
    description: str


@dataclass
class ZoneResult:
    zone_id: int
    start_mm: float
    end_mm: float
    size_mm: float
    modules: int
    avg_temp_c: float
    install_length_mm: float
    body_length_mm: float
    gap_length_mm: float
    exceed_length_mm: float
    left_overhang_mm: float
    right_overhang_mm: float
    is_first: bool
    is_last: bool
    segment_x: Sequence[float] = field(default_factory=list)
    segment_t: Sequence[float] = field(default_factory=list)
    module_positions: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class MethodMetrics:
    e_fit: float
    e_sep: float
    size_compliance: float
    heater_mismatch: float
    balance_score: float
    internal_violations: int
    weighted_fit_error: float
    gradient_capture_score: float
    composite_score: float
    total_modules: int
    total_install_length_mm: float
    total_body_length_mm: float
    total_gap_length_mm: float
    total_left_overhang_mm: float
    total_right_overhang_mm: float

    @staticmethod
    def metric_definitions() -> List[MetricDefinition]:
        return [
            MetricDefinition("e_fit", "区内拟合误差 E_fit", "越小越好", False, "原始区内温度波动误差，用于补充观察拟合稳定性。"),
            MetricDefinition("weighted_fit_error", "加权拟合误差", "越小越好", True, "对温度梯度较大的位置加权后的区内拟合误差。"),
            MetricDefinition("e_sep", "分区分离度 E_sep", "越大越好", True, "相邻分区平均温差，越大表示分区温度区分更明显。"),
            MetricDefinition("gradient_capture_score", "边界贴合度", "越大越好", True, "分区边界对温度梯度突变位置的贴合程度。"),
            MetricDefinition("size_compliance", "尺寸合规率", "越大越好", False, "满足最小分区尺寸要求的分区占比。"),
            MetricDefinition("heater_mismatch", "安装长度误差", "越小越好", True, "分区长度与模块安装长度的平均偏差。"),
            MetricDefinition("balance_score", "均衡性", "越大越好", True, "分区长度均衡程度，越接近 1 越均衡。"),
            MetricDefinition("internal_violations", "内部违规数", "越小越好", False, "安装长度超出有效分区尺寸的分区数量。"),
            MetricDefinition("composite_score", "综合得分", "越大越好", True, "最终推荐直接依据的综合评分。"),
            MetricDefinition("total_modules", "总模块数", "视项目而定", False, "全部分区使用的模块总数，便于估算工程量。"),
            MetricDefinition("total_install_length_mm", "总安装占位长度 (mm)", "视项目而定", False, "模块安装总占位长度。"),
            MetricDefinition("total_body_length_mm", "总模块本体长度 (mm)", "视项目而定", False, "模块本体长度总和，不含间距。"),
            MetricDefinition("total_gap_length_mm", "总间距长度 (mm)", "视项目而定", False, "模块之间间距总和。"),
            MetricDefinition("total_left_overhang_mm", "左侧总外伸 (mm)", "越小越好", False, "左侧边缘外伸总长度。"),
            MetricDefinition("total_right_overhang_mm", "右侧总外伸 (mm)", "越小越好", False, "右侧边缘外伸总长度。"),
        ]

    def metric_value_map(self) -> Dict[str, float]:
        return {
            "e_fit": self.e_fit,
            "weighted_fit_error": self.weighted_fit_error,
            "e_sep": self.e_sep,
            "gradient_capture_score": self.gradient_capture_score,
            "size_compliance": self.size_compliance,
            "heater_mismatch": self.heater_mismatch,
            "balance_score": self.balance_score,
            "internal_violations": self.internal_violations,
            "composite_score": self.composite_score,
            "total_modules": self.total_modules,
            "total_install_length_mm": self.total_install_length_mm,
            "total_body_length_mm": self.total_body_length_mm,
            "total_gap_length_mm": self.total_gap_length_mm,
            "total_left_overhang_mm": self.total_left_overhang_mm,
            "total_right_overhang_mm": self.total_right_overhang_mm,
        }


@dataclass
class AnalysisResult:
    profile_df: pd.DataFrame
    config: Dict[str, float]
    equal_zones: List[ZoneResult]
    aligned_zones: List[ZoneResult]
    equal_metrics: MethodMetrics
    aligned_metrics: MethodMetrics
