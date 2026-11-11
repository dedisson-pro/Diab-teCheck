import os, json
import numpy as np
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "../models")

_model  = None
_scaler = None
_features = None

def _load():
    global _model, _scaler, _features
    if _model is None:
        model_path  = os.path.join(MODELS_DIR, "model.pkl")
        scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")
        feat_path   = os.path.join(MODELS_DIR, "features.json")
        if not os.path.exists(model_path):
            raise FileNotFoundError("model.pkl introuvable — exécute le notebook d'abord !")
        _model   = joblib.load(model_path)
        _scaler  = joblib.load(scaler_path)
        with open(feat_path) as f:
            _features = json.load(f)

def get_features():
    _load()
    return _features

def predict_diabetes(patient: dict) -> dict:
    try:
        _load()
        X = np.array([[patient[f] for f in _features]])
        X_sc = _scaler.transform(X)
        proba = _model.predict_proba(X_sc)[0]
        risk_pct = round(float(proba[1]) * 100, 1)
        prediction = "Risque détecté" if proba[1] >= 0.5 else "Pas de risque significatif"
        risk_level = (
            "Élevé"  if risk_pct >= 70 else
            "Modéré" if risk_pct >= 40 else
            "Faible"
        )
        # Feature importances pour l'explication
        importances = {}
        if hasattr(_model, "feature_importances_"):
            for feat, imp in zip(_features, _model.feature_importances_):
                importances[feat] = round(float(imp), 4)

        return {
            "risk_probability": risk_pct,
            "prediction": prediction,
            "risk_level": risk_level,
            "is_at_risk": bool(proba[1] >= 0.5),
            "feature_importances": importances
        }
    except Exception as e:
        return {"error": str(e)}
