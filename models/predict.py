import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional

from models.dataset import DatasetBuilder
from models.model_registry import ModelRegistry


class ModelPredictor:
    """Inference engine for trained ML probability models with in-memory caching."""

    _CACHED_MODELS: Optional[Dict[int, Any]] = None

    def __init__(self, model_dir: str = "models/saved_models"):
        self.model_dir = Path(model_dir)
        self.registry = ModelRegistry(registry_file=self.model_dir / "registry.json")
        self.models: Dict[int, Any] = {}
        self.load_models()

    def load_models(self):
        if ModelPredictor._CACHED_MODELS is not None:
            self.models = dict(ModelPredictor._CACHED_MODELS)
            return

        loaded: Dict[int, Any] = {}
        for horizon in [5, 10, 20]:
            info = self.registry.get_model_info(horizon)
            if info and "filepath" in info:
                fpath = Path(info["filepath"])
                if fpath.exists():
                    try:
                        model = joblib.load(fpath)
                        loaded[horizon] = model
                    except Exception as e:
                        print(f"[ModelPredictor] Error loading model for horizon {horizon}D: {e}")

        ModelPredictor._CACHED_MODELS = loaded
        self.models = dict(loaded)

    def predict_stock_probabilities(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        probs = {
            "ai_prob_5d": None,
            "ai_prob_10d": None,
            "ai_prob_20d": None
        }

        if df is None or df.empty or len(df) < 30:
            return probs

        builder = DatasetBuilder()
        full_df = builder.build_features_for_df(df)
        if full_df.empty:
            return probs

        # Extract features for latest row
        last_row = full_df[DatasetBuilder.FEATURE_COLS].iloc[[-1]]
        if last_row.isna().sum().sum() > 0:
            return probs

        for h, key in [(5, "ai_prob_5d"), (10, "ai_prob_10d"), (20, "ai_prob_20d")]:
            if h in self.models:
                try:
                    p = float(self.models[h].predict_proba(last_row)[0, 1])
                    probs[key] = round(p, 4)
                except Exception as e:
                    probs[key] = None
            else:
                probs[key] = None

        return probs
