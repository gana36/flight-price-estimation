"""
Prometheus metrics for the Flight Price Prediction API.
Tracks requests, latency, and prediction counts.
"""

from prometheus_client import Counter, Histogram, Gauge

# Request counter by method, endpoint, and status
REQUEST_COUNT = Counter(
    'app_request_count',
    'Total request count',
    ['method', 'endpoint', 'status']
)

# Request latency histogram
REQUEST_LATENCY = Histogram(
    'app_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint']
)

# Prediction counter
PREDICTION_COUNT = Counter(
    'app_prediction_count',
    'Total prediction count',
    ['status']  # success, error
)

# Model info gauge
MODEL_INFO = Gauge(
    'app_model_info',
    'Information about the current model',
    ['model_name', 'model_version']
)

# Prediction value histogram
PREDICTION_VALUE = Histogram(
    'app_prediction_value',
    'Distribution of predicted flight prices',
    buckets=[1000, 2000, 5000, 10000, 20000, 50000, 100000]
)

# Prediction latency
PREDICTION_LATENCY = Histogram(
    'app_prediction_latency_ms',
    'Prediction latency in milliseconds',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
)
