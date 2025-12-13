"""Data drift detection using Evidently."""

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
    def __init__(self, reference_data_path: str = "data/processed/reference.parquet"):
        self.reference_data = pd.read_parquet(reference_data_path)
        logger.info(f"Loaded reference data: {len(self.reference_data)} records")

    def detect_drift(self, current_data: pd.DataFrame, report_path: str = None) -> Dict[str, Any]:
        """Compare current data against reference and generate drift report."""
        logger.info(f"Detecting drift on {len(current_data)} current records...")

        # Find common columns between reference and current data
        reference_cols = set(self.reference_data.columns)
        current_cols = set(current_data.columns)
        common_cols = list(reference_cols.intersection(current_cols))
        
        if not common_cols:
            raise ValueError("No common columns between reference and current data")
        
        # Filter to common columns only
        reference_aligned = self.reference_data[common_cols].copy()
        current_aligned = current_data[common_cols].copy()
        
        logger.info(f"Comparing {len(common_cols)} common columns: {common_cols}")
        
        # Ensure consistent dtypes
        for col in common_cols:
            if reference_aligned[col].dtype != current_aligned[col].dtype:
                logger.warning(f"Column {col}: converting types to match")
                try:
                    current_aligned[col] = current_aligned[col].astype(reference_aligned[col].dtype)
                except (ValueError, TypeError):
                    # If conversion fails, convert both to string
                    reference_aligned[col] = reference_aligned[col].astype(str)
                    current_aligned[col] = current_aligned[col].astype(str)

        # Create Evidently report
        report = Report(metrics=[
            DataDriftPreset(),
            DataQualityPreset()
        ])

        # Run report
        report.run(
            reference_data=reference_aligned,
            current_data=current_aligned
        )

        # Save HTML report
        if report_path is None:
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = reports_dir / f"drift_report_{timestamp}.html"

        report.save_html(str(report_path))
        logger.info(f"Drift report saved to {report_path}")

        results = {
            "report_path": str(report_path),
            "timestamp": datetime.now().isoformat(),
            "n_reference": len(self.reference_data),
            "n_current": len(current_data)
        }

        return results


def monitor_production_drift(hours: int = 24):
    """Check drift on recent predictions from database."""
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
