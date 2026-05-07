from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .analysis import analyze_profile
from .config import AnalysisConfig
from .exporters import export_analysis_excel
from .io_utils import normalize_profile_dataframe, read_profile_file
from .models import AnalysisResult
from .reporting import ReportFrames, build_report_frames, build_summary_cards, build_zone_summary_table
from .sample_data import sample_profile_dataframe


@dataclass
class AnalysisArtifacts:
    result: AnalysisResult
    frames: ReportFrames
    summary_cards: list
    zone_summary: object
    export_path: Path


def load_profile(source: str = "sample", file_path: Optional[str] = None):
    if source == "sample":
        return normalize_profile_dataframe(sample_profile_dataframe())
    if not file_path:
        raise ValueError("文件模式需要提供输入文件路径。")
    return read_profile_file(file_path)


def run_analysis_pipeline(
    config: AnalysisConfig,
    source: str = "sample",
    file_path: Optional[str] = None,
    output_dir: str = "outputs",
    output_name: Optional[str] = None,
) -> AnalysisArtifacts:
    profile_df = load_profile(source=source, file_path=file_path)
    return run_analysis_for_dataframe(
        profile_df=profile_df,
        config=config,
        output_dir=output_dir,
        output_name=output_name,
    )


def run_analysis_for_dataframe(
    profile_df,
    config: AnalysisConfig,
    output_dir: str = "outputs",
    output_name: Optional[str] = None,
) -> AnalysisArtifacts:
    result = analyze_profile(profile_df, config)
    frames = build_report_frames(result)
    summary_cards = build_summary_cards(result)
    zone_summary = build_zone_summary_table(result)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    filename = output_name or f"heater_zoning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    export_path = export_analysis_excel(result, output_root / filename)
    return AnalysisArtifacts(
        result=result,
        frames=frames,
        summary_cards=summary_cards,
        zone_summary=zone_summary,
        export_path=export_path,
    )
