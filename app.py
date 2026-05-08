from html import escape

from flask import Flask, render_template, request, send_from_directory, url_for

from src.heater_zoning import AnalysisConfig, sample_profile_dataframe
from src.heater_zoning.io_utils import read_profile_upload
from src.heater_zoning.reporting import (
    build_config_snapshot,
    build_decision_overview,
    build_recommendation_summary,
)
from src.heater_zoning.runflow import run_analysis_for_dataframe, run_analysis_pipeline
from src.heater_zoning.visualization import (
    build_metrics_bar_figure,
    build_metrics_radar_figure,
    build_module_layout_figure,
    build_temperature_comparison_figure,
    figure_to_html,
)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


PRESET_CONFIGS = {
    "balanced": {"label": "平衡推荐", "overrides": {}},
    "precision": {
        "label": "追求贴合",
        "overrides": {"gradient_weight": 0.30, "fit_weight": 0.36, "heater_weight": 0.10, "balance_weight": 0.08},
    },
    "installation": {
        "label": "优先安装",
        "overrides": {"heater_weight": 0.22, "balance_weight": 0.14, "fit_weight": 0.24, "gradient_weight": 0.18},
    },
    "compact": {
        "label": "控制分区/模块复杂度",
        "overrides": {"max_zones": 6, "equal_zone_count": 6, "balance_weight": 0.16, "heater_weight": 0.16},
    },
}


def build_preset_options():
    return [{"value": key, "label": value["label"]} for key, value in PRESET_CONFIGS.items()]


def merge_config_with_preset(form) -> dict:
    preset_key = form.get("preset_key", "balanced")
    base = AnalysisConfig().to_dict()
    base.update(PRESET_CONFIGS.get(preset_key, PRESET_CONFIGS["balanced"])["overrides"])
    for key, value in form.items():
        if key == "preset_key":
            continue
        base[key] = value
    return base


def parse_config(form) -> AnalysisConfig:
    merged = merge_config_with_preset(form)
    return AnalysisConfig(
        total_length=float(merged.get("total_length", 500.0)),
        max_zones=int(merged.get("max_zones", 8)),
        alpha=float(merged.get("alpha", 5.0)),
        equal_zone_count=int(merged.get("equal_zone_count", 8)),
        module_length=float(merged.get("module_length", 23.0)),
        module_gap=float(merged.get("module_gap", 10.0)),
        outer_edge_allow=float(merged.get("outer_edge_allow", 10.0)),
        sample_left_ratio=float(merged.get("sample_left_ratio", 0.30)),
        sample_mid_ratio=float(merged.get("sample_mid_ratio", 0.50)),
        sample_right_ratio=float(merged.get("sample_right_ratio", 0.70)),
        fit_weight=float(merged.get("fit_weight", 0.32)),
        separation_weight=float(merged.get("separation_weight", 0.22)),
        gradient_weight=float(merged.get("gradient_weight", 0.24)),
        heater_weight=float(merged.get("heater_weight", 0.12)),
        balance_weight=float(merged.get("balance_weight", 0.10)),
        fit_decay=float(merged.get("fit_decay", 850.0)),
        heater_decay=float(merged.get("heater_decay", 16.0)),
        internal_violation_penalty=float(merged.get("internal_violation_penalty", 0.18)),
        size_compliance_penalty=float(merged.get("size_compliance_penalty", 0.08)),
    ).validate()


def format_cell_value(value) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return escape(str(value))


def format_percent(value: float) -> str:
    return f"{value * 100:+.2f}%"


def _badge(label: str, variant: str) -> str:
    return f'<span class="badge badge-{variant}">{escape(label)}</span>'


def metrics_dataframe_to_html(df) -> str:
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in df.columns)
    rows_html = []
    for _, row in df.iterrows():
        better = row["更优方案"]
        row_class = "row-equal" if better == "等距分区" else "row-aligned" if better == "模块对齐分区" else ""

        direction = row["指标方向"]
        if direction == "越大越好":
            direction_html = _badge(direction, "up")
        elif direction == "越小越好":
            direction_html = _badge(direction, "down")
        else:
            direction_html = _badge(direction, "neutral")

        included_html = _badge(row["纳入综合得分"], "score" if row["纳入综合得分"] == "是" else "muted")
        better_html = _badge(
            better,
            {
                "等距分区": "equal",
                "模块对齐分区": "aligned",
                "持平": "neutral",
                "按项目判断": "muted",
            }.get(better, "neutral"),
        )

        rows_html.append(
            "".join(
                [
                    f'<tr class="{row_class}">',
                    f"<td>{escape(str(row['指标']))}</td>",
                    f"<td>{direction_html}</td>",
                    f"<td>{included_html}</td>",
                    f"<td>{better_html}</td>",
                    f'<td class="{"value-better" if better == "等距分区" else ""}">{format_cell_value(row["等距分区"])}</td>',
                    f'<td class="{"value-better" if better == "模块对齐分区" else ""}">{format_cell_value(row["模块对齐分区"])}</td>',
                    f'<td class="metric-desc">{escape(str(row["指标说明"]))}</td>',
                    "</tr>",
                ]
            )
        )
    return f'<table class="data-table metrics-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows_html)}</tbody></table>'


