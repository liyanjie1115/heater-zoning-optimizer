from flask import Flask, render_template, request, send_from_directory, url_for

from src.heater_zoning import AnalysisConfig, sample_profile_dataframe
from src.heater_zoning.io_utils import read_profile_upload
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


def parse_config(form) -> AnalysisConfig:
    return AnalysisConfig(
        total_length=float(form.get("total_length", 500.0)),
        max_zones=int(form.get("max_zones", 8)),
        alpha=float(form.get("alpha", 5.0)),
        equal_zone_count=int(form.get("equal_zone_count", 8)),
        module_length=float(form.get("module_length", 23.0)),
        module_gap=float(form.get("module_gap", 10.0)),
        outer_edge_allow=float(form.get("outer_edge_allow", 10.0)),
        sample_left_ratio=float(form.get("sample_left_ratio", 0.30)),
        sample_mid_ratio=float(form.get("sample_mid_ratio", 0.50)),
        sample_right_ratio=float(form.get("sample_right_ratio", 0.70)),
        fit_weight=float(form.get("fit_weight", 0.32)),
        separation_weight=float(form.get("separation_weight", 0.22)),
        gradient_weight=float(form.get("gradient_weight", 0.24)),
        heater_weight=float(form.get("heater_weight", 0.12)),
        balance_weight=float(form.get("balance_weight", 0.10)),
        fit_decay=float(form.get("fit_decay", 850.0)),
        heater_decay=float(form.get("heater_decay", 16.0)),
        internal_violation_penalty=float(form.get("internal_violation_penalty", 0.18)),
        size_compliance_penalty=float(form.get("size_compliance_penalty", 0.08)),
    ).validate()


def dataframe_to_html(df, max_rows=12):
    preview = df.head(max_rows)
    return preview.to_html(classes="data-table", index=False, border=0, justify="center")


@app.route("/", methods=["GET", "POST"])
def index():
    context = {
        "error_message": None,
        "result_ready": False,
        "default_config": AnalysisConfig().to_dict(),
        "input_preview_html": dataframe_to_html(sample_profile_dataframe()),
        "active_source": "sample",
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
                    "metrics_table_html": dataframe_to_html(frames.metrics, max_rows=30),
                    "download_url": url_for("download_output", filename=artifacts.export_path.name),
                }
            )
        except Exception as exc:
            context.update(
                {
                    "error_message": str(exc),
                    "default_config": request.form.to_dict() or AnalysisConfig().to_dict(),
                    "active_source": request.form.get("data_source", "sample"),
                }
            )

    return render_template("index.html", **context)


@app.route("/outputs/<path:filename>")
def download_output(filename: str):
    return send_from_directory("outputs", filename, as_attachment=True, attachment_filename=filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
