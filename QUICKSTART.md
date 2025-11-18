# Quick Start Guide - Flight Price Prediction MLOps

This guide will get you up and running with the Flight Price Prediction project in 10 minutes.

## Prerequisites

- Python 3.11+
- Docker Desktop (for Windows)
- 8GB+ RAM available

## Step 1: Clone and Setup (2 minutes)

```bash
# Navigate to project directory
cd FlightPricePrediction

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Start Services (3 minutes)

```bash
# Copy environment template
copy .env.example .env

# Start Docker services
cd infra
docker-compose up -d

# Wait for services to be healthy (check with)
docker-compose ps
```

Services will be available at:
- MLflow UI: http://localhost:5000
- PostgreSQL: localhost:5432
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Step 3: Prepare Data (2 minutes)

```bash
# Return to project root
cd ..

# Prepare datasets
python -m src.ml.data
```

This creates train/test splits and saves them to `data/processed/`.

## Step 4: Train Model (3 minutes)

```bash
# Set MLflow tracking URI
set MLFLOW_TRACKING_URI=http://localhost:5000

# Train ensemble model
python -m src.ml.train

# This will:
# - Train Random Forest, XGBoost, and LightGBM models
# - Combine them into an ensemble
# - Log to MLflow
# - Save model locally
```

Check MLflow UI at http://localhost:5000 to see your experiment!

## Step 5: Start API (1 minute)

```bash
# Option 1: Local (development)
uvicorn src.app.api:app --reload --host 0.0.0.0 --port 8000

# Option 2: Docker (production-like)
cd infra
docker-compose up app
```

## Step 6: Test API (1 minute)

Open http://localhost:8000/docs for interactive API documentation.

Or test with curl:

```bash
curl -X POST "http://localhost:8000/predict" ^
  -H "Content-Type: application/json" ^
  -d "{\"airline\": \"SpiceJet\", \"source_city\": \"Delhi\", \"destination_city\": \"Mumbai\", \"departure_time\": \"Evening\", \"arrival_time\": \"Night\", \"stops\": \"zero\", \"class\": \"Economy\", \"duration\": 2.17, \"days_left\": 1}"
```

## Step 7: Promote Model to Production

```bash
# Validate model meets thresholds
python scripts\validate_model.py --version 1

# Promote to production
python scripts\promote_model.py --version 1 --alias production --reload-app
```

## Verify Everything Works

1. **Health Check**: http://localhost:8000/health
2. **Model Info**: http://localhost:8000/model_info
3. **Metrics**: http://localhost:8000/metrics
4. **MLflow**: http://localhost:5000
5. **API Docs**: http://localhost:8000/docs

## Common Commands

### Data Pipeline
```bash
# Run full DVC pipeline
dvc repro

# Prepare data only
python -m src.ml.data

# Train model
python -m src.ml.train

# Evaluate model
python -m src.ml.evaluate
```

### Model Management
```bash
# List model versions
python scripts\promote_model.py --model-name FlightPricePredictor --list

# Validate before promotion
python scripts\validate_model.py --version 1

# Promote to production
python scripts\promote_model.py --version 1 --alias production
```

### Testing
```bash
# Run all tests
pytest -v

# Run specific tests
pytest tests/test_api.py -v
pytest tests/test_model.py -v

# With coverage
pytest --cov=src --cov-report=html
```

### Docker Services
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f app
docker-compose logs -f mlflow

# Rebuild after code changes
docker-compose up --build
```

### Monitoring
```bash
# Monitor data drift (requires predictions in DB)
python -m src.monitoring.drift_detection --hours 24

# View Grafana dashboards
# Open http://localhost:3000 (admin/admin)

# View Prometheus metrics
# Open http://localhost:9090
```

## Troubleshooting

### Docker services won't start
```bash
# Check if ports are already in use
netstat -ano | findstr :5000
netstat -ano | findstr :8000
netstat -ano | findstr :5432

# Stop and remove all containers
docker-compose down -v

# Restart
docker-compose up -d
```

### Model not loading in API
```bash
# Check MLflow is running
curl http://localhost:5000/health

# Check model is registered
# Visit http://localhost:5000 and look for "FlightPricePredictor"

# Check API logs
docker-compose logs app
```

### Import errors
```bash
# Make sure you're in project root and venv is activated
cd C:\Users\saiga\OneDrive\Documents\Data_SCience\MLOps\FlightPricePrediction
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker ps | findstr postgres

# Check database exists
docker exec -it flightprice-postgres psql -U postgres -c "\l"

# Create tables if missing
python -m src.database.models
```

## Next Steps

1. **Explore the API**: Try different flight combinations in the /docs interface
2. **Check MLflow**: Review experiment runs and model metrics
3. **Set up monitoring**: Run some predictions and check drift detection
4. **AWS Deployment**: Follow AWS_SETUP_GUIDE.md for cloud deployment
5. **Customize models**: Adjust hyperparameters in configs/training.yaml

## Development Workflow

1. Make code changes
2. Run tests: `pytest -v`
3. Train new model: `python -m src.ml.train`
4. Validate: `python scripts\validate_model.py --version <new-version>`
5. Promote: `python scripts\promote_model.py --version <new-version> --alias production`
6. Monitor: Check metrics at /metrics and drift reports

## Getting Help

- Check logs: `docker-compose logs -f`
- Review README.md for detailed documentation
- Check AWS_SETUP_GUIDE.md for cloud deployment
- Run tests to verify setup: `pytest -v`

## Clean Up

```bash
# Stop all services
docker-compose down

# Remove all data (careful!)
docker-compose down -v

# Deactivate virtual environment
deactivate
```

Congratulations! You now have a fully functional MLOps pipeline for flight price prediction running locally. Ready to deploy to AWS? Check out AWS_SETUP_GUIDE.md!