def difference_dataframe_to_html(df) -> str:
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in df.columns)
    rows_html = []
    for _, row in df.iterrows():
        better = row["更优方案"]
        row_class = "row-equal" if better == "等距分区" else "row-aligned" if better == "模块对齐分区" else ""
        rel = float(row["相对变化"])
        trend_variant = "good" if rel > 0.001 else "bad" if rel < -0.001 else "neutral"
        trend_symbol = "▲" if rel > 0.001 else "▼" if rel < -0.001 else "■"
        trend_html = f'<span class="trend trend-{trend_variant}">{trend_symbol} {format_percent(rel)}</span>'

        rows_html.append(
            "".join(
                [
                    f'<tr class="{row_class}">',
                    f"<td>{escape(str(row['指标']))}</td>",
                    f"<td>{escape(str(row['指标方向']))}</td>",
                    f"<td>{format_cell_value(row['等距分区'])}</td>",
                    f"<td>{format_cell_value(row['模块对齐分区'])}</td>",
                    f"<td>{format_cell_value(row['绝对差值(模块对齐-等距)'])}</td>",
                    f"<td>{trend_html}</td>",
                    f"<td>{_badge(better, {'等距分区': 'equal', '模块对齐分区': 'aligned', '持平': 'neutral', '按项目判断': 'muted'}.get(better, 'neutral'))}</td>",
                    "</tr>",
                ]
            )
        )
    return f'<table class="data-table difference-table"><thead><tr>{headers}</tr></thead><tbody>{"".join(rows_html)}</tbody></table>'


def dataframe_to_html(df, max_rows=12, table_kind="default"):
    preview = df.head(max_rows).copy()
    if table_kind == "metrics":
        return metrics_dataframe_to_html(preview)
    if table_kind == "differences":
        return difference_dataframe_to_html(preview)
    return preview.to_html(classes="data-table", index=False, border=0, justify="center")


@app.route("/", methods=["GET", "POST"])
def index():
    context = {
        "error_message": None,
        "result_ready": False,
        "default_config": AnalysisConfig().to_dict(),
        "input_preview_html": dataframe_to_html(sample_profile_dataframe()),
        "active_source": "sample",
        "active_preset": "balanced",
        "preset_options": build_preset_options(),
        "summary_cards": [],
        "recommendation": None,
        "decision_overview": [],
        "config_snapshot": [],
        "difference_table_html": "",
    }

    if request.method == "POST":
        try:
            config = parse_config(request.form)
            source = request.form.get("data_source", "sample")
            if source == "upload":
                upload = request.files.get("profile_file")
                if not upload or not upload.filename:
                    raise ValueError("请上传 CSV 或 Excel 数据文件。")
                profile_df = read_profile_upload(upload)
                artifacts = run_analysis_for_dataframe(profile_df=profile_df, config=config)
            else:
                artifacts = run_analysis_pipeline(config=config, source="sample")

            result = artifacts.result
            frames = artifacts.frames

            context.update(
                {
                    "result_ready": True,
                    "default_config": config.to_dict(),
                    "active_source": source,
                    "active_preset": request.form.get("preset_key", "balanced"),
                    "summary_cards": artifacts.summary_cards,
                    "recommendation": build_recommendation_summary(result),
                    "decision_overview": build_decision_overview(result),
                    "config_snapshot": build_config_snapshot(result),
                    "input_preview_html": dataframe_to_html(result.profile_df, max_rows=20),
                    "temperature_chart": figure_to_html(
                        build_temperature_comparison_figure(result.profile_df, result.equal_zones, result.aligned_zones)
                    ),
                    "layout_chart": figure_to_html(build_module_layout_figure(result.equal_zones, result.aligned_zones)),
                    "metrics_chart": figure_to_html(build_metrics_bar_figure(result.equal_metrics, result.aligned_metrics)),
                    "radar_chart": figure_to_html(build_metrics_radar_figure(result.equal_metrics, result.aligned_metrics)),
                    "equal_metrics": result.equal_metrics,
                    "aligned_metrics": result.aligned_metrics,
                    "equal_table_html": dataframe_to_html(frames.equal_zones, max_rows=20),
                    "aligned_table_html": dataframe_to_html(frames.aligned_zones, max_rows=20),
                    "equal_points_html": dataframe_to_html(frames.equal_points, max_rows=20),
                    "aligned_points_html": dataframe_to_html(frames.aligned_points, max_rows=20),
                    "metrics_table_html": dataframe_to_html(frames.metrics, max_rows=30, table_kind="metrics"),
                    "difference_table_html": dataframe_to_html(frames.differences, max_rows=30, table_kind="differences"),
                    "download_url": url_for("download_output", filename=artifacts.export_path.name),
                }
            )
        except Exception as exc:
            context.update(
                {
                    "error_message": str(exc),
                    "default_config": merge_config_with_preset(request.form) if request.form else AnalysisConfig().to_dict(),
                    "active_source": request.form.get("data_source", "sample"),
                    "active_preset": request.form.get("preset_key", "balanced"),
                }
            )

    return render_template("index.html", **context)


@app.route("/outputs/<path:filename>")
def download_output(filename: str):
    return send_from_directory("outputs", filename, as_attachment=True, attachment_filename=filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
