"""Render build-e chole: python -m app.ml.train_all"""
import json
import os

from ..config import settings


def ensure_models():
    need = ["forecaster.joblib", "latest_prices.json", "forecaster_metrics.json", "grader.joblib", "grader_metrics.json"]
    if all(os.path.exists(os.path.join(settings.MODELS_DIR, n)) for n in need):
        return False
    main()
    return True


def main():
    from . import forecaster, grader
    print("Training price forecaster...")
    print(json.dumps(forecaster.train(), indent=2))
    print("Training photo grader...")
    print(json.dumps(grader.train(), indent=2))


if __name__ == "__main__":
    main()
