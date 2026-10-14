from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.model import OUTPUT_DIR, load_model

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

@app.get("/api/health")
def api_health():
    try:
        bundle = load_model()
        return jsonify({"status": "ready", "model": bundle["metrics"].get("selected_model")})
    except FileNotFoundError:
        return jsonify({"status": "model_not_trained"}), 503

@app.get("/artifacts/<name>")
def report_artifact(name):
    allowed = {"confusion_matrix.png", "roc_curve.png", "precision_recall_curve.png",
               "feature_importance.png"}
    if name not in allowed:
        abort(404)
    return send_from_directory(OUTPUT_DIR, name)

@app.post("/api/predict")
def predict():
    try:
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Send a JSON object containing transaction features."}), 400
        bundle = load_model()
        features = bundle["features"]
        missing = [feature for feature in features if feature not in payload or payload[feature] is None]
        if missing:
            return jsonify({"error": "Missing required features.", "missing_features": missing}), 400
        row = {feature: payload[feature] for feature in features}
        import pandas as pd
        probability = float(bundle["model"].predict_proba(pd.DataFrame([row]))[0, 1])
        threshold = float(bundle.get("threshold", bundle["metrics"].get("threshold", 0.5)))
        predicted = int(probability >= threshold)
        return jsonify({"fraud_probability": probability,
                        "threshold": threshold,
                        "prediction": predicted,
                        "label": "Potential fraud" if predicted else "Likely legitimate",
                        "notice": "Demonstration estimate; not a calibrated guarantee or payment decision."})
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 503
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid feature values: {exc}"}), 400

if __name__ == "__main__":
    app.run(debug=False, port=5000)
