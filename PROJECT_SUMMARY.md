# Flight Price Prediction - Project Summary

## Overview

A production-ready MLOps pipeline for Indian domestic flight price prediction using ensemble machine learning models, deployed on AWS ECS Fargate.

## Model Results

| Metric | Value |
|--------|-------|
| **R² Score** | 0.9838 |
| **MAE** | 1,559 INR |
| **RMSE** | 2,891 INR |
| **MAPE** | 12.07% |
| **Dataset** | 300,153 records |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   DVC       │────▶│   MLflow    │────▶│   FastAPI   │
│  (Data)     │     │  (Models)   │     │   (API)     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│     S3      │     │  PostgreSQL │     │ Prometheus  │
│  (Storage)  │     │  (Logging)  │     │  (Metrics)  │
└─────────────┘     └─────────────┘     └─────────────┘
```

## What Was Built

### Machine Learning
- **Ensemble Model**: Random Forest (35%) + XGBoost (40%) + LightGBM (25%)
- **Features**: 12 features including airline, route, time, class, duration
- **Preprocessing**: LabelEncoder for categoricals, StandardScaler for numericals

### API Service
- FastAPI REST endpoints
- Health checks for ECS
- Prometheus metrics export
- Zero-downtime model reloading
- Swagger documentation

### Infrastructure
- Docker containers for all services
- Docker Compose for local development
- AWS ECS Fargate deployment
- ECR for image registry

### Monitoring
- Prometheus metrics collection
- Grafana dashboards
- PostgreSQL prediction logging
- Data drift detection with Evidently

### CI/CD
- GitHub Actions workflow
- Automated testing with pytest
- Docker build and push to ECR
- ECS service deployment

## Project Structure

```
FlightPricePrediction/
├── configs/                    # YAML configurations
│   ├── base.yaml              # Data & evaluation settings
│   └── training.yaml          # Model hyperparameters
├── docker/                    # Dockerfiles
│   ├── Dockerfile.app         # FastAPI container
│   └── Dockerfile.mlflow      # MLflow container
├── infra/                     # Infrastructure
│   ├── docker-compose.yaml    # Local services
│   ├── prometheus/            # Prometheus config
│   └── aws/                   # ECS task definitions
├── src/
│   ├── app/
│   │   ├── api.py            # FastAPI endpoints
│   │   └── metrics.py        # Prometheus metrics
│   ├── database/
│   │   └── models.py         # SQLAlchemy ORM
│   ├── ml/
│   │   ├── data.py           # Data preprocessing
│   │   ├── models.py         # EnsembleModel class
│   │   ├── train.py          # Training pipeline
│   │   └── evaluate.py       # Model evaluation
│   └── monitoring/
│       └── drift_detection.py
├── scripts/
│   ├── promote_model.py       # Model promotion
│   └── validate_model.py      # Model validation
├── tests/
│   ├── test_api.py
│   └── test_model.py
├── dvc.yaml                   # DVC pipeline
├── requirements.txt
└── .github/workflows/ci-cd.yaml
```

## Technology Stack

| Category | Technologies |
|----------|-------------|
| **ML** | scikit-learn, XGBoost, LightGBM, pandas, numpy |
| **MLOps** | MLflow, DVC, Evidently |
| **API** | FastAPI, Uvicorn, Pydantic |
| **Database** | PostgreSQL, SQLAlchemy |
| **Monitoring** | Prometheus, Grafana |
| **Infrastructure** | Docker, AWS ECS Fargate, ECR, S3 |
| **CI/CD** | GitHub Actions |
| **Testing** | pytest, black, ruff |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check for ECS |
| `/predict` | POST | Make prediction |
| `/model_info` | GET | Current model metadata |
| `/reload` | POST | Hot-reload model |
| `/metrics` | GET | Prometheus metrics |
| `/docs` | GET | Swagger UI |

## Workflows

### Training Pipeline
```bash
dvc repro  # Runs: prepare → train → evaluate
```

### Model Promotion
```bash
python scripts/promote_model.py --version 1 --alias production
```

### Local Deployment
```bash
cd infra && docker-compose up -d --build
```

### AWS Deployment
```bash
docker build -t flightprice-app -f docker/Dockerfile.app .
docker tag flightprice-app <account>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/flightprice-app:latest
aws ecs update-service --cluster flightprice-cluster --service flightprice-app-service --force-new-deployment
```

## Cost Estimates (AWS)

| Service | Monthly Cost |
|---------|-------------|
| ECS Fargate (0.5 vCPU, 1GB) | ~$15 |
| ECR Storage | ~$1 |
| S3 Storage | ~$1 |
| CloudWatch Logs | ~$1 |
| **Total** | **~$18/month** |

## Key Design Decisions

1. **Ensemble over Single Model** - Better generalization (R² = 0.98)
2. **LabelEncoder over OneHotEncoder** - Reduces feature dimensionality
3. **MLflow Aliases** - Modern approach for model promotion
4. **DVC for Data** - Version control for large datasets
5. **FastAPI over Flask** - Better performance, auto-docs
6. **Fargate over EC2** - Serverless, managed scaling
7. **PostgreSQL** - ACID compliance for prediction logging

## Local Services

| Service | URL | Credentials |
|---------|-----|-------------|
| FastAPI | http://localhost:8000/docs | - |
| MLflow | http://localhost:5000 | - |
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| PostgreSQL | localhost:5432 | postgres/postgres |

## Files Created

- **Source Code**: 10 Python modules
- **Configurations**: 2 YAML configs + .env
- **Docker**: 2 Dockerfiles + docker-compose
- **Infrastructure**: ECS task definitions, Prometheus config
- **Documentation**: README, QUICKSTART, AWS_SETUP_GUIDE
- **CI/CD**: GitHub Actions workflow
- **Tests**: API and model tests

## Next Steps

1. **Add more features** - Weather, holidays, events
2. **Implement A/B testing** - Compare model versions
3. **Set up alerts** - CloudWatch alarms for errors
4. **Add Grafana dashboards** - Visualize predictions
5. **Implement caching** - Redis for frequent predictions
6. **Add authentication** - API key or OAuth

---

**Built with MLOps best practices for production deployment on AWS.**
