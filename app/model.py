"""Training, evaluation, and persistence for the UPI fraud demo.

The held-out test set is used only for the final report. Logistic regression is
included as a transparent baseline; the configured random forest is the model
served by Flask. Metrics describe this dataset/split and are not a guarantee of
production performance.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import tempfile

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, brier_score_loss,
    classification_report, confusion_matrix, f1_score, matthews_corrcoef,
    precision_recall_curve, precision_score, recall_score, roc_auc_score,
    average_precision_score, roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "archive" / "dataset.csv"
MODEL_PATH = ROOT / "app" / "fraud_model.joblib"
OUTPUT_DIR = ROOT / "artifacts"
TARGET = "is_fraud"
DROP_COLUMNS = ["transaction id", "timestamp", "sender_upi_id", "receiver_upi_id"]
RANDOM_STATE = 42
TEST_SIZE = 0.20
THRESHOLD = 0.50


def _validate_dataset(df: pd.DataFrame) -> None:
    """Fail early on schema/label errors that would make metrics misleading."""
    if df.empty:
        raise ValueError("The dataset contains no transaction rows.")
    if TARGET not in df.columns:
        raise ValueError(f"Dataset must contain target column {TARGET!r}.")
    if df[TARGET].isna().any():
        raise ValueError(f"Target column {TARGET!r} contains missing labels.")
    labels = set(pd.to_numeric(df[TARGET], errors="raise").unique())
    if not labels.issubset({0, 1}) or labels != {0, 1}:
        raise ValueError(f"Target must contain both binary labels 0 and 1; found {labels}.")
    feature_columns = [c for c in df.columns if c not in [TARGET, *DROP_COLUMNS]]
    if not feature_columns:
        raise ValueError("No usable feature columns remain after identifier removal.")


def _make_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    numeric = X.select_dtypes(include="number").columns.tolist()
    categorical = [c for c in X.columns if c not in numeric]
    transformers = []
    if numeric:
        transformers.append(("numeric", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric))
    if categorical:
        transformers.append(("categorical", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical))
    return ColumnTransformer(transformers, remainder="drop")


def _pipeline(prep: ColumnTransformer, estimator) -> Pipeline:
    # Each candidate receives its own transformer because fitting mutates it.
    import copy
    return Pipeline([("prep", copy.deepcopy(prep)), ("classifier", estimator)])


def _scores(y_true, prediction, probability) -> dict:
    cm = confusion_matrix(y_true, prediction, labels=[0, 1])
    tn, fp, fn, tp = (int(v) for v in cm.ravel())
    return {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, prediction)),
        "precision": float(precision_score(y_true, prediction, zero_division=0)),
        "recall": float(recall_score(y_true, prediction, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else 0.0,
        "f1": float(f1_score(y_true, prediction, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probability)),
        "average_precision": float(average_precision_score(y_true, probability)),
        "matthews_corrcoef": float(matthews_corrcoef(y_true, prediction)),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "confusion_matrix": cm.tolist(),
        "classification_report": classification_report(
            y_true, prediction, labels=[0, 1], target_names=["legitimate", "fraud"],
            output_dict=True, zero_division=0),
        "support": {"legitimate": tn + fp, "fraud": fn + tp},
        "errors": {"false_positives": fp, "false_negatives": fn},
    }


def _save_artifacts(metrics: dict, y_test, probability, prediction, pipeline,
                    output_dir: Path = OUTPUT_DIR) -> None:
    """Write reusable, machine-readable results and publication-friendly plots."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    pd.DataFrame(metrics["classification_report"]).T.to_csv(
        output_dir / "classification_report.csv", index=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import ConfusionMatrixDisplay, PrecisionRecallDisplay, RocCurveDisplay

        print("Writing confusion-matrix plot…", flush=True)
        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        ConfusionMatrixDisplay(np.asarray(metrics["confusion_matrix"]), display_labels=["Legitimate", "Fraud"]).plot(
            ax=ax, cmap="Greens", colorbar=False, values_format="d")
        ax.set_title("Held-out test confusion matrix")
        fig.tight_layout(); fig.savefig(output_dir / "confusion_matrix.png", dpi=180); plt.close(fig)

        print("Writing ROC plot…", flush=True)
        curve_fpr, curve_tpr, _ = roc_curve(y_test, probability)
        curve_indexes = np.linspace(0, len(curve_fpr) - 1, min(4000, len(curve_fpr))).astype(int)
        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        ax.plot(curve_fpr[curve_indexes], curve_tpr[curve_indexes], label="Selected model")
        ax.plot([0, 1], [0, 1], linestyle="--", color="grey", label="Chance")
        ax.set_title(f"ROC curve (AUC {metrics['roc_auc']:.3f})"); ax.legend()
        fig.tight_layout(); fig.savefig(output_dir / "roc_curve.png", dpi=180); plt.close(fig)

        print("Writing precision-recall plot…", flush=True)
        curve_precision, curve_recall, _ = precision_recall_curve(y_test, probability)
        curve_indexes = np.linspace(0, len(curve_recall) - 1, min(4000, len(curve_recall))).astype(int)
        fig, ax = plt.subplots(figsize=(5.5, 4.5))
        ax.plot(curve_recall[curve_indexes], curve_precision[curve_indexes])
        ax.axhline(np.mean(y_test), linestyle="--", color="grey", label="Positive-class prevalence")
        ax.set(xlabel="Recall", ylabel="Precision", xlim=(0, 1), ylim=(0, 1))
        ax.legend()
        ax.set_title(f"Precision-recall curve (AP {metrics['average_precision']:.3f})")
        fig.tight_layout(); fig.savefig(output_dir / "precision_recall_curve.png", dpi=180); plt.close(fig)

        classifier = pipeline.named_steps["classifier"]
        transformed_names = pipeline.named_steps["prep"].get_feature_names_out()
        if hasattr(classifier, "feature_importances_"):
            importances = pd.DataFrame({"feature": transformed_names,
                                        "importance": classifier.feature_importances_})
            clean_names = importances.feature.str.replace(r"^(numeric|categorical)__", "", regex=True)
            original_names = sorted(metrics["features"], key=len, reverse=True)
            importances["source_feature"] = clean_names.map(
                lambda transformed: next((name for name in original_names
                                           if transformed == name or transformed.startswith(name + "_")),
                                         transformed))
            importances = importances.groupby("source_feature", as_index=False).importance.sum()
            importances.sort_values("importance", ascending=False).to_csv(
                output_dir / "feature_importance.csv", index=False)
            top = importances.head(12).sort_values("importance")
            fig, ax = plt.subplots(figsize=(7, 5))
            ax.barh(top.source_feature, top.importance, color="#287454")
            ax.set_title("Random-forest impurity importance (grouped by source field)")
            ax.set_xlabel("Importance; descriptive, not causal")
            fig.tight_layout(); fig.savefig(output_dir / "feature_importance.png", dpi=180); plt.close(fig)
    except ImportError:
        # Core model training should still work if optional plotting packages
        # have not yet been installed; JSON/CSV evaluation is always produced.
        pass


