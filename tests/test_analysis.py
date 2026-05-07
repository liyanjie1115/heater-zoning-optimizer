import unittest

from src.heater_zoning import AnalysisConfig, analyze_profile, sample_profile_dataframe


class AnalysisSmokeTest(unittest.TestCase):
    def test_sample_profile_analysis_runs(self):
        result = analyze_profile(sample_profile_dataframe(), AnalysisConfig())
        self.assertEqual(len(result.equal_zones), 8)
        self.assertGreaterEqual(len(result.aligned_zones), 1)
        self.assertLessEqual(len(result.aligned_zones), 8)
        self.assertGreater(result.equal_metrics.total_modules, 0)
        self.assertGreater(result.aligned_metrics.total_modules, 0)


if __name__ == "__main__":
    unittest.main()

