"""Tests for data processor"""

import unittest
from src.data_processor import DataProcessor


class TestDataProcessor(unittest.TestCase):
    """Test data processing functionality"""

    def setUp(self):
        self.processor = DataProcessor()

    def test_process_commits_empty(self):
        """Test processing empty commit list"""
        result = self.processor.process_commits([])
        self.assertEqual(result, {})

    def test_process_commits_aggregation(self):
        """Test commits are correctly aggregated by date"""
        commits = [
            {
                "date": "2026-01-01T10:00:00",
                "additions": 100,
                "deletions": 10,
                "repository": "repo1"
            },
            {
                "date": "2026-01-01T15:00:00",
                "additions": 50,
                "deletions": 5,
                "repository": "repo2"
            },
            {
                "date": "2026-01-02T10:00:00",
                "additions": 200,
                "deletions": 20,
                "repository": "repo1"
            }
        ]

        result = self.processor.process_commits(commits)

        self.assertEqual(len(result), 2)
        self.assertEqual(result["2026-01-01"]["additions"], 150)
        self.assertEqual(result["2026-01-01"]["deletions"], 15)
        self.assertEqual(result["2026-01-01"]["commits"], 2)
        self.assertEqual(result["2026-01-01"]["net_lines"], 135)

    def test_calculate_summary(self):
        """Test summary calculation"""
        daily_stats = {
            "2026-01-01": {
                "additions": 100,
                "deletions": 10,
                "commits": 2,
                "net_lines": 90,
                "repositories": ["repo1"]
            },
            "2026-01-02": {
                "additions": 50,
                "deletions": 5,
                "commits": 1,
                "net_lines": 45,
                "repositories": ["repo2"]
            }
        }

        summary = self.processor.calculate_summary(daily_stats)

        self.assertEqual(summary["total_additions"], 150)
        self.assertEqual(summary["total_deletions"], 15)
        self.assertEqual(summary["net_lines"], 135)
        self.assertEqual(summary["total_commits"], 3)
        self.assertEqual(summary["total_days"], 2)


if __name__ == "__main__":
    unittest.main()
