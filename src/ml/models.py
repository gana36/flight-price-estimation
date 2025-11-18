"""
Ensemble model class definition.
Separated for consistent pickle serialization across modules.
"""

import numpy as np
from typing import Dict, Any
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb
import lightgbm as lgb
import logging

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
