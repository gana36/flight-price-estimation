"""
Model evaluation module.
Comprehensive evaluation of ensemble model performance.
"""

import joblib
import pandas as pd
import numpy as np
import yaml
import mlflow
from pathlib import Path
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error
)
import matplotlib.pyplot as plt
import seaborn as sns
import logging

# Import EnsembleModel class so joblib can deserialize the model
from src.ml.models import EnsembleModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_test_data():
    """Load test dataset."""
    test_df = pd.read_parquet("data/processed/test.parquet")
    X_test = test_df.drop(columns=['price']).values
    y_test = test_df['price'].values
    return X_test, y_test


def evaluate():
    """Main evaluation function."""
    logger.info("Starting model evaluation...")

    # Load model
    model_path = "models/latest.joblib"
    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model not found at {model_path}. Train model first.")

    model = joblib.load(model_path)
    logger.info(f"Model loaded from {model_path}")

    # Load test data
    X_test, y_test = load_test_data()
    logger.info(f"Test data loaded: {X_test.shape}")

    # Make predictions
    y_pred = model.predict(X_test)

    # Calculate metrics
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    mape = np.mean(np.abs((y_test - y_pred) / y_test)) * 100

    metrics = {
        'mae': mae,
        'rmse': rmse,
        'r2_score': r2,
        'mape': mape
    }

    logger.info("Evaluation Results:")
    logger.info(f"  MAE: ${mae:.2f}")
    logger.info(f"  RMSE: ${rmse:.2f}")
    logger.info(f"  R² Score: {r2:.4f}")
    logger.info(f"  MAPE: {mape:.2f}%")

    # Check thresholds from config
    with open("configs/base.yaml", 'r') as f:
        config = yaml.safe_load(f)

    thresholds = config['evaluation']['thresholds']
    passed = True

    if r2 < thresholds['min_r2']:
        logger.warning(f"R² score {r2:.4f} below threshold {thresholds['min_r2']}")
        passed = False

    if rmse > thresholds['max_rmse']:
        logger.warning(f"RMSE {rmse:.2f} above threshold {thresholds['max_rmse']}")
        passed = False

    if mape > thresholds['max_mape']:
        logger.warning(f"MAPE {mape:.2f}% above threshold {thresholds['max_mape']*100}%")
        passed = False

    if passed:
        logger.info("✓ Model passes all evaluation thresholds")
    else:
        logger.warning("✗ Model does not meet all thresholds")

    # Generate evaluation report
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Save metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(reports_dir / "evaluation_metrics.csv", index=False)

    # Save predictions for analysis
    results_df = pd.DataFrame({
        'actual': y_test,
        'predicted': y_pred,
        'error': y_test - y_pred,
        'abs_error': np.abs(y_test - y_pred),
        'pct_error': np.abs((y_test - y_pred) / y_test) * 100
    })
    results_df.to_csv(reports_dir / "predictions.csv", index=False)

    logger.info(f"Evaluation complete. Reports saved to {reports_dir}/")

    return metrics, passed


if __name__ == "__main__":
    metrics, passed = evaluate()
