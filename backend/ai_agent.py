import os
from groq import Groq

_client = None

def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client

def _model() -> str:
    return os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

SYSTEM_PROMPT = """Tu es DiabèteCheck, un assistant médical de prévention du diabète.
Tu analyses les résultats d'un modèle de prédiction et fournis des conseils personnalisés
en français. Tu es précis, bienveillant et rappelles toujours que tes conseils
ne remplacent pas un médecin. Ne dépasse jamais les faits cliniques établis."""


def analyze_risk(prediction: dict, patient: dict) -> dict:
    risk_pct  = prediction.get("risk_probability", 0)
    risk_lvl  = prediction.get("risk_level", "Inconnu")
    is_risk   = prediction.get("is_at_risk", False)

    prompt = f"""Le modèle ML a prédit :
- Probabilité de diabète : {risk_pct}%
- Niveau de risque : {risk_lvl}
- Résultat : {"⚠️ Risque détecté" if is_risk else "✅ Pas de risque significatif"}

Données patient :
- Âge : {patient.get('Age')} ans
- Glucose : {patient.get('Glucose')} mg/dL
- IMC : {patient.get('BMI')}
- Pression artérielle : {patient.get('BloodPressure')} mm Hg
- Insuline : {patient.get('Insulin')} µU/mL
- Grossesses : {patient.get('Pregnancies')}

Génère un rapport médical structuré au format JSON :
{{
  "resume": "Résumé en 1 phrase du résultat",
  "facteurs_risque": ["facteur 1", "facteur 2"],
  "facteurs_positifs": ["point positif 1"],
  "recommandations": ["conseil 1", "conseil 2", "conseil 3"],
  "urgence_consultation": "Oui/Non/À envisager",
  "disclaimer": "Message de prudence médical"
}}"""

    try:
        resp = _get_client().chat.completions.create(
            model=_model(),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.3, max_tokens=800
        )
        content = resp.choices[0].message.content.strip()
        # Nettoyage markdown
        if "```" in content:
            for part in content.split("```"):
                p = part.strip()
                if p.startswith("json"): p = p[4:].strip()
                if p.startswith("{"): content = p; break
        start = content.find("{"); end = content.rfind("}") + 1
        import json
        return json.loads(content[start:end])
    except Exception as e:
        return {
            "resume": "Analyse IA indisponible",
            "facteurs_risque": [], "facteurs_positifs": [],
            "recommandations": ["Consultez un médecin pour une évaluation complète."],
            "urgence_consultation": "À envisager",
            "disclaimer": f"Erreur IA : {e}"
        }


def chat_with_agent(user_message: str, context: dict, history: list) -> dict:
    ctx = ""
    if context:
        ctx = (f"\nContexte patient — Risque : {context.get('risk_probability','?')}%, "
               f"Niveau : {context.get('risk_level','?')}, "
               f"Glucose : {context.get('Glucose','?')}, IMC : {context.get('BMI','?')}\n")

    messages = [{"role": "system", "content": SYSTEM_PROMPT + ctx}]
    for msg in history[-6:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_message})

    try:
        resp = _get_client().chat.completions.create(
            model=_model(), messages=messages,
            temperature=0.5, max_tokens=600
        )
        reply = resp.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        return {"reply": f"Désolé, je ne peux pas répondre pour l'instant : {e}"}
