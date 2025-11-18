# Flight Price Prediction - MLOps Project

Production-ready MLOps pipeline for flight price prediction using ensemble models, with complete AWS cloud deployment capability.

## Model Performance

| Metric | Value |
|--------|-------|
| R² Score | **0.9838** |
| MAE | 1,559 INR |
| RMSE | 2,891 INR |
| MAPE | 12.07% |

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat&logo=amazon-aws&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![MLflow](https://img.shields.io/badge/MLflow-0194E2?style=flat&logo=mlflow&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=flat&logo=grafana&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-E6522C?style=flat&logo=prometheus&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=flat&logo=scikit-learn&logoColor=white)

- **ML**: Random Forest + XGBoost + LightGBM (Ensemble)
- **Pipeline**: DVC for data versioning, MLflow for experiment tracking
- **API**: FastAPI with Prometheus metrics
- **Infrastructure**: Docker, AWS ECS Fargate, ECR
- **Monitoring**: Grafana, Prometheus, PostgreSQL logging

## Quick Start

### 1. Setup Environment

```bash
# Clone and setup
git clone <your-repo-url>
cd FlightPricePrediction

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 2. Start Local Services

```bash
cd infra
docker-compose up -d --build
```

This starts:
- **PostgreSQL**: localhost:5432
- **MLflow**: http://localhost:5000
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### 3. Train Model

```bash
# Using DVC pipeline (recommended)
dvc repro

# Or manually
python -m src.ml.data      # Prepare data
python -m src.ml.train     # Train model
python -m src.ml.evaluate  # Evaluate
```

### 4. Promote to Production

```bash
python scripts/promote_model.py --version 1 --alias production
```

### 5. Test API

```bash
# Health check
curl http://localhost:8000/health

# Make prediction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "airline": "Vistara",
    "flight": "UK-123",
    "source_city": "Delhi",
    "departure_time": "Morning",
    "stops": "zero",
    "arrival_time": "Afternoon",
    "destination_city": "Mumbai",
    "class": "Economy",
    "duration": 2.5,
    "days_left": 15
  }'
```

**API Documentation**: http://localhost:8000/docs

## AWS Deployment

### Prerequisites

- AWS CLI configured (`aws configure`)
- Docker installed

### Deploy to ECS Fargate

```bash
# 1. Create AWS resources
aws ecr create-repository --repository-name flightprice-app --region us-east-1
aws ecs create-cluster --cluster-name flightprice-cluster --region us-east-1
aws s3 mb s3://flightprice-mlops-<account-id> --region us-east-1

# 2. Build and push Docker image
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker build -t flightprice-app:latest -f docker/Dockerfile.app .
docker tag flightprice-app:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest

# 3. Create IAM role for ECS
aws iam create-role --role-name ecsTaskExecutionRole --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name ecsTaskExecutionRole --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# 4. Register task definition and create service
aws ecs register-task-definition --cli-input-json file://infra/aws/ecs-task-definition-app-simple.json --region us-east-1
aws ecs create-service --cluster flightprice-cluster --service-name flightprice-app-service --task-definition flightprice-app-task --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[<subnet-id>],securityGroups=[<sg-id>],assignPublicIp=ENABLED}" --region us-east-1
```

### Cleanup AWS Resources

```bash
aws ecs update-service --cluster flightprice-cluster --service flightprice-app-service --desired-count 0 --region us-east-1
aws ecs delete-service --cluster flightprice-cluster --service flightprice-app-service --region us-east-1
aws ecs delete-cluster --cluster flightprice-cluster --region us-east-1
aws ecr delete-repository --repository-name flightprice-app --force --region us-east-1
```

## Project Structure

```
FlightPricePrediction/
├── configs/                    # YAML configurations
│   ├── base.yaml              # Data & evaluation settings
│   └── training.yaml          # Model hyperparameters
├── docker/                    # Dockerfiles
├── infra/                     # Infrastructure
│   ├── docker-compose.yaml    # Local development
│   └── aws/                   # ECS task definitions
├── src/
│   ├── app/api.py            # FastAPI endpoints
│   ├── ml/
│   │   ├── data.py           # Data preprocessing
│   │   ├── models.py         # EnsembleModel class
│   │   ├── train.py          # Training pipeline
│   │   └── evaluate.py       # Model evaluation
│   ├── database/models.py    # SQLAlchemy ORM
│   └── monitoring/           # Drift detection
├── scripts/                   # Deployment scripts
├── tests/                     # Pytest suite
├── dvc.yaml                   # DVC pipeline
└── requirements.txt
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/predict` | POST | Make prediction |
| `/model_info` | GET | Current model info |
| `/reload` | POST | Hot-reload model |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Swagger UI |

## Configuration

### Model Weights (configs/training.yaml)

```yaml
ensemble:
  weights:
    random_forest: 0.35
    xgboost: 0.40
    lightgbm: 0.25
```

### Evaluation Thresholds (configs/base.yaml)

```yaml
evaluation:
  thresholds:
    min_r2: 0.75
    max_rmse: 5000
    max_mape: 0.15
```

## Monitoring

### Prometheus Metrics

- `app_request_count` - Request counter by endpoint
- `app_prediction_count` - Total predictions
- `app_prediction_value` - Price distribution
- `app_prediction_latency_ms` - Inference latency

### Data Drift Detection

```bash
python -m src.monitoring.drift_detection --hours 24
```

Generates HTML reports in `reports/` directory.

## Testing

```bash
# Run all tests
pytest -v

# With coverage
pytest --cov=src --cov-report=html
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci-cd.yaml`):
1. **Test** - Run pytest suite
2. **Lint** - Code quality (black, ruff)
3. **Build** - Docker image to ECR
4. **Deploy** - Update ECS service

## Cost Estimates (AWS)

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate (0.5 vCPU, 1GB) | ~$15 |
| ECR Storage | ~$1 |
| S3 Storage | ~$1 |
| CloudWatch Logs | ~$1 |
| **Total** | **~$18/month** |

## Troubleshooting

**Model not loading**: Check MLflow is running at http://localhost:5000

**Database errors**: Verify PostgreSQL container is healthy with `docker ps`

**API errors**: Check logs with `docker logs flightprice-app`

## License

MIT License
