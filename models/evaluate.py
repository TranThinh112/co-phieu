import numpy as np
import pandas as pd
from typing import Dict, Any, List
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score, accuracy_score, precision_score

class ModelEvaluator:
    """Evaluates ML probability models out-of-sample."""

    @staticmethod
    def evaluate_predictions(y_true: np.ndarray, y_prob: np.ndarray, top_k: int = 5) -> Dict[str, Any]:
        if len(y_true) == 0 or len(y_prob) == 0:
            return {
                "brier_score": 1.0,
                "log_loss": 9.9,
                "accuracy": 0.0,
                "roc_auc": 0.5,
                "precision_at_k": 0.0,
                "total_test_samples": 0
            }

        # Clip probabilities to avoid log loss log(0)
        y_prob_clipped = np.clip(y_prob, 1e-5, 1 - 1e-5)
        y_pred = (y_prob >= 0.5).astype(int)

        brier = float(brier_score_loss(y_true, y_prob))
        l_loss = float(log_loss(y_true, y_prob_clipped))
        acc = float(accuracy_score(y_true, y_pred))

        try:
            auc = float(roc_auc_score(y_true, y_prob))
        except Exception:
            auc = 0.5

        # Precision@K calculation
        k = min(top_k, len(y_prob))
        top_indices = np.argsort(y_prob)[-k:]
        prec_k = float(np.mean(y_true[top_indices])) if k > 0 else 0.0

        return {
            "brier_score": round(brier, 4),
            "log_loss": round(l_loss, 4),
            "accuracy": round(acc, 4),
            "roc_auc": round(auc, 4),
            "precision_at_k": round(prec_k, 4),
            "total_test_samples": len(y_true)
        }
