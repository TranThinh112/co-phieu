import json
import datetime
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional
from data.storage import StorageEngine

class ModelRegistry:
    """Manages metadata, versioning and persistence for trained ML models."""

    def __init__(self, registry_file: str = "models/saved_models/registry.json", db_path: str = "database/scanner.db"):
        self.registry_file = Path(registry_file)
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path)
        # Ensure database tables are created
        self.storage = StorageEngine(str(db_path))
        self._init_file()

    def _init_file(self):
        if not self.registry_file.exists():
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def register_model(self, horizon: int, model_id: str, features: List[str], metrics: Dict[str, Any], filepath: str):
        with open(self.registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "model_id": model_id,
            "horizon": horizon,
            "trained_at": now_str,
            "features": features,
            "metrics": metrics,
            "filepath": str(filepath)
        }

        registry[str(horizon)] = entry

        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO model_registry (model_id, horizon, trained_at, train_samples, features, metrics_json, filepath)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    model_id,
                    horizon,
                    now_str,
                    metrics.get("total_test_samples", 0),
                    json.dumps(features),
                    json.dumps(metrics),
                    str(filepath)
                ))
                conn.commit()
        except Exception as e:
            print(f"[ModelRegistry] DB log error: {e}")

    def get_model_info(self, horizon: int) -> Optional[Dict[str, Any]]:
        if not self.registry_file.exists():
            return None
        with open(self.registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
        return registry.get(str(horizon))
