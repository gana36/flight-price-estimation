"""
Data drift detection using Evidently.
Monitors prediction data for distribution shifts and data quality issues.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DriftDetector:
    """Monitor data drift using Evidently."""

    def __init__(self, reference_data_path: str = "data/processed/reference.parquet"):
        """
        Initialize drift detector.

        Args:
            reference_data_path: Path to reference dataset
        """
        self.reference_data = pd.read_parquet(reference_data_path)
        logger.info(f"Loaded reference data: {len(self.reference_data)} records")

    def detect_drift(
        self,
        current_data: pd.DataFrame,
        report_path: str = None
    ) -> Dict[str, Any]:
        """
        Detect drift between reference and current data.

        Args:
            current_data: Current production data
            report_path: Path to save HTML report

        Returns:
            Drift detection results
        """
        logger.info(f"Detecting drift on {len(current_data)} current records...")

        # Create Evidently report
        report = Report(metrics=[
            DataDriftPreset(),
            DataQualityPreset()
        ])

        # Run report
        report.run(
            reference_data=self.reference_data,
            current_data=current_data
        )

        # Save HTML report
        if report_path is None:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = reports_dir / f"drift_report_{timestamp}.html"

        report.save_html(str(report_path))
        logger.info(f"Drift report saved to {report_path}")

        # Extract key metrics
        # Note: Evidently API may vary by version
        results = {
            "report_path": str(report_path),
            "timestamp": datetime.now().isoformat(),
            "n_reference": len(self.reference_data),
            "n_current": len(current_data)
        }

        return results


def monitor_production_drift(hours: int = 24):
    """
    Monitor drift in production predictions.

    Args:
        hours: Number of hours of recent data to analyze
    """
    from src.database.models import get_session, Prediction

    logger.info(f"Monitoring drift for last {hours} hours...")

    # Get recent predictions from database
    session = get_session()
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    predictions = session.query(Prediction).filter(
        Prediction.timestamp >= cutoff_time
    ).all()

    if len(predictions) < 100:
        logger.warning(f"Only {len(predictions)} predictions found. Need at least 100 for drift detection.")
        return

    # Convert to DataFrame
    current_data = pd.DataFrame([
        {**p.features, 'price': p.predicted_price}
        for p in predictions
    ])

    # Run drift detection
    detector = DriftDetector()
    results = detector.detect_drift(current_data)

    logger.info(f"Drift detection complete: {results}")

    session.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Monitor production data drift')
    parser.add_argument('--hours', type=int, default=24, help='Hours of data to analyze')
    args = parser.parse_args()

    monitor_production_drift(hours=args.hours)
