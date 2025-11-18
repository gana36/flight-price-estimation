"""
Ensemble model training module with MLflow integration.
Trains Random Forest, XGBoost, and LightGBM models and combines them.
"""

import os
import yaml
import mlflow
import mlflow.sklearn
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import lightgbm as lgb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnsembleModel:
    """Ensemble model combining Random Forest, XGBoost, and LightGBM."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize ensemble model.

        Args:
            config: Configuration dictionary with model hyperparameters
        """
        self.config = config
        self.models = {}
        self.weights = config['ensemble']['weights']

    def build_models(self):
        """Build individual models based on configuration."""
        logger.info("Building ensemble models...")

        # Random Forest
        rf_params = self.config['models']['random_forest']
        self.models['random_forest'] = RandomForestRegressor(**rf_params)
        logger.info(f"Random Forest configured with {rf_params['n_estimators']} estimators")

        # XGBoost
        xgb_params = self.config['models']['xgboost']
        self.models['xgboost'] = xgb.XGBRegressor(**xgb_params)
        logger.info(f"XGBoost configured with {xgb_params['n_estimators']} estimators")

        # LightGBM
        lgb_params = self.config['models']['lightgbm']
        self.models['lightgbm'] = lgb.LGBMRegressor(**lgb_params)
        logger.info(f"LightGBM configured with {lgb_params['n_estimators']} estimators")

    def train(self, X_train: np.ndarray, y_train: np.ndarray):
        """
        Train all models in the ensemble.

        Args:
            X_train: Training features
            y_train: Training target
        """
        logger.info(f"Training ensemble on {X_train.shape[0]} samples...")

        for name, model in self.models.items():
            logger.info(f"Training {name}...")
            model.fit(X_train, y_train)
            logger.info(f"{name} training complete")

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions using weighted ensemble.

        Args:
            X: Features for prediction

        Returns:
            Ensemble predictions
        """
        predictions = {}

        for name, model in self.models.items():
            predictions[name] = model.predict(X)

        # Weighted average
        ensemble_pred = np.zeros_like(predictions['random_forest'])
        for name, pred in predictions.items():
            weight = self.weights[name]
            ensemble_pred += weight * pred

        return ensemble_pred

    def get_feature_importance(self) -> Dict[str, np.ndarray]:
        """Get feature importance from each model."""
        importance = {}

        if hasattr(self.models['random_forest'], 'feature_importances_'):
            importance['random_forest'] = self.models['random_forest'].feature_importances_

        if hasattr(self.models['xgboost'], 'feature_importances_'):
            importance['xgboost'] = self.models['xgboost'].feature_importances_

        if hasattr(self.models['lightgbm'], 'feature_importances_'):
            importance['lightgbm'] = self.models['lightgbm'].feature_importances_

        return importance


def load_config(config_path: str = "configs/training.yaml") -> Dict[str, Any]:
    """Load training configuration."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_data() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load preprocessed training and test data."""
    logger.info("Loading preprocessed data...")

    train_df = pd.read_parquet("data/processed/train.parquet")
    test_df = pd.read_parquet("data/processed/test.parquet")

    X_train = train_df.drop(columns=['price']).values
    y_train = train_df['price'].values

    X_test = test_df.drop(columns=['price']).values
    y_test = test_df['price'].values

    logger.info(f"Train: {X_train.shape}, Test: {X_test.shape}")
    return X_train, y_train, X_test, y_test


def evaluate_model(
    model: EnsembleModel,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Dict[str, float]:
    """
    Evaluate model performance.

    Args:
        model: Trained ensemble model
        X_test: Test features
        y_test: Test target

    Returns:
        Dictionary of evaluation metrics
    """
    logger.info("Evaluating model...")

    y_pred = model.predict(X_test)

    metrics = {
        'mae': mean_absolute_error(y_test, y_pred),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
        'r2_score': r2_score(y_test, y_pred),
        'mape': np.mean(np.abs((y_test - y_pred) / y_test)) * 100
    }

    logger.info("Evaluation metrics:")
    for metric_name, value in metrics.items():
        logger.info(f"  {metric_name}: {value:.4f}")

    return metrics


def train_model():
    """Main training function with MLflow tracking."""
    logger.info("Starting model training pipeline...")

    # Load configurations
    config = load_config()
    base_config_path = "configs/base.yaml"
    with open(base_config_path, 'r') as f:
        base_config = yaml.safe_load(f)

    # Set up MLflow
    mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(mlflow_uri)

    experiment_name = base_config['mlflow']['experiment_name']
    mlflow.set_experiment(experiment_name)

    # Load data
    X_train, y_train, X_test, y_test = load_data()

    # Start MLflow run
    with mlflow.start_run():
        # Log parameters
        mlflow.log_params({
            'ensemble_strategy': config['ensemble']['strategy'],
            'rf_n_estimators': config['models']['random_forest']['n_estimators'],
            'xgb_n_estimators': config['models']['xgboost']['n_estimators'],
            'lgb_n_estimators': config['models']['lightgbm']['n_estimators'],
            'rf_max_depth': config['models']['random_forest']['max_depth'],
            'xgb_max_depth': config['models']['xgboost']['max_depth'],
            'lgb_max_depth': config['models']['lightgbm']['max_depth'],
            'xgb_learning_rate': config['models']['xgboost']['learning_rate'],
            'lgb_learning_rate': config['models']['lightgbm']['learning_rate'],
        })

        mlflow.log_params(config['ensemble']['weights'])

        # Build and train model
        model = EnsembleModel(config)
        model.build_models()
        model.train(X_train, y_train)

        # Evaluate model
        metrics = evaluate_model(model, X_test, y_test)

        # Log metrics
        mlflow.log_metrics(metrics)

        # Log individual model predictions for analysis
        for name, individual_model in model.models.items():
            y_pred_individual = individual_model.predict(X_test)
            individual_metrics = {
                f'{name}_mae': mean_absolute_error(y_test, y_pred_individual),
                f'{name}_rmse': np.sqrt(mean_squared_error(y_test, y_pred_individual)),
                f'{name}_r2': r2_score(y_test, y_pred_individual),
            }
            mlflow.log_metrics(individual_metrics)

        # Save model locally
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        model_path = models_dir / "latest.joblib"
        joblib.dump(model, model_path)
        logger.info(f"Model saved to {model_path}")

        # Log model to MLflow
        mlflow.sklearn.log_model(
            model,
            "model",
            registered_model_name=base_config['mlflow']['registered_model_name']
        )

        # Log feature importance
        feature_importance = model.get_feature_importance()
        for model_name, importance in feature_importance.items():
            importance_df = pd.DataFrame({
                'feature_index': range(len(importance)),
                'importance': importance
            })
            importance_path = f"feature_importance_{model_name}.csv"
            importance_df.to_csv(importance_path, index=False)
            mlflow.log_artifact(importance_path)
            os.remove(importance_path)

        # Log configuration files
        mlflow.log_artifact("configs/base.yaml")
        mlflow.log_artifact("configs/training.yaml")

        logger.info(f"MLflow run completed. Run ID: {mlflow.active_run().info.run_id}")
        logger.info(f"Model registered as: {base_config['mlflow']['registered_model_name']}")

    return model, metrics


if __name__ == "__main__":
    model, metrics = train_model()
    logger.info("Training pipeline complete!")
