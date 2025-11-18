"""
Validate model before promotion to production.
Checks performance thresholds and data compatibility.
"""

import os
import sys
import argparse
import yaml
import mlflow
from mlflow import MlflowClient
import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "configs/base.yaml"):
    """Load evaluation thresholds from config."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def validate_model(
    model_name: str,
    version: str,
    auto_promote: bool = False
):
    """
    Validate model version against thresholds.

    Args:
        model_name: Name of registered model
        version: Model version to validate
        auto_promote: Automatically promote if validation passes

    Returns:
        bool: True if validation passes
    """
    logger.info(f"Validating model {model_name} version {version}")

    # Load config
    config = load_config()
    thresholds = config['evaluation']['thresholds']

    # Set MLflow tracking URI
    mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(mlflow_uri)

    client = MlflowClient()

    try:
        # Get model version
        model_version = client.get_model_version(model_name, version)
        run_id = model_version.run_id

        logger.info(f"Validating run {run_id}")

        # Get run metrics
        run = client.get_run(run_id)
        metrics = run.data.metrics

        logger.info("Model metrics:")
        for key, value in metrics.items():
            logger.info(f"  {key}: {value}")

        # Validate thresholds
        passed = True
        validation_results = {}

        # Check R² score
        if 'r2_score' in metrics:
            r2 = metrics['r2_score']
            threshold = thresholds['min_r2']
            r2_passed = r2 >= threshold
            validation_results['r2_score'] = {
                'value': r2,
                'threshold': threshold,
                'passed': r2_passed
            }
            if not r2_passed:
                logger.warning(f"✗ R² score {r2:.4f} below threshold {threshold}")
                passed = False
            else:
                logger.info(f"✓ R² score {r2:.4f} meets threshold {threshold}")

        # Check RMSE
        if 'rmse' in metrics:
            rmse = metrics['rmse']
            threshold = thresholds['max_rmse']
            rmse_passed = rmse <= threshold
            validation_results['rmse'] = {
                'value': rmse,
                'threshold': threshold,
                'passed': rmse_passed
            }
            if not rmse_passed:
                logger.warning(f"✗ RMSE {rmse:.2f} above threshold {threshold}")
                passed = False
            else:
                logger.info(f"✓ RMSE {rmse:.2f} meets threshold {threshold}")

        # Check MAPE
        if 'mape' in metrics:
            mape = metrics['mape']
            threshold = thresholds['max_mape']
            mape_passed = mape <= threshold
            validation_results['mape'] = {
                'value': mape,
                'threshold': threshold,
                'passed': mape_passed
            }
            if not mape_passed:
                logger.warning(f"✗ MAPE {mape:.2f}% above threshold {threshold*100}%")
                passed = False
            else:
                logger.info(f"✓ MAPE {mape:.2f}% meets threshold {threshold*100}%")

        # Overall result
        if passed:
            logger.info(f"✓ Model version {version} passes all validation checks")

            if auto_promote:
                logger.info("Auto-promoting model to production...")
                from promote_model import promote_model
                promote_model(model_name, version, alias='production')

        else:
            logger.error(f"✗ Model version {version} failed validation")

        return passed

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Validate model before promotion')
    parser.add_argument(
        '--model-name',
        type=str,
        default='FlightPricePredictor',
        help='Name of the registered model'
    )
    parser.add_argument(
        '--version',
        type=str,
        required=True,
        help='Model version to validate'
    )
    parser.add_argument(
        '--auto-promote',
        action='store_true',
        help='Automatically promote if validation passes'
    )

    args = parser.parse_args()

    passed = validate_model(
        model_name=args.model_name,
        version=args.version,
        auto_promote=args.auto_promote
    )

    sys.exit(0 if passed else 1)
