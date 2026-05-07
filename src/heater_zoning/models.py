from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import pandas as pd


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

    def to_display_rows(self, method_name: str) -> List[Dict[str, float]]:
        return [
            {"方法": method_name, "指标": "区内拟合误差 E_fit", "值": self.e_fit},
            {"方法": method_name, "指标": "加权拟合误差", "值": self.weighted_fit_error},
            {"方法": method_name, "指标": "分区分离度 E_sep", "值": self.e_sep},
            {"方法": method_name, "指标": "梯度边界贴合度", "值": self.gradient_capture_score},
            {"方法": method_name, "指标": "尺寸合规率", "值": self.size_compliance},
            {"方法": method_name, "指标": "安装长度误差", "值": self.heater_mismatch},
            {"方法": method_name, "指标": "均衡性", "值": self.balance_score},
            {"方法": method_name, "指标": "内部违规数", "值": self.internal_violations},
            {"方法": method_name, "指标": "综合得分", "值": self.composite_score},
            {"方法": method_name, "指标": "模块总数", "值": self.total_modules},
            {"方法": method_name, "指标": "安装总长度(mm)", "值": self.total_install_length_mm},
            {"方法": method_name, "指标": "模块本体总长度(mm)", "值": self.total_body_length_mm},
            {"方法": method_name, "指标": "模块间距总长度(mm)", "值": self.total_gap_length_mm},
            {"方法": method_name, "指标": "左侧总外伸(mm)", "值": self.total_left_overhang_mm},
            {"方法": method_name, "指标": "右侧总外伸(mm)", "值": self.total_right_overhang_mm},
        ]


@dataclass
class AnalysisResult:
    profile_df: pd.DataFrame
    config: Dict[str, float]
    equal_zones: List[ZoneResult]
    aligned_zones: List[ZoneResult]
    equal_metrics: MethodMetrics
    aligned_metrics: MethodMetrics
