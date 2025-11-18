"""
FastAPI application for Flight Price Prediction.
Provides REST API endpoints for predictions, monitoring, and model management.
"""

import os
import sys
import time
import joblib
import mlflow
import mlflow.sklearn
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.app.metrics import (
    REQUEST_COUNT,
    REQUEST_LATENCY,
    PREDICTION_COUNT,
    MODEL_INFO,
    PREDICTION_VALUE,
    PREDICTION_LATENCY
)
from src.database.models import Prediction, get_session

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=os.getenv('API_TITLE', 'Flight Price Prediction API'),
    version=os.getenv('API_VERSION', '1.0.0'),
    description=os.getenv('API_DESCRIPTION', 'MLOps API for flight price prediction')
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model variable
current_model = None
current_model_info = {}


class FlightFeatures(BaseModel):
    """Input features for flight price prediction."""

    airline: str = Field(..., description="Airline name")
    source_city: str = Field(..., description="Source city")
    destination_city: str = Field(..., description="Destination city")
    departure_time: str = Field(..., description="Departure time category")
    arrival_time: str = Field(..., description="Arrival time category")
    stops: str = Field(..., description="Number of stops")
    flight_class: str = Field(..., description="Flight class (economy/business)", alias="class")
    duration: float = Field(..., description="Flight duration in hours")
    days_left: int = Field(..., description="Days until departure")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "airline": "SpiceJet",
                "source_city": "Delhi",
                "destination_city": "Mumbai",
                "departure_time": "Evening",
                "arrival_time": "Night",
                "stops": "zero",
                "class": "Economy",
                "duration": 2.17,
                "days_left": 1
            }
        }


class PredictionResponse(BaseModel):
    """Response model for predictions."""

    predicted_price: float
    model_name: str
    model_version: str
    prediction_timestamp: str
    latency_ms: float


class ModelInfoResponse(BaseModel):
    """Response model for model information."""

    model_name: str
    model_version: Optional[str]
    model_alias: Optional[str]
    loaded_at: str
    model_type: str


def load_model_from_mlflow(alias: str = None, version: str = None):
    """
    Load model from MLflow registry.

    Args:
        alias: Model alias (e.g., 'production', 'staging')
        version: Specific model version

    Returns:
        Loaded model and metadata
    """
    mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(mlflow_uri)

    model_name = os.getenv('MLFLOW_REGISTERED_MODEL_NAME', 'FlightPricePredictor')

    try:
        if alias:
            # Load by alias (modern approach)
            model_uri = f"models:/{model_name}@{alias}"
            logger.info(f"Loading model from MLflow: {model_uri}")
            model = mlflow.sklearn.load_model(model_uri)

            # Get version info from alias
            client = mlflow.MlflowClient()
            model_version = client.get_model_version_by_alias(model_name, alias)
            version_number = model_version.version

        elif version:
            # Load specific version
            model_uri = f"models:/{model_name}/{version}"
            logger.info(f"Loading model from MLflow: {model_uri}")
            model = mlflow.sklearn.load_model(model_uri)
            version_number = version

        else:
            # Load latest version
            model_uri = f"models:/{model_name}/latest"
            logger.info(f"Loading model from MLflow: {model_uri}")
            model = mlflow.sklearn.load_model(model_uri)
            version_number = "latest"

        model_info = {
            'model_name': model_name,
            'model_version': str(version_number),
            'model_alias': alias,
            'loaded_at': datetime.utcnow().isoformat(),
            'model_type': 'ensemble'
        }

        logger.info(f"Model loaded successfully: {model_info}")
        return model, model_info

    except Exception as e:
        logger.error(f"Error loading model from MLflow: {e}")
        raise


def load_model_local():
    """Load model from local file as fallback."""
    model_path = os.getenv('MODEL_LOCAL_PATH', 'models/latest.joblib')

    if not Path(model_path).exists():
        raise FileNotFoundError(f"Model not found at {model_path}")

    logger.info(f"Loading model from local file: {model_path}")
    model = joblib.load(model_path)

    model_info = {
        'model_name': 'FlightPricePredictor',
        'model_version': 'local',
        'model_alias': None,
        'loaded_at': datetime.utcnow().isoformat(),
        'model_type': 'ensemble'
    }

    return model, model_info


