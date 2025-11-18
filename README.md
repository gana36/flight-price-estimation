# Flight Price Prediction - MLOps Project

Production-ready MLOps pipeline for flight price prediction using ensemble models (Random Forest + XGBoost + LightGBM), fully compatible with AWS cloud infrastructure.

## Features

- **Ensemble Model**: Combines Random Forest, XGBoost, and LightGBM for robust predictions
- **AWS Cloud Ready**: Complete integration with S3, RDS, ECR, and ECS
- **MLOps Pipeline**: End-to-end ML pipeline with DVC for data versioning and MLflow for model tracking
- **API Service**: FastAPI-based REST API with health checks and metrics
- **Monitoring**: Prometheus metrics, Grafana dashboards, and Evidently drift detection
- **CI/CD**: GitHub Actions pipeline for automated testing and deployment
- **Zero-Downtime Deployment**: Hot-reload model updates without service restart
- **Database Logging**: PostgreSQL-based prediction logging for monitoring and analysis

## Project Structure

```
FlightPricePrediction/
├── configs/                    # Configuration files
│   ├── base.yaml              # Base configuration
│   └── training.yaml          # Model hyperparameters
├── data/
│   ├── raw/                   # Raw data (gitignored)
│   └── processed/             # Processed data (DVC-tracked)
├── docker/                    # Docker configurations
│   ├── Dockerfile.app         # API application container
│   └── Dockerfile.mlflow      # MLflow server container
├── infra/                     # Infrastructure configs
│   ├── docker-compose.yaml    # Local development
│   ├── prometheus/            # Prometheus configuration
│   └── aws/                   # AWS ECS task definitions
├── models/                    # Trained models (local backup)
├── reports/                   # Evaluation and drift reports
├── scripts/                   # Deployment scripts
│   ├── promote_model.py       # Model promotion
│   └── validate_model.py      # Model validation
├── src/
│   ├── app/                   # FastAPI application
│   │   ├── api.py            # API endpoints
│   │   └── metrics.py        # Prometheus metrics
│   ├── database/              # Database models
│   │   └── models.py         # SQLAlchemy ORM
│   ├── ml/                    # ML pipeline
│   │   ├── data.py           # Data preprocessing
│   │   ├── train.py          # Model training
│   │   └── evaluate.py       # Model evaluation
│   └── monitoring/            # Monitoring tools
│       └── drift_detection.py # Data drift monitoring
├── tests/                     # Test suite
│   ├── test_api.py           # API tests
│   └── test_model.py         # Model tests
├── .github/workflows/         # CI/CD pipelines
├── dvc.yaml                   # DVC pipeline definition
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git
- AWS CLI (for cloud deployment)

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd FlightPricePrediction
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configurations
   ```

5. **Start services with Docker Compose**
   ```bash
   cd infra
   docker-compose up --build -d
   ```

6. **Initialize database**
   ```bash
   python -m src.database.models
   ```

### Training the Model

1. **Prepare data**
   ```bash
   python -m src.ml.data
   ```

2. **Train ensemble model**
   ```bash
   # Ensure MLflow is running
   set MLFLOW_TRACKING_URI=http://localhost:5000
   python -m src.ml.train
   ```

3. **Evaluate model**
   ```bash
   python -m src.ml.evaluate
   ```

4. **Validate and promote model**
   ```bash
   python scripts/validate_model.py --version 1
   python scripts/promote_model.py --version 1 --alias production --reload-app
   ```

### Running the API

**Option 1: Docker (Recommended)**
```bash
cd infra
docker-compose up app
```

**Option 2: Local**
```bash
uvicorn src.app.api:app --host 0.0.0.0 --port 8000 --reload
```

Access the API:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics
- MLflow UI: http://localhost:5000
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

### Making Predictions

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "SpiceJet",
    "source_city": "Delhi",
    "destination_city": "Mumbai",
    "departure_time": "Evening",
    "arrival_time": "Night",
    "stops": "zero",
    "class": "Economy",
    "duration": 2.17,
    "days_left": 1
  }'
