from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(_env_path):
    with open(_env_path, encoding="utf-8-sig") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()

from model_service import predict_diabetes, get_features
from ai_agent import analyze_risk, chat_with_agent
from database import init_db, save_prediction, get_all_predictions, get_stats
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app, origins=os.getenv("ALLOWED_ORIGINS", "*"))
init_db()

# ── PRÉDICTION ───────────────────────────────────────────────
@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or {}
    features = get_features()
    patient = {}
    missing = []
    for feat in features:
        val = data.get(feat)
        if val is None:
            missing.append(feat)
        else:
            try:
                patient[feat] = float(val)
            except (ValueError, TypeError):
                return jsonify({"error": f"Valeur invalide pour {feat}"}), 400
    if missing:
        return jsonify({"error": f"Champs manquants : {', '.join(missing)}"}), 400

    try:
        result = predict_diabetes(patient)
        if "error" in result:
            return jsonify(result), 500

        ai_analysis = analyze_risk(result, patient)

        pred_id = save_prediction({**patient, **result, "ai_report": json.dumps(ai_analysis, ensure_ascii=False)})
        return jsonify({"pred_id": pred_id, "prediction": result, "analysis": ai_analysis})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

# ── CHAT IA ──────────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    history = data.get("history", [])
    context = data.get("context", {})
    if not message:
        return jsonify({"error": "Message manquant"}), 400
    return jsonify(chat_with_agent(message, context, history))

# ── HISTORIQUE ───────────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
def history():
    preds = get_all_predictions()
    for p in preds:
        try:
            p["ai_report"] = json.loads(p["ai_report"]) if p["ai_report"] else {}
        except (json.JSONDecodeError, TypeError):
            p["ai_report"] = {}
    return jsonify(preds)

# ── STATS ────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(get_stats())

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/<path:path>")
def serve_frontend(path):
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404
    full = os.path.join(FRONTEND_DIR, path)
    if os.path.isfile(full):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    print(f"🩺 DiabèteCheck démarré sur http://localhost:{port}")
    app.run(debug=False, host="0.0.0.0", port=port)
