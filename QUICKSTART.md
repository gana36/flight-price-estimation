# Quick Start Guide

Get the Flight Price Prediction project running locally in about 10 minutes.

## Prerequisites

- Python 3.11+
- Docker Desktop
- 8GB+ RAM available

## Step 1: Setup Environment

```bash
cd FlightPricePrediction

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Start Docker Services

```bash
# Copy environment template
copy .env.example .env

# Start services
cd infra
docker-compose up -d

# Check services are running
docker-compose ps
```

Services available at:
- MLflow: http://localhost:5000
- PostgreSQL: localhost:5432
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## Step 3: Train Model

```bash
cd ..  # Back to project root

# Option 1: Use DVC pipeline (recommended)
dvc repro

# Option 2: Run manually
python -m src.ml.data      # Prepare data
python -m src.ml.train     # Train model
python -m src.ml.evaluate  # Evaluate
```

Check MLflow at http://localhost:5000 to see experiment results.

## Step 4: Promote Model

```bash
python scripts/promote_model.py --version 1 --alias production
```

## Step 5: Start API

```bash
# Option 1: Docker (recommended)
cd infra
docker-compose up app

# Option 2: Local development
uvicorn src.app.api:app --reload --host 0.0.0.0 --port 8000
```

## Step 6: Test API

Open http://localhost:8000/docs for interactive documentation.

Or use curl:

```bash
curl -X POST http://localhost:8000/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"airline\": \"Vistara\", \"flight\": \"UK-123\", \"source_city\": \"Delhi\", \"departure_time\": \"Morning\", \"stops\": \"zero\", \"arrival_time\": \"Afternoon\", \"destination_city\": \"Mumbai\", \"class\": \"Economy\", \"duration\": 2.5, \"days_left\": 15}"
```

## Verify Setup

- Health Check: http://localhost:8000/health
- Model Info: http://localhost:8000/model_info
- Metrics: http://localhost:8000/metrics
- API Docs: http://localhost:8000/docs
- MLflow UI: http://localhost:5000

## Common Commands

### Training
```bash
dvc repro                    # Full pipeline
python -m src.ml.train       # Train only
python -m src.ml.evaluate    # Evaluate only
```

### Model Management
```bash
python scripts/promote_model.py --model-name FlightPricePredictor --list
python scripts/validate_model.py --version 1
python scripts/promote_model.py --version 1 --alias production
```

### Docker
```bash
docker-compose up -d         # Start all
docker-compose down          # Stop all
docker-compose logs -f app   # View logs
docker-compose up --build    # Rebuild
```

### Testing
```bash
pytest -v
pytest --cov=src --cov-report=html
```

## Troubleshooting

### Docker won't start
```bash
# Check port conflicts
netstat -ano | findstr :5000
netstat -ano | findstr :8000

# Reset containers
docker-compose down -v
docker-compose up -d
```

### Model not loading
- Check MLflow is running: http://localhost:5000
- Check logs: `docker-compose logs app`

### Import errors
```bash
# Ensure venv is activated
venv\Scripts\activate
pip install -r requirements.txt
```

## Clean Up

```bash
docker-compose down      # Stop services
docker-compose down -v   # Remove data too
deactivate               # Exit venv
```

## Next Steps

1. Try different predictions in the /docs interface
2. Review experiments in MLflow
3. Check AWS_SETUP_GUIDE.md for cloud deployment
4. Adjust hyperparameters in configs/training.yaml
