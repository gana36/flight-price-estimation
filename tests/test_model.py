"""
Model validation tests.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path


@pytest.mark.skipif(
    not Path("models/latest.joblib").exists(),
    reason="Model file not found"
)
def test_model_exists():
    """Test that model file exists."""
    model_path = Path("models/latest.joblib")
    assert model_path.exists()
    assert model_path.stat().st_size > 0


@pytest.mark.skipif(
    not Path("models/latest.joblib").exists(),
    reason="Model file not found"
)
def test_model_loading():
    """Test model can be loaded."""
    import joblib

    model_path = "models/latest.joblib"
    model = joblib.load(model_path)
    assert model is not None


@pytest.mark.skipif(
    not Path("models/latest.joblib").exists() or not Path("data/processed/test.parquet").exists(),
    reason="Model or test data not found"
)
def test_model_predictions():
    """Test model can make predictions."""
    import joblib

    # Load model
    model = joblib.load("models/latest.joblib")

    # Load test data
    test_df = pd.read_parquet("data/processed/test.parquet")
    X_test = test_df.drop(columns=['price']).values[:10]  # First 10 samples

    # Make predictions
    predictions = model.predict(X_test)

    # Validate predictions
    assert len(predictions) == 10
    assert all(isinstance(p, (int, float, np.number)) for p in predictions)
    assert all(p > 0 for p in predictions)  # Prices should be positive
    assert all(not np.isnan(p) for p in predictions)  # No NaN values


@pytest.mark.skipif(
    not Path("models/latest.joblib").exists() or not Path("data/processed/test.parquet").exists(),
    reason="Model or test data not found"
)
def test_model_performance():
    """Test model meets performance thresholds."""
    import joblib
    import yaml
    from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

    # Load config
    with open("configs/base.yaml", 'r') as f:
        config = yaml.safe_load(f)

    thresholds = config['evaluation']['thresholds']

    # Load model
    model = joblib.load("models/latest.joblib")

    # Load test data
    test_df = pd.read_parquet("data/processed/test.parquet")
    X_test = test_df.drop(columns=['price']).values
    y_test = test_df['price'].values

    # Make predictions
    y_pred = model.predict(X_test)

    # Calculate metrics
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    mape = np.mean(np.abs((y_test - y_pred) / y_test))

    # Check thresholds
    assert r2 >= thresholds['min_r2'], f"R² {r2:.4f} below threshold {thresholds['min_r2']}"
    assert rmse <= thresholds['max_rmse'], f"RMSE {rmse:.2f} above threshold {thresholds['max_rmse']}"
    assert mape <= thresholds['max_mape'], f"MAPE {mape:.4f} above threshold {thresholds['max_mape']}"


def test_config_files_exist():
    """Test configuration files exist."""
    assert Path("configs/base.yaml").exists()
    assert Path("configs/training.yaml").exists()


def test_config_valid():
    """Test configuration files are valid YAML."""
    import yaml

    with open("configs/base.yaml", 'r') as f:
        base_config = yaml.safe_load(f)

    with open("configs/training.yaml", 'r') as f:
        training_config = yaml.safe_load(f)

    # Check required keys exist
    assert 'data' in base_config
    assert 'evaluation' in base_config
    assert 'mlflow' in base_config

    assert 'ensemble' in training_config
    assert 'models' in training_config
