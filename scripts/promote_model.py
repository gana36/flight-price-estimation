"""
Promote model to production using MLflow aliases.
Supports zero-downtime deployment with optional API reload.
"""

import os
import sys
import argparse
import mlflow
from mlflow import MlflowClient
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def promote_model(
    model_name: str,
    version: str,
    alias: str = "production",
    reload_app: bool = True,
    api_url: str = "http://localhost:8000"
):
    """
    Promote model version to an alias (e.g., production).

    Args:
        model_name: Name of registered model
        version: Model version to promote
        alias: Alias to assign (default: production)
        reload_app: Whether to reload the API after promotion
        api_url: Base URL of the API
    """
    logger.info(f"Promoting model {model_name} version {version} to alias '{alias}'")

    # Set MLflow tracking URI
    mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(mlflow_uri)

    client = MlflowClient()

    try:
        # Get model version details
        model_version = client.get_model_version(model_name, version)
        logger.info(f"Model version {version} details:")
        logger.info(f"  Run ID: {model_version.run_id}")
        logger.info(f"  Status: {model_version.status}")
        logger.info(f"  Created: {model_version.creation_timestamp}")

        # Set alias
        logger.info(f"Setting alias '{alias}' to version {version}")
        client.set_registered_model_alias(model_name, alias, version)
        logger.info(f"✓ Alias '{alias}' set successfully")

        # Verify alias
        alias_version = client.get_model_version_by_alias(model_name, alias)
        logger.info(f"✓ Verified: alias '{alias}' points to version {alias_version.version}")

        # Reload API if requested
        if reload_app:
            logger.info(f"Reloading API at {api_url}...")
            try:
                response = requests.post(
                    f"{api_url}/reload",
                    params={"alias": alias},
                    timeout=30
                )
                response.raise_for_status()
                logger.info(f"✓ API reloaded successfully: {response.json()}")
            except Exception as e:
                logger.error(f"Failed to reload API: {e}")
                logger.warning("Model alias updated but API reload failed. Restart service manually.")

        logger.info(f"✓ Model promotion complete!")

    except Exception as e:
        logger.error(f"Model promotion failed: {e}")
        sys.exit(1)


def list_model_versions(model_name: str):
    """List all versions of a model."""
    mlflow_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(mlflow_uri)

    client = MlflowClient()

    try:
        versions = client.search_model_versions(f"name='{model_name}'")

        logger.info(f"Model versions for '{model_name}':")
        for mv in versions:
            logger.info(f"  Version {mv.version}:")
            logger.info(f"    Status: {mv.status}")
            logger.info(f"    Aliases: {mv.aliases if hasattr(mv, 'aliases') else 'N/A'}")
            logger.info(f"    Run ID: {mv.run_id}")
            logger.info("")

    except Exception as e:
        logger.error(f"Failed to list versions: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Promote model to production')
    parser.add_argument(
        '--model-name',
        type=str,
        default='FlightPricePredictor',
        help='Name of the registered model'
    )
    parser.add_argument(
        '--version',
        type=str,
        required=True,
        help='Model version to promote'
    )
    parser.add_argument(
        '--alias',
        type=str,
        default='production',
        help='Alias to assign (default: production)'
    )
    parser.add_argument(
        '--reload-app',
        action='store_true',
        default=True,
        help='Reload API after promotion (default: True)'
    )
    parser.add_argument(
        '--api-url',
        type=str,
        default='http://localhost:8000',
        help='Base URL of the API'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all model versions'
    )

    args = parser.parse_args()

    if args.list:
        list_model_versions(args.model_name)
    else:
        promote_model(
            model_name=args.model_name,
            version=args.version,
            alias=args.alias,
            reload_app=args.reload_app,
            api_url=args.api_url
        )
