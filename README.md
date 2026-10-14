# UPI Fraud Detection

A complete learning project with a Jupyter analysis notebook, reproducible model training, hold-out evaluation, a Flask API, and a browser-based demo. The application is for education and experimentation; it is not a payment authorization or fraud operations system.

## Project contents

```text
upi_fraud_detection.ipynb   Data inspection, training, evaluation, visualizations
archive/dataset.csv        Supplied labeled transaction dataset
app/model.py               Validation, preprocessing, model comparison, evaluation, saving
app/server.py              Flask website and JSON endpoints
templates/index.html       Metrics dashboard and transaction form
static/                    Website styles, script, and generated styles
artifacts/                 Metrics, class report, and training diagnostic plots
train.py                   Command-line training entry point
requirements.txt           Python packages
```

## Install and prepare

Use Python 3.10 or newer. In PowerShell, from the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Keep the supplied file at `archive/dataset.csv`. The target column must be `is_fraud` with both classes encoded as 0 (legitimate) and 1 (fraud). Training stops with a clear error if the file or target is invalid.

## Train and evaluate

Run the full pipeline from a terminal:

```powershell
python train.py
```

Or open `upi_fraud_detection.ipynb` in Jupyter and run its cells in order. The pipeline:

1. Removes transaction IDs, timestamp strings, and sender/receiver UPI IDs from the input features.
2. Makes fixed-seed, stratified train/validation/test partitions (65%/15%/20%).
3. Learns missing-value handling and categorical encoding inside the training pipelines to avoid fitting preprocessing on held-out rows.
4. Compares a balanced logistic-regression baseline with a class-balanced random forest using validation ROC AUC. The random forest uses 150 trees, depth 20, minimum leaf size 2, and a fixed seed.
5. Refits the validation-selected candidate on the combined training and validation rows, then evaluates once on the untouched test rows using a 0.50 decision threshold.
6. Saves the fitted pipeline, feature schema, threshold, model metadata, and test results.

The notebook also retrains two controlled feature-ablation experiments on the same fixed partitions: without `risk_score`, and without both `risk_score` and `amount (INR)`. Each experiment writes to its own folder under `artifacts/feature_ablations/`; neither overwrites the model used by the Flask demo. This quantifies dependence on highly associated fields, but does not by itself prove target leakage.

The comparison is intentionally small and is not an exhaustive hyperparameter search. Accuracy, precision, recall, specificity, F1, balanced accuracy, ROC AUC, average precision, Matthews correlation coefficient, Brier score, class-level report, and confusion matrix are reported. Confusion-matrix order is `[[true negatives, false positives], [false negatives, true positives]]`.

Generated outputs:

- `app/fraud_model.joblib` — fitted pipeline and metadata (ignored by Git; regenerate with training).
- `artifacts/metrics.json` and `artifacts/classification_report.csv` — evaluation results.
- `artifacts/confusion_matrix.png`, `artifacts/roc_curve.png`, `artifacts/precision_recall_curve.png`, and `artifacts/feature_importance.png` — plots shown on the site.
- `artifacts/feature_importance.csv` — grouped random-forest impurity importance when that model is selected.

## Start the website

Train the model first, then:

```powershell
python -m app.server
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000). The dashboard shows final test performance, validation candidate scores, diagnostic plots, and the transaction scoring form. Stop the local server with Ctrl+C.

## API

- `GET /api/health` — readiness and selected estimator.
- `GET /api/metrics` — saved evaluation report (`503` if the model has not been trained).
- `POST /api/predict` — requires a JSON object with every feature shown in the notebook/model bundle. Returns the positive-class score, applied threshold, and predicted class. Invalid JSON, missing values, and invalid input receive client errors.

Example request fields (the values are illustrative):

```json
{
  "transaction type": "P2P", "merchant_category": "Grocery", "amount (INR)": 1250,
  "transaction_status": "SUCCESS", "sender_age_group": "26-35", "receiver_age_group": "18-25",
  "sender_state": "Delhi", "sender_bank": "SBI", "receiver_bank": "HDFC",
  "device_type": "Android", "network_type": "4G", "hour_of_day": 12,
  "day_of_week": "Monday", "is_weekend": 0, "risk_score": 250
}
```

## Interpretation and limits

Metrics are conditional on the supplied labels, feature definitions, and one fixed split. Similar fraud prevalence in a test split does not establish performance under real-world class imbalance or changing transaction behavior. The provenance of `risk_score` is undocumented; confirm it is available before a decision and not derived from the target or post-transaction investigation. Model scores are not calibrated guarantees. A production evaluation would need verified label provenance, leakage review, time- and entity-based hold-outs, threshold/cost analysis, calibration, monitoring, privacy/security review, and human oversight.

