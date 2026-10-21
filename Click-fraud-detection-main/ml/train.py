"""Offline model training; never called by the API process."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier

from backend.app.services.features import FEATURE_NAMES, training_features

ROOT = Path(__file__).resolve().parents[1]

def train(data_path: Path | str = ROOT / "data" / "dataset.csv", output_dir: Path | str = ROOT / "models") -> dict:
    source = Path(data_path)
    data = pd.read_csv(source)
    if "timestamp" in data:
        data = data.sort_values("timestamp")
    split = max(1, int(len(data) * .60))
    threshold_split = max(split + 1, int(len(data) * .75))
    test_split = max(threshold_split + 1, int(len(data) * .85))
    X = pd.DataFrame([training_features(row) for row in data.to_dict("records")], columns=FEATURE_NAMES)
    y = data["is_fraud"].astype(int).to_numpy()
    model = XGBClassifier(n_estimators=250, max_depth=4, learning_rate=.05,
        subsample=.85, colsample_bytree=.9, eval_metric="logloss", random_state=42,
        n_jobs=2, early_stopping_rounds=20)
    model.fit(X.iloc[:split], y[:split], eval_set=[(X.iloc[split:threshold_split], y[split:threshold_split])], verbose=False)
    threshold_x, threshold_y = X.iloc[threshold_split:test_split], y[threshold_split:test_split]
    threshold_probs = model.predict_proba(threshold_x)[:, 1]
    test_x, test_y = X.iloc[test_split:], y[test_split:]
    probs = model.predict_proba(test_x)[:, 1]
    fp_cost, fn_cost = float(os.getenv("C_FP", "1")), float(os.getenv("C_FN", "5"))
    candidates = np.linspace(.05, .95, 91)
    threshold = min(candidates, key=lambda t: fp_cost * np.sum((threshold_probs >= t) & (threshold_y == 0)) + fn_cost * np.sum((threshold_probs < t) & (threshold_y == 1)))
    pred = (probs >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(test_y, pred, labels=[0, 1]).ravel()
    metrics = {"precision": float(precision_score(test_y, pred, zero_division=0)),
        "recall": float(recall_score(test_y, pred, zero_division=0)), "f1": float(f1_score(test_y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(test_y, probs)), "pr_auc": float(average_precision_score(test_y, probs)),
        "fpr": float(fp / max(1, fp + tn)), "fnr": float(fn / max(1, fn + tp)),
        "threshold": float(threshold), "cost": float(fp_cost * fp + fn_cost * fn),
        "brier_score": float(brier_score_loss(test_y, probs))}
    for k in (10, 50, 100):
        take = min(k, len(test_y))
        top = np.argsort(probs)[-take:]
        metrics[f"precision_at_{k}"] = float(test_y[top].mean()) if take else 0.0
        metrics[f"recall_at_{k}"] = float(test_y[top].sum() / max(1, test_y.sum())) if take else 0.0
    baseline = (data.iloc[test_split:]["ip_click_count"].to_numpy() >= 50).astype(int)
    b_tn, b_fp, b_fn, b_tp = confusion_matrix(test_y, baseline, labels=[0, 1]).ravel()
    metrics["single_rule_baseline"] = {
        "threshold": "ip_click_count>=50",
        "precision": float(precision_score(test_y, baseline, zero_division=0)),
        "recall": float(recall_score(test_y, baseline, zero_division=0)),
        "cost": float(fp_cost * b_fp + fn_cost * b_fn),
    }
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model.save_model(out / "model.json")
    metadata = {"dataset": "synthetic", "data_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "git_revision": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or None,  # noqa: S607 - fixed git subcommand, no shell.
        "features": list(FEATURE_NAMES), "metrics": metrics, "params": model.get_params()}
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
    return metadata

if __name__ == "__main__":
    print(json.dumps(train(), indent=2))
