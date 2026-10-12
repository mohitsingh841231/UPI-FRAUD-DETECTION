from app.model import train_model
import json

if __name__ == "__main__":
    result = train_model()
    print(json.dumps({k: v for k, v in result.items() if k != "classification_report"}, indent=2))