def initialize_model():
    """Initialize model on startup."""
    global current_model, current_model_info

    try:
        # Try loading by alias first
        alias = os.getenv('MODEL_ALIAS', 'production')
        try:
            current_model, current_model_info = load_model_from_mlflow(alias=alias)
        except:
            # Fallback to local model
            logger.warning("MLflow model not available, using local model")
            current_model, current_model_info = load_model_local()

        # Update Prometheus gauge
        MODEL_INFO.labels(
            model_name=current_model_info['model_name'],
            model_version=current_model_info['model_version']
        ).set(1)

        logger.info("Model initialization complete")

    except Exception as e:
        logger.error(f"Failed to initialize model: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Run initialization on startup."""
    logger.info("Starting Flight Price Prediction API...")
    initialize_model()
    logger.info("API startup complete")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint."""
    REQUEST_COUNT.labels(method='GET', endpoint='/health', status='200').inc()

    return {
        "status": "healthy",
        "model_loaded": current_model is not None,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/model_info", response_model=ModelInfoResponse)
async def get_model_info():
    """Get current model information."""
    REQUEST_COUNT.labels(method='GET', endpoint='/model_info', status='200').inc()

    if not current_model:
        raise HTTPException(status_code=503, detail="Model not loaded")

    return current_model_info


@app.post("/reload")
async def reload_model(alias: str = None, version: str = None):
    """
    Reload model without restarting the service (zero-downtime update).

    Args:
        alias: Model alias to load (e.g., 'production')
        version: Specific version to load
    """
    global current_model, current_model_info

    try:
        if alias:
            new_model, new_info = load_model_from_mlflow(alias=alias)
        elif version:
            new_model, new_info = load_model_from_mlflow(version=version)
        else:
            # Reload current alias
            current_alias = current_model_info.get('model_alias', 'production')
            new_model, new_info = load_model_from_mlflow(alias=current_alias)

        # Update global variables
        current_model = new_model
        current_model_info = new_info

        # Update Prometheus gauge
        MODEL_INFO.labels(
            model_name=new_info['model_name'],
            model_version=new_info['model_version']
        ).set(1)

        REQUEST_COUNT.labels(method='POST', endpoint='/reload', status='200').inc()

        return {
            "status": "success",
            "message": "Model reloaded successfully",
            "model_info": new_info
        }

    except Exception as e:
        REQUEST_COUNT.labels(method='POST', endpoint='/reload', status='500').inc()
        raise HTTPException(status_code=500, detail=f"Failed to reload model: {str(e)}")


@app.post("/predict", response_model=PredictionResponse)
async def predict(features: FlightFeatures):
    """
    Predict flight price based on input features.

    Args:
        features: Flight features for prediction

    Returns:
        Predicted price and metadata
    """
    start_time = time.time()

    if not current_model:
        REQUEST_COUNT.labels(method='POST', endpoint='/predict', status='503').inc()
        PREDICTION_COUNT.labels(status='error').inc()
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        # Convert features to format expected by model
        # This is simplified - you'll need to match your preprocessing pipeline
        feature_dict = features.dict(by_alias=True)

        # For now, we'll assume the model expects preprocessed features
        # In production, you'd apply the same preprocessing as training
        # TODO: Integrate with data preprocessing pipeline

        # Make prediction (placeholder - needs actual feature engineering)
        # predicted_price = current_model.predict(processed_features)[0]

        # Temporary: return a mock prediction
        # Replace this with actual model inference
        predicted_price = 5000.0  # Placeholder

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Log to database
        try:
            session = get_session()
            prediction_record = Prediction(
                features=feature_dict,
                predicted_price=float(predicted_price),
                model_name=current_model_info['model_name'],
                model_version=current_model_info['model_version'],
                latency_ms=latency_ms
            )
            session.add(prediction_record)
            session.commit()
            session.close()
        except Exception as db_error:
            logger.error(f"Failed to log prediction to database: {db_error}")

        # Update Prometheus metrics
        REQUEST_COUNT.labels(method='POST', endpoint='/predict', status='200').inc()
        PREDICTION_COUNT.labels(status='success').inc()
        PREDICTION_VALUE.observe(predicted_price)
        PREDICTION_LATENCY.observe(latency_ms)

        return PredictionResponse(
            predicted_price=predicted_price,
            model_name=current_model_info['model_name'],
            model_version=current_model_info['model_version'],
            prediction_timestamp=datetime.utcnow().isoformat(),
            latency_ms=latency_ms
        )

    except Exception as e:
        REQUEST_COUNT.labels(method='POST', endpoint='/predict', status='500').inc()
        PREDICTION_COUNT.labels(status='error').inc()
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Flight Price Prediction API",
        "version": os.getenv('API_VERSION', '1.0.0'),
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "model_info": "/model_info",
            "reload": "/reload",
            "metrics": "/metrics",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=os.getenv('APP_HOST', '0.0.0.0'),
        port=int(os.getenv('APP_PORT', 8000)),
        reload=os.getenv('RELOAD', 'false').lower() == 'true'
    )
