import pytest
from unittest.mock import patch
import os
import json
from app.ml.forecaster import Forecaster
from app.ml.grader import Grader
from app.config import settings

def test_version_mismatch_raises():
    metrics_path = os.path.join(settings.MODELS_DIR, "forecaster_metrics.json")
    with open(metrics_path) as f:
        original_metrics = json.load(f)
    
    modified_metrics = dict(original_metrics)
    modified_metrics["versions"] = dict(original_metrics.get("versions", {}))
    modified_metrics["versions"]["scikit-learn"] = "0.0.1_mismatch"
    
    try:
        with open(metrics_path, "w") as f:
            json.dump(modified_metrics, f)
        
        with pytest.raises(RuntimeError, match="version mismatch"):
            Forecaster()
    finally:
        with open(metrics_path, "w") as f:
            json.dump(original_metrics, f)

def test_health_degraded_path(client):
    from app.main import db
    # Mock db ping to fail
    with patch.object(db(), "ping", side_effect=Exception("Database unreachable")):
        r = client.get("/health")
        assert r.status_code == 503
        data = r.json()
        assert data["status"] == "degraded"
        assert data["db_ping"] is False

    with patch.object(db(), "ping", return_value=False):
        r = client.get("/health")
        assert r.status_code == 503
        data = r.json()
        assert data["status"] == "degraded"
        assert data["db_ping"] is False
