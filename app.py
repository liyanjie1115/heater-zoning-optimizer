from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, send_from_directory, url_for

from src.heater_zoning import AnalysisConfig, analyze_profile, sample_profile_dataframe
from src.heater_zoning.analysis import metrics_dataframe, representative_points_dataframe, zones_dataframe
from src.heater_zoning.exporters import export_analysis_excel
from src.heater_zoning.io_utils import normalize_profile_dataframe, read_profile_upload
from src.heater_zoning.visualization import (
    build_metrics_bar_figure,
    build_metrics_radar_figure,
    build_module_layout_figure,
    build_temperature_comparison_figure,
    figure_to_html,
)


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024

OUTPUT_DIR = Path("outputs")


def parse_config(form) -> AnalysisConfig:
    return AnalysisConfig(
        total_length=float(form.get("total_length", 500.0)),
        max_zones=int(form.get("max_zones", 8)),
        alpha=float(form.get("alpha", 5.0)),
        equal_zone_count=int(form.get("equal_zone_count", 8)),
        module_length=float(form.get("module_length", 23.0)),
        module_gap=float(form.get("module_gap", 10.0)),
        outer_edge_allow=float(form.get("outer_edge_allow", 10.0)),
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
            else:
                profile_df = normalize_profile_dataframe(sample_profile_dataframe())

            result = analyze_profile(profile_df, config)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = OUTPUT_DIR / f"heater_zoning_report_{timestamp}.xlsx"
            export_analysis_excel(result, export_path)

            distance = result.profile_df["distance_mm"].to_numpy()
            temp = result.profile_df["temperature_c"].to_numpy()
            equal_df = zones_dataframe(result.equal_zones, "等距分区", distance, temp)
            aligned_df = zones_dataframe(result.aligned_zones, "模块对齐分区", distance, temp)
            equal_points_df = representative_points_dataframe(result.equal_zones, distance, temp, "等距分区")
            aligned_points_df = representative_points_dataframe(result.aligned_zones, distance, temp, "模块对齐分区")
            metrics_df = metrics_dataframe(result.equal_metrics, result.aligned_metrics)

            context.update(
                {
                    "result_ready": True,
                    "default_config": config.to_dict(),
                    "active_source": source,
                    "input_preview_html": dataframe_to_html(profile_df, max_rows=20),
                    "temperature_chart": figure_to_html(
                        build_temperature_comparison_figure(result.profile_df, result.equal_zones, result.aligned_zones)
                    ),
                    "layout_chart": figure_to_html(build_module_layout_figure(result.equal_zones, result.aligned_zones)),
                    "metrics_chart": figure_to_html(build_metrics_bar_figure(result.equal_metrics, result.aligned_metrics)),
                    "radar_chart": figure_to_html(build_metrics_radar_figure(result.equal_metrics, result.aligned_metrics)),
                    "equal_metrics": result.equal_metrics,
                    "aligned_metrics": result.aligned_metrics,
                    "equal_table_html": dataframe_to_html(equal_df, max_rows=20),
                    "aligned_table_html": dataframe_to_html(aligned_df, max_rows=20),
                    "equal_points_html": dataframe_to_html(equal_points_df, max_rows=20),
                    "aligned_points_html": dataframe_to_html(aligned_points_df, max_rows=20),
                    "metrics_table_html": dataframe_to_html(metrics_df, max_rows=30),
                    "download_url": url_for("download_output", filename=export_path.name),
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
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True, attachment_filename=filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

