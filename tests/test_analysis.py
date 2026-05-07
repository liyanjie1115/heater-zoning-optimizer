import tempfile
import unittest
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from src.heater_zoning import AnalysisConfig, analyze_profile, sample_profile_dataframe
from src.heater_zoning.cli import main as cli_main
from src.heater_zoning.exporters import export_analysis_excel, export_summary_pdf
from src.heater_zoning.io_utils import normalize_profile_dataframe
from src.heater_zoning.runflow import run_analysis_pipeline
from src.heater_zoning.settings import AppSettings


class AnalysisSmokeTest(unittest.TestCase):
    def test_sample_profile_analysis_runs(self):
        result = analyze_profile(sample_profile_dataframe(), AnalysisConfig())
        self.assertEqual(len(result.equal_zones), 8)
        self.assertGreaterEqual(len(result.aligned_zones), 1)
        self.assertLessEqual(len(result.aligned_zones), 8)
        self.assertGreater(result.equal_metrics.total_modules, 0)
        self.assertGreater(result.aligned_metrics.total_modules, 0)

    def test_normalize_profile_dataframe_accepts_alias_columns(self):
        raw = pd.DataFrame(
            {
                "距离": [500.0, 0.0, 250.0, 250.0],
                "温度": [320.0, 650.0, 450.0, 451.0],
            }
        )
        normalized = normalize_profile_dataframe(raw)
        self.assertEqual(list(normalized.columns), ["distance_mm", "temperature_c"])
        self.assertEqual(normalized["distance_mm"].tolist(), [0.0, 250.0, 500.0])

    def test_export_analysis_excel_creates_expected_sheets(self):
        result = analyze_profile(sample_profile_dataframe(), AnalysisConfig())
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report.xlsx"
            export_analysis_excel(result, output_path)
            self.assertTrue(output_path.exists())
            workbook = load_workbook(output_path)
            self.assertEqual(
                workbook.sheetnames,
                ["原始数据", "等距分区结果", "模块对齐分区结果", "等距分区三点", "模块对齐分区三点", "评价指标"],
            )

    def test_cli_generates_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            exit_code = cli_main(["--output-dir", tmpdir, "--output-name", "cli_report.xlsx", "--json"])
            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(tmpdir) / "cli_report.xlsx").exists())

    def test_run_analysis_pipeline_uses_sample_source(self):
        artifacts = run_analysis_pipeline(config=AnalysisConfig(), source="sample")
        self.assertTrue(artifacts.export_path.exists())
        self.assertEqual(artifacts.summary_cards[0]["label"], "推荐方案")

    def test_export_summary_pdf_creates_file(self):
        result = analyze_profile(sample_profile_dataframe(), AnalysisConfig())
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "summary.pdf"
            export_summary_pdf(result, output_path)
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)

    def test_app_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"
            settings = AppSettings()
            settings.add_recent_file("D:/data/profile.csv")
            settings.save_template("default", AnalysisConfig())
            settings.save(settings_path)

            restored = AppSettings.load(settings_path)
            self.assertEqual(restored.recent_files[0], "D:/data/profile.csv")
            self.assertIn("default", restored.templates)
            self.assertEqual(restored.load_template("default").module_gap, 10.0)


if __name__ == "__main__":
    unittest.main()