def train_model(data_path=DATA_PATH, model_path=MODEL_PATH,
                excluded_features=(), artifact_dir=OUTPUT_DIR):
    """Train, compare to a simple baseline, evaluate once, and persist results.

    The 20% stratified test partition remains untouched during fitting. Model
    selection between the two candidates uses a separate validation partition
    drawn from the remaining 80%; the final test score is never used to choose
    which estimator is deployed.
    """
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset not found: {data_path}")
    df = pd.read_csv(data_path)
    _validate_dataset(df)
    y = pd.to_numeric(df[TARGET], errors="raise").astype(int)
    X = df.drop(columns=[TARGET] + [c for c in DROP_COLUMNS if c in df.columns])
    excluded_features = list(excluded_features)
    unknown_exclusions = sorted(set(excluded_features) - set(X.columns))
    if unknown_exclusions:
        raise ValueError(f"Cannot exclude unknown feature columns: {unknown_exclusions}")
    X = X.drop(columns=excluded_features)
    if X.shape[1] == 0:
        raise ValueError("At least one model feature must remain after feature ablation.")
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y)
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.1875,
        random_state=RANDOM_STATE, stratify=y_train_val)
    # 0.1875 of the 80% development split gives a 65/15/20 train/validation/test split.
    prep = _make_preprocessor(X)
    candidates = {
        "logistic_regression": _pipeline(prep, LogisticRegression(
            max_iter=1000, class_weight="balanced", solver="lbfgs", random_state=RANDOM_STATE)),
        "random_forest": _pipeline(prep, RandomForestClassifier(
            n_estimators=150, max_depth=20, min_samples_leaf=2,
            class_weight="balanced_subsample", random_state=RANDOM_STATE,
            n_jobs=max(1, min(4, os.cpu_count() or 1)))),
    }
    validation = {}
    for name, candidate in candidates.items():
        print(f"Fitting {name.replace('_', ' ')} on {len(X_train):,} training rows…", flush=True)
        candidate.fit(X_train, y_train)
        validation[name] = float(roc_auc_score(y_val, candidate.predict_proba(X_val)[:, 1]))
        print(f"  validation ROC AUC: {validation[name]:.4f}", flush=True)
    selected_name = max(validation, key=validation.get)
    selected_estimator = candidates[selected_name].named_steps["classifier"]
    deployed = _pipeline(prep, selected_estimator)
    X_development = pd.concat([X_train, X_val], axis=0)
    y_development = pd.concat([y_train, y_val], axis=0)
    deployed.fit(X_development, y_development)
    probability = deployed.predict_proba(X_test)[:, 1]
    prediction = (probability >= THRESHOLD).astype(int)
    metrics = _scores(y_test, prediction, probability)
    metrics.update({
        "threshold": THRESHOLD,
        "selected_model": selected_name,
        "selection_metric": "validation_roc_auc",
        "model_config": {
            "logistic_regression": {"max_iter": 1000, "class_weight": "balanced", "solver": "lbfgs"},
            "random_forest": {"n_estimators": 150, "max_depth": 20, "min_samples_leaf": 2,
                              "class_weight": "balanced_subsample"},
        },
        "validation_roc_auc": validation,
        "test_rows": int(len(y_test)),
        "train_rows": int(len(X_development)),
        "validation_rows": int(len(X_val)),
        "dataset_rows": int(len(df)),
        "fraud_rate": float(y.mean()),
        "features": X.columns.tolist(),
        "excluded_columns": [c for c in DROP_COLUMNS if c in df.columns],
        "feature_ablation": excluded_features,
        "random_state": RANDOM_STATE,
        "split": {"train": 0.65, "validation": 0.15, "test": 0.20, "stratified": True},
        "software": {"scikit_learn": sklearn.__version__, "pandas": pd.__version__},
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "risk_score_caveat": (
            "Confirm risk_score is available before the fraud decision and is not derived from target labels. "
            "Its provenance is not documented in the supplied dataset."),
    })
    bundle = {"model": deployed, "features": X.columns.tolist(), "metrics": metrics,
              "target": TARGET, "threshold": THRESHOLD}
    if model_path is not None:
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replacement avoids leaving a partially-written model on interruption.
        with tempfile.NamedTemporaryFile(dir=model_path.parent, suffix=".tmp", delete=False) as tmp:
            temporary_path = Path(tmp.name)
        try:
            joblib.dump(bundle, temporary_path)
            temporary_path.replace(model_path)
        finally:
            temporary_path.unlink(missing_ok=True)
    _save_artifacts(metrics, y_test, probability, prediction, deployed, Path(artifact_dir))
    return metrics


def load_model(path=MODEL_PATH):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError("Model is not trained yet. Run `python train.py` first.")
    return joblib.load(path)
