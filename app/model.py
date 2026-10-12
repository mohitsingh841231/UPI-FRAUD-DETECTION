"""Train and load the UPI fraud classifier."""
from pathlib import Path
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, roc_auc_score, confusion_matrix,
                             classification_report)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "archive" / "dataset.csv"
MODEL_PATH = ROOT / "app" / "fraud_model.joblib"
TARGET = "is_fraud"
# Identifiers and timestamp strings are excluded to avoid memorizing identities.
DROP_COLUMNS = ["transaction id", "timestamp", "sender_upi_id", "receiver_upi_id"]

def train_model(data_path=DATA_PATH, model_path=MODEL_PATH):
    df = pd.read_csv(data_path)
    if TARGET not in df:
        raise ValueError(f"Dataset must contain target column {TARGET!r}")
    y = pd.to_numeric(df[TARGET], errors="raise").astype(int)
    X = df.drop(columns=[TARGET] + [c for c in DROP_COLUMNS if c in df.columns])
    numeric = X.select_dtypes(include="number").columns.tolist()
    categorical = [c for c in X.columns if c not in numeric]
    prep = ColumnTransformer([
        ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("categorical", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    model = Pipeline([("prep", prep), ("classifier", RandomForestClassifier(
        n_estimators=100, max_depth=20, min_samples_leaf=2,
        class_weight="balanced_subsample", random_state=42, n_jobs=4))])
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]
    metrics = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, prob)),
        "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        "classification_report": classification_report(y_test, pred, output_dict=True, zero_division=0),
        "test_rows": int(len(y_test)), "fraud_rate": float(y.mean()),
        "features": X.columns.tolist(),
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": X.columns.tolist(), "metrics": metrics}, model_path)
    return metrics

def load_model(path=MODEL_PATH):
    if not Path(path).exists():
        raise FileNotFoundError("Model is not trained yet. Run the notebook or python train.py first.")
    return joblib.load(path)
