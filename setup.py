"""
Setup script for Flight Price Prediction MLOps project.
Automates initial project setup and validation.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(command, description, check=True):
    """Run a shell command with error handling."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr and not check:
            print(f"Warning: {result.stderr}")
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {description} failed")
        print(f"Error output: {e.stderr}")
        return False


def check_prerequisites():
    """Check if required software is installed."""
    print("\n" + "="*60)
    print("Checking Prerequisites")
    print("="*60)

    checks = {
        "Python 3.11+": ["python", "--version"],
        "Docker": ["docker", "--version"],
        "Git": ["git", "--version"],
    }

    all_passed = True
    for name, cmd in checks.items():
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            version = result.stdout.strip()
            print(f"✓ {name}: {version}")
        except FileNotFoundError:
            print(f"✗ {name}: Not found")
            all_passed = False

    return all_passed


def create_directories():
    """Create necessary directories."""
    print("\n" + "="*60)
    print("Creating Directories")
    print("="*60)

    directories = [
        "data/raw",
        "data/processed",
        "models",
        "reports",
        "mlflow",
        "mlruns",
        "logs"
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}")

    return True


def setup_environment():
    """Set up environment file."""
    print("\n" + "="*60)
    print("Setting Up Environment")
    print("="*60)

    if not Path(".env").exists():
        if Path(".env.example").exists():
            import shutil
            shutil.copy(".env.example", ".env")
            print("✓ Created .env from .env.example")
            print("⚠ Please edit .env with your actual values")
        else:
            print("✗ .env.example not found")
            return False
    else:
        print("✓ .env already exists")

    return True


def install_dependencies():
    """Install Python dependencies."""
    print("\n" + "="*60)
    print("Installing Python Dependencies")
    print("="*60)

    return run_command(
        "pip install -r requirements.txt",
        "Installing dependencies"
    )


def initialize_dvc():
    """Initialize DVC."""
    print("\n" + "="*60)
    print("Initializing DVC")
    print("="*60)

    if not Path(".dvc").exists():
        return run_command("dvc init", "Initializing DVC", check=False)
    else:
        print("✓ DVC already initialized")
        return True


def validate_docker_compose():
    """Validate docker-compose configuration."""
    print("\n" + "="*60)
    print("Validating Docker Compose")
    print("="*60)

    return run_command(
        "docker-compose -f infra/docker-compose.yaml config",
        "Validating docker-compose.yaml",
        check=False
    )


def print_summary():
    """Print setup summary and next steps."""
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)

    print("\n📋 Next Steps:\n")

    steps = [
        "1. Edit .env with your configuration values",
        "2. Start Docker services: cd infra && docker-compose up -d",
        "3. Prepare data: python -m src.ml.data",
        "4. Train model: python -m src.ml.train",
        "5. Start API: uvicorn src.app.api:app --reload",
        "6. Visit API docs: http://localhost:8000/docs",
        "7. Visit MLflow UI: http://localhost:5000"
    ]

    for step in steps:
        print(f"  {step}")

    print("\n📚 Documentation:\n")
    print("  - README.md: Full documentation")
    print("  - QUICKSTART.md: 10-minute quick start guide")
    print("  - AWS_SETUP_GUIDE.md: AWS deployment guide")

    print("\n🔧 Useful Commands:\n")
    print("  - Run tests: pytest -v")
    print("  - Start services: docker-compose up -d")
    print("  - View logs: docker-compose logs -f")
    print("  - Train model: python -m src.ml.train")

    print("\n" + "="*60)


def main():
    """Main setup function."""
    print("\n" + "="*60)
    print("Flight Price Prediction - MLOps Setup")
    print("="*60)

    # Check prerequisites
    if not check_prerequisites():
        print("\n✗ Prerequisites check failed. Please install missing software.")
        sys.exit(1)

    # Create directories
    if not create_directories():
        print("\n✗ Directory creation failed.")
        sys.exit(1)

    # Setup environment
    if not setup_environment():
        print("\n✗ Environment setup failed.")
        sys.exit(1)

    # Install dependencies
    print("\nDo you want to install Python dependencies? (y/n): ", end="")
    if input().lower() == 'y':
        if not install_dependencies():
            print("\n⚠ Dependency installation failed. You may need to install manually.")

    # Initialize DVC
    print("\nDo you want to initialize DVC? (y/n): ", end="")
    if input().lower() == 'y':
        initialize_dvc()

    # Validate Docker Compose
    print("\nDo you want to validate Docker Compose configuration? (y/n): ", end="")
    if input().lower() == 'y':
        validate_docker_compose()

    # Print summary
    print_summary()


if __name__ == "__main__":
    main()
