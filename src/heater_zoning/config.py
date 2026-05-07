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
        return self

    def to_dict(self):
        return asdict(self)

