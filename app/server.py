from flask import Flask, jsonify, render_template, request
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.model import load_model

app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))

@app.get("/")
def home():
    try:
        metrics = load_model()["metrics"]
    except FileNotFoundError:
        metrics = None
    return render_template("index.html", metrics=metrics)

@app.get("/api/metrics")
def api_metrics():
    try:
        return jsonify(load_model()["metrics"])
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 503

@app.post("/api/predict")
def predict():
    try:
        payload = request.get_json(force=True)
        bundle = load_model()
        row = {feature: payload.get(feature) for feature in bundle["features"]}
        import pandas as pd
        probability = float(bundle["model"].predict_proba(pd.DataFrame([row]))[0, 1])
        return jsonify({"fraud_probability": probability,
                        "prediction": int(probability >= 0.5),
                        "label": "Potential fraud" if probability >= 0.5 else "Likely legitimate"})
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400

if __name__ == "__main__":
    app.run(debug=False, port=5000)