```

## AWS Deployment

### Prerequisites

1. **AWS Account Setup**
   - Create S3 buckets for DVC and MLflow artifacts
   - Set up RDS PostgreSQL for MLflow backend and predictions
   - Create ECR repositories for Docker images
   - Configure ECS cluster

2. **Configure AWS Credentials**
   ```bash
   aws configure
   ```

3. **Set up Secrets Manager**
   Store sensitive credentials in AWS Secrets Manager:
   - Database connection strings
   - MLflow URIs
   - API keys

### Deployment Steps

1. **Push Docker images to ECR**
   ```bash
   # Login to ECR
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

   # Build and push app image
   docker build -f docker/Dockerfile.app -t <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest .
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest

   # Build and push MLflow image
   docker build -f docker/Dockerfile.mlflow -t <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-mlflow:latest .
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-mlflow:latest
   ```

2. **Update ECS task definitions**
   ```bash
   # Update placeholders in task definitions
   cd infra/aws
   # Edit ecs-task-definition-app.json and ecs-task-definition-mlflow.json

   # Register task definitions
   aws ecs register-task-definition --cli-input-json file://ecs-task-definition-app.json
   aws ecs register-task-definition --cli-input-json file://ecs-task-definition-mlflow.json
   ```

3. **Deploy to ECS**
   ```bash
   aws ecs update-service \
     --cluster flightprice-cluster \
     --service flightprice-app-service \
     --task-definition flightprice-app-task \
     --force-new-deployment
   ```

4. **Configure DVC with S3**
   ```bash
   dvc remote modify s3remote access_key_id <your-access-key>
   dvc remote modify s3remote secret_access_key <your-secret-key>
   dvc push
   ```

## Configuration

### Base Configuration (`configs/base.yaml`)

Controls data processing, evaluation thresholds, and MLflow settings.

Key parameters:
- `data.test_size`: Train/test split ratio (default: 0.2)
- `evaluation.thresholds.min_r2`: Minimum R² score for model validation (default: 0.75)
- `evaluation.thresholds.max_rmse`: Maximum RMSE for model validation (default: 5000)

### Training Configuration (`configs/training.yaml`)

Controls ensemble model hyperparameters.

Key parameters:
- `ensemble.weights`: Model weights for ensemble (RF: 0.35, XGB: 0.40, LGB: 0.25)
- `models.*`: Individual model hyperparameters

## Monitoring

### Data Drift Detection

Monitor production data drift:
```bash
python -m src.monitoring.drift_detection --hours 24
```

Generates HTML reports in `reports/` directory.

### Metrics

Prometheus metrics available at `/metrics`:
- `app_request_count`: Request counter by endpoint
- `app_request_latency_seconds`: Request latency histogram
- `app_prediction_count`: Prediction counter
- `app_prediction_value`: Predicted price distribution
- `app_prediction_latency_ms`: Prediction latency

## Testing

Run all tests:
```bash
pytest -v
```

Run specific test suites:
```bash
pytest tests/test_api.py -v
pytest tests/test_model.py -v
```

With coverage:
```bash
pytest --cov=src --cov-report=html
```

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/ci-cd.yaml`):

1. **Test**: Run pytest suite
2. **Lint**: Code quality checks (black, ruff, isort)
3. **Build**: Build and push Docker images to ECR
4. **Deploy**: Update ECS services

Triggers:
- Push to `main` or `develop`
- Pull requests to `main`

## Model Promotion Workflow

1. **Train model**
   ```bash
   python -m src.ml.train
   ```

2. **Validate model**
   ```bash
   python scripts/validate_model.py --version <version-number>
   ```

3. **Promote to production**
   ```bash
   python scripts/promote_model.py --version <version-number> --alias production --reload-app
   ```

4. **Verify deployment**
   ```bash
   curl http://localhost:8000/model_info
   ```

## Troubleshooting

### Model not loading in API
- Check MLflow server is running: `http://localhost:5000`
- Verify model is registered in MLflow
- Check logs: `docker logs flightprice-app`

### Database connection errors
- Ensure PostgreSQL is running: `docker ps`
- Verify DATABASE_URL in `.env`
- Check database exists: `psql -U postgres -l`

### Prediction errors
- Validate input features match training data
- Check model compatibility
- Review API logs for detailed error messages

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/predict` | POST | Make prediction |
| `/model_info` | GET | Current model information |
| `/reload` | POST | Reload model (zero-downtime) |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | API documentation (Swagger UI) |

## Environment Variables

See `.env.example` for complete list of environment variables.

Key variables:
- `MLFLOW_TRACKING_URI`: MLflow server URL
- `DATABASE_URL`: PostgreSQL connection string
- `AWS_REGION`: AWS region for S3/ECR/ECS
- `MODEL_ALIAS`: Model alias to load (default: production)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request
