"""Data preparation for Flight Price Prediction."""

import os
import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, LabelEncoder
from typing import Tuple, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FlightDataProcessor:
    def __init__(self, config_path: str = "configs/base.yaml"):
        self.config = self._load_config(config_path)
        self.scaler = None
        self.feature_names = None
        self.label_encoders = {}  # Store encoders for each categorical column

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def load_data(self, data_path: str) -> pd.DataFrame:
        logger.info(f"Loading data from {data_path}")

        if data_path.endswith('.csv'):
            df = pd.read_csv(data_path)
        elif data_path.endswith('.parquet'):
            df = pd.read_parquet(data_path)
        else:
            raise ValueError(f"Unsupported file format: {data_path}")

        # Drop unnecessary columns
        if 'Unnamed: 0' in df.columns:
            df = df.drop(columns=['Unnamed: 0'])
            logger.info("Dropped column: Unnamed: 0")

        logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Engineering features...")

        df = df.copy()

        # Convert duration to hours if it's a string (e.g., "2h 30m")
        if 'duration' in df.columns and df['duration'].dtype == object:
            df['duration_hours'] = df['duration'].apply(self._parse_duration)

        # Price per hour (if duration is available)
        if 'duration_hours' in df.columns and 'price' in df.columns:
            df['price_per_hour'] = df['price'] / (df['duration_hours'] + 1)  # +1 to avoid division by zero

        # Days left binning (booking urgency) - use numeric encoding directly
        if 'days_left' in df.columns:
            df['booking_urgency'] = pd.cut(
                df['days_left'],
                bins=[0, 7, 14, 30, 60, float('inf')],
                labels=[4, 3, 2, 1, 0]  # Higher number = more urgent
            ).astype(float).fillna(0).astype(int)

        # Is weekend departure
        if 'departure_time' in df.columns:
            # Assuming departure_time categories include day info or can be mapped
            weekend_times = ['Late_Night']  # Customize based on your data
            df['is_weekend'] = df['departure_time'].isin(weekend_times).astype(int)

        logger.info(f"Feature engineering complete. Total features: {len(df.columns)}")
        return df

    def _parse_duration(self, duration_str: str) -> float:
        if pd.isna(duration_str):
            return 0.0

        try:
            hours = 0.0
            if 'h' in str(duration_str):
                parts = str(duration_str).replace('m', '').split('h')
                hours = float(parts[0])
                if len(parts) > 1 and parts[1].strip():
                    hours += float(parts[1].strip()) / 60
            return hours
        except:
            return 0.0

    def preprocess(self, df: pd.DataFrame, fit: bool = True) -> Tuple[np.ndarray, pd.DataFrame]:
        """Handle missing values, encode categoricals, scale numericals."""
        logger.info("Preprocessing data...")

        df = df.copy()

        # Separate target if present
        target = None
        if self.config['data']['target'] in df.columns:
            target = df[self.config['data']['target']]
            df = df.drop(columns=[self.config['data']['target']])

        # Handle missing values for numerical features
        numerical_features = self.config['data']['features']['numerical']
        for col in numerical_features:
            if col in df.columns:
                df[col] = df[col].fillna(df[col].median())

        # Use LabelEncoder for ALL object/categorical columns (like the notebook)
        for col in df.columns:
            if df[col].dtype == 'object':
                if fit:
                    le = LabelEncoder()
                    df[col] = le.fit_transform(df[col].astype(str))
                    self.label_encoders[col] = le
                    logger.info(f"Label encoded column: {col}")
                else:
                    if col in self.label_encoders:
                        # Handle unseen labels by mapping to -1
                        le = self.label_encoders[col]
                        df[col] = df[col].astype(str).apply(
                            lambda x: le.transform([x])[0] if x in le.classes_ else -1
                        )
                    else:
                        logger.warning(f"No encoder found for column {col}, using 0")
                        df[col] = 0

        # Store feature names for consistency
        if fit:
            self.feature_names = df.columns.tolist()
        else:
            # Ensure same features as training
            missing_cols = set(self.feature_names) - set(df.columns)
            for col in missing_cols:
                df[col] = 0
            df = df[self.feature_names]

        # Scale numerical features
        if self.config['preprocessing']['scale_numerical']:
            scaler_type = self.config['preprocessing']['scaler']

            if fit:
                if scaler_type == 'standard':
                    self.scaler = StandardScaler()
                elif scaler_type == 'minmax':
                    self.scaler = MinMaxScaler()
                elif scaler_type == 'robust':
                    self.scaler = RobustScaler()

                features = self.scaler.fit_transform(df)
            else:
                if self.scaler is None:
                    raise ValueError("Scaler not fitted. Call with fit=True first.")
                features = self.scaler.transform(df)
        else:
            features = df.values

        logger.info(f"Preprocessing complete. Feature shape: {features.shape}")
        return features, target

    def split_data(self, features: np.ndarray, target: pd.Series) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        test_size = self.config['data']['test_size']
        random_state = self.config['data']['random_state']

        logger.info(f"Splitting data with test_size={test_size}")

        X_train, X_test, y_train, y_test = train_test_split(
            features,
            target,
            test_size=test_size,
            random_state=random_state,
            shuffle=self.config['training']['shuffle']
        )

        logger.info(f"Train set: {X_train.shape}, Test set: {X_test.shape}")
        return X_train, X_test, y_train, y_test


def prepare_datasets():
    logger.info("Starting data preparation...")

    # Initialize processor
    processor = FlightDataProcessor()

    # Load raw data
    data_path = "Clean_Dataset.csv"  # Update based on your data
    df = processor.load_data(data_path)

    # Engineer features
    df = processor.engineer_features(df)

    # Preprocess
    features, target = processor.preprocess(df, fit=True)

    # Split data
    X_train, X_test, y_train, y_test = processor.split_data(features, target)

    # Save processed data
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use feature names from processor to preserve column names
    train_df = pd.DataFrame(X_train, columns=processor.feature_names)
    train_df['price'] = y_train.values
    train_df.to_parquet(output_dir / "train.parquet", index=False)

    test_df = pd.DataFrame(X_test, columns=processor.feature_names)
    test_df['price'] = y_test.values
    test_df.to_parquet(output_dir / "test.parquet", index=False)

    # Save reference data for drift detection (sample from train)
    reference_df = train_df.sample(n=min(1000, len(train_df)), random_state=42)
    reference_df.to_parquet(output_dir / "reference.parquet", index=False)

    # Save current data placeholder (will be updated in production)
    current_df = test_df.sample(n=min(100, len(test_df)), random_state=42)
    current_df.to_parquet(output_dir / "current.parquet", index=False)

    logger.info("Data preparation complete!")
    logger.info(f"Train: {len(train_df)}, Test: {len(test_df)}")
    logger.info(f"Reference: {len(reference_df)}, Current: {len(current_df)}")


if __name__ == "__main__":
    prepare_datasets()
