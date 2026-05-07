from dataclasses import asdict, dataclass


@dataclass
class AnalysisConfig:
    total_length: float = 500.0
    max_zones: int = 8
    alpha: float = 5.0
    equal_zone_count: int = 8
    module_length: float = 23.0
    module_gap: float = 10.0
    outer_edge_allow: float = 10.0
    sample_left_ratio: float = 0.30
    sample_mid_ratio: float = 0.50
    sample_right_ratio: float = 0.70
    fit_weight: float = 0.32
    separation_weight: float = 0.22
    gradient_weight: float = 0.24
    heater_weight: float = 0.12
    balance_weight: float = 0.10
    fit_decay: float = 850.0
    heater_decay: float = 16.0
    internal_violation_penalty: float = 0.18
    size_compliance_penalty: float = 0.08

    @property
    def module_pitch(self) -> float:
        return self.module_length + self.module_gap

    @property
    def min_zone_size(self) -> float:
        return self.module_length

    def validate(self) -> "AnalysisConfig":
        if self.total_length <= 0:
            raise ValueError("总长度必须大于 0。")
        if self.max_zones < 1:
            raise ValueError("最大分区数必须至少为 1。")
        if self.equal_zone_count < 1:
            raise ValueError("等距分区数必须至少为 1。")
        if self.module_length <= 0:
            raise ValueError("模块长度必须大于 0。")
        if self.module_gap < 0:
            raise ValueError("模块间距不能为负数。")
        if self.outer_edge_allow < 0:
            raise ValueError("边缘外伸余量不能为负数。")

        ratios = [self.sample_left_ratio, self.sample_mid_ratio, self.sample_right_ratio]
        if any(ratio <= 0 or ratio >= 1 for ratio in ratios):
            raise ValueError("三点采样位置比例必须在 0 到 1 之间。")
        if not (self.sample_left_ratio < self.sample_mid_ratio < self.sample_right_ratio):
            raise ValueError("三点采样位置必须满足 左点 < 中点 < 右点。")

        weights = [
            self.fit_weight,
            self.separation_weight,
            self.gradient_weight,
            self.heater_weight,
            self.balance_weight,
        ]
        if any(weight < 0 for weight in weights):
            raise ValueError("评分权重不能为负数。")
        if sum(weights) <= 0:
            raise ValueError("评分权重之和必须大于 0。")

        if self.fit_decay <= 0:
            raise ValueError("拟合衰减系数必须大于 0。")
        if self.heater_decay <= 0:
            raise ValueError("安装匹配衰减系数必须大于 0。")
        if self.internal_violation_penalty < 0:
            raise ValueError("内部违规惩罚不能为负数。")
        if self.size_compliance_penalty < 0:
            raise ValueError("尺寸合规惩罚不能为负数。")
        return self

    def to_dict(self):
        return asdict(self)
