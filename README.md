# UPI Fraud Detection

Jupyter notebook, scikit-learn training pipeline, and Flask website for the supplied `archive/dataset.csv` dataset (250,000 rows).

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Train and evaluate

Open `UPI_Fraud_Detection.ipynb` in Jupyter and run all cells, or run:

```powershell
python train.py
```

Training uses an 80/20 stratified train/test split. The trained model and test metrics are saved to `app/fraud_model.joblib`. The confusion matrix is arranged as `[[true negatives, false positives], [false negatives, true positives]]`.

## Start the Flask website

```powershell
python -m app.server
```

Visit http://127.0.0.1:5000. The site displays accuracy, precision, recall, ROC AUC, and the confusion matrix, and includes a transaction scoring form. JSON endpoints are `GET /api/metrics` and `POST /api/predict`.

## Notes

Transaction IDs, timestamps, and sender/receiver UPI IDs are excluded from model features. The dataset's `risk_score` remains a feature; assess whether it is available at decision time and independently validated before operational use. Accuracy alone can be misleading on imbalanced fraud data, so review precision, recall, F1, ROC AUC, and the confusion matrix. This is a demonstration and should not be used alone to make real payment decisions.
