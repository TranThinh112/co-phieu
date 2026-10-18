import joblib
import datetime
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV

from models.dataset import DatasetBuilder
from models.evaluate import ModelEvaluator
from models.model_registry import ModelRegistry

class ModelTrainer:
    """Trains, calibrates and registers LightGBM models for stock horizons (5D, 10D, 20D)."""

    def __init__(self, model_dir: str = "models/saved_models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.registry = ModelRegistry(registry_file=self.model_dir / "registry.json")

    def train_horizon_model(self, stock_dfs: Dict[str, pd.DataFrame], horizon: int = 10) -> Dict[str, Any]:
        print(f"[ModelTrainer] Building dataset for horizon {horizon}D...")
        builder = DatasetBuilder()
        X, y = builder.create_dataset(stock_dfs, horizon=horizon)

        if X.empty or len(X) < 60:
            print(f"[ModelTrainer] Insufficient data to train horizon {horizon}D ({len(X)} samples).")
            return {"status": "failed", "reason": "Insufficient samples"}

        X_train, y_train, X_test, y_test = DatasetBuilder.time_series_split(X, y, test_ratio=0.2, purge_window=horizon)

        if len(X_train) < 30 or len(X_test) < 10:
            print(f"[ModelTrainer] Split resulted in empty train/test sets.")
            return {"status": "failed", "reason": "Split too small"}

        # Base LightGBM classifier with hyperparameter constraint to prevent overfitting
        base_model = LGBMClassifier(
            n_estimators=100,
            learning_rate=0.03,
            max_depth=4,
            num_leaves=15,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1
        )

        # Calibrated classifier for reliable probability output
        calibrated_model = CalibratedClassifierCV(estimator=base_model, cv=3, method='sigmoid')
        calibrated_model.fit(X_train, y_train)

        # Predict out-of-sample test probabilities
        y_prob_test = calibrated_model.predict_proba(X_test)[:, 1]
        eval_metrics = ModelEvaluator.evaluate_predictions(y_test.to_numpy(), y_prob_test)

        # Save trained model artifact
        model_id = f"lgbm_{horizon}d_{datetime.date.today().strftime('%Y%m%d')}"
        model_filepath = self.model_dir / f"model_{horizon}d.joblib"
        joblib.dump(calibrated_model, model_filepath)

        # Register metadata
        self.registry.register_model(
            horizon=horizon,
            model_id=model_id,
            features=DatasetBuilder.FEATURE_COLS,
            metrics=eval_metrics,
            filepath=str(model_filepath)
        )

        print(f"[ModelTrainer] Trained {horizon}D model successfully. Brier Score: {eval_metrics['brier_score']}, Precision@K: {eval_metrics['precision_at_k']}")
        return {
            "status": "success",
            "horizon": horizon,
            "metrics": eval_metrics,
            "filepath": str(model_filepath)
        }

    def train_all_horizons(self, stock_dfs: Dict[str, pd.DataFrame], horizons: List[int] = [5, 10, 20]) -> Dict[int, Any]:
        results = {}
        for h in horizons:
            results[h] = self.train_horizon_model(stock_dfs, horizon=h)
        return results
