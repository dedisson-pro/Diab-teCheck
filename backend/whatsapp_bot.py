"""
DiabèteCheck — Agent WhatsApp (Twilio Sandbox)
Conversation guidée : pose 8 questions, prédit le risque, répond avec Groq AI.
"""
import os

# Sessions en mémoire : { numero_telephone: { "step": int, "data": dict } }
_sessions = {}

QUESTIONS = [
    {
        "key": "Pregnancies",
        "text": "🤰 *Combien de grossesses avez-vous eu ?*\n_(Répondez avec un nombre entier, ex: 2. Si homme: 0)_"
    },
    {
        "key": "Glucose",
        "text": "🩸 *Quel est votre taux de glucose (mg/dL) ?*\n_(Glycémie à jeun, ex: 120. Normal: 70-100 mg/dL)_"
    },
    {
        "key": "BloodPressure",
        "text": "💓 *Quelle est votre tension artérielle diastolique (mmHg) ?*\n_(Le 2ème chiffre ex: si 120/80 → répondez 80)_"
    },
    {
        "key": "SkinThickness",
        "text": "📏 *Quelle est l'épaisseur de votre pli cutané tricipital (mm) ?*\n_(Mesure médicale. Si inconnue, tapez: *0*)_"
    },
    {
        "key": "Insulin",
        "text": "💉 *Quel est votre taux d'insuline sérique (µU/mL) ?*\n_(Si inconnu, tapez: *0*)_"
    },
    {
        "key": "BMI",
        "text": "⚖️ *Quel est votre IMC (Indice de Masse Corporelle) ?*\n_(IMC = poids(kg) / taille(m)². Ex: 70kg / 1.75m² = 22.9)_"
    },
    {
        "key": "DiabetesPedigreeFunction",
        "text": "🧬 *Avez-vous des antécédents familiaux de diabète ?*\n• Tapez *1* → Oui, plusieurs membres\n• Tapez *2* → Oui, 1 membre\n• Tapez *3* → Non\n_(Cette valeur représente le risque génétique)_"
    },
    {
        "key": "Age",
        "text": "🎂 *Quel est votre âge ?*\n_(En années, ex: 35)_"
    },
]

PEDIGREE_MAP = {"1": 0.8, "2": 0.4, "3": 0.1}

WELCOME = (
    "👋 Bonjour ! Je suis *DiabèteCheck*, votre assistant IA de dépistage du diabète.\n\n"
    "Je vais vous poser *8 questions médicales* pour évaluer votre risque.\n"
    "⚠️ _Ce test est indicatif et ne remplace pas un avis médical._\n\n"
    "Tapez *GO* pour commencer, ou *AIDE* pour de l'aide."
)

HELP_TEXT = (
    "📋 *Commandes disponibles :*\n"
    "• *GO* → Démarrer le test\n"
    "• *RESET* → Recommencer\n"
    "• *STOP* → Arrêter\n\n"
    "Pour chaque question, répondez simplement avec un nombre.\n"
    "En cas de doute sur une valeur, tapez *0* (elle sera estimée)."
)


def _reset(phone: str):
    _sessions[phone] = {"step": 0, "data": {}}


def _validate_number(text: str, key: str):
    """Valide et convertit la valeur selon la variable."""
    text = text.strip().replace(",", ".")
    try:
        val = float(text)
    except ValueError:
        return None, "❌ Répondez avec un nombre (ex: 25.5)"

    if key == "Pregnancies":
        if val < 0 or val > 20:
            return None, "❌ Nombre de grossesses invalide (0-20)"
        return int(val), None
    elif key == "Glucose":
        if val < 0 or val > 500:
            return None, "❌ Glucose invalide (0-500 mg/dL)"
        return float(val), None
    elif key == "BloodPressure":
        if val < 0 or val > 200:
            return None, "❌ Tension invalide (0-200 mmHg)"
        return float(val), None
    elif key == "SkinThickness":
        if val < 0 or val > 100:
            return None, "❌ Valeur invalide (0-100 mm)"
        return float(val), None
    elif key == "Insulin":
        if val < 0 or val > 1000:
            return None, "❌ Insuline invalide (0-1000 µU/mL)"
        return float(val), None
    elif key == "BMI":
        if val < 0 or val > 70:
            return None, "❌ IMC invalide (0-70)"
        return float(val), None
    elif key == "DiabetesPedigreeFunction":
        mapped = PEDIGREE_MAP.get(text.strip())
        if mapped is None:
            return None, "❌ Répondez *1*, *2* ou *3*"
        return mapped, None
    elif key == "Age":
        if val < 1 or val > 120:
            return None, "❌ Âge invalide (1-120)"
        return int(val), None
    return float(val), None


def _format_result(result: dict, patient: dict) -> str:
    risk = result.get("risk_probability", 0)
    level = result.get("risk_level", "Inconnu")
    prediction = result.get("prediction", "")

    # Emoji selon le niveau
    if level == "Élevé":
        emoji = "🔴"
        conseil = "⚕️ *Consultez un médecin rapidement.* Votre profil indique un risque élevé de diabète."
    elif level == "Modéré":
        emoji = "🟡"
        conseil = "⚕️ *Consultez un médecin.* Adoptez une alimentation équilibrée et faites de l'exercice régulièrement."
    else:
        emoji = "🟢"
        conseil = "✅ *Continuez vos bonnes habitudes !* Maintenez une alimentation saine et restez actif."

    # Facteurs principaux
    importances = result.get("feature_importances", {})
    top = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:3]
    factors_names = {"Glucose": "Glucose", "BMI": "IMC", "Age": "Âge",
                     "Pregnancies": "Grossesses", "Insulin": "Insuline",
                     "BloodPressure": "Tension", "SkinThickness": "Pli cutané",
                     "DiabetesPedigreeFunction": "Antécédents familiaux"}
    factors_txt = "\n".join([f"  • {factors_names.get(k, k)}" for k, _ in top])

    return (
        f"{emoji} *Résultat DiabèteCheck*\n\n"
        f"📊 Risque de diabète : *{risk}%*\n"
        f"Niveau : *{level}* — _{prediction}_\n\n"
        f"🔍 *Facteurs principaux détectés :*\n{factors_txt}\n\n"
        f"{conseil}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🌐 Analyse complète : diabetecheck.onrender.com\n"
        f"_DiabèteCheck — IA de dépistage · Pas un diagnostic médical_"
    )


def handle_message(phone: str, message: str) -> str:
    """Point d'entrée principal : traite un message et retourne la réponse."""
    from model_service import predict_diabetes

    msg = message.strip()
    cmd = msg.upper()

    if cmd in ("AIDE", "HELP", "/HELP"):
        return HELP_TEXT

    if cmd in ("RESET", "RESTART", "/RESET"):
        _reset(phone)
        return "🔄 Session réinitialisée.\n\n" + WELCOME

    if cmd in ("STOP", "QUITTER", "FIN"):
        _sessions.pop(phone, None)
        return "👋 À bientôt ! Tapez *GO* pour refaire un test."

    # Nouvelle session ou message initial
    if phone not in _sessions or cmd in ("GO", "COMMENCER", "START", "/START"):
        _reset(phone)
        q = QUESTIONS[0]
        _sessions[phone]["step"] = 0
        return f"✅ Démarrage du test !\n\n*Question 1/8*\n\n{q['text']}"

    session = _sessions[phone]
    step = session["step"]

    if step >= len(QUESTIONS):
        return "✅ Test déjà terminé. Tapez *RESET* pour recommencer."

    # Valider la réponse à la question courante
    q = QUESTIONS[step]
    val, error = _validate_number(msg, q["key"])

    if error:
        return f"{error}\n\n*Question {step + 1}/8*\n\n{q['text']}"

    # Sauvegarder la valeur
    session["data"][q["key"]] = val
    session["step"] += 1

    # Si toutes les questions sont répondues
    if session["step"] == len(QUESTIONS):
        patient = session["data"]
        result = predict_diabetes(patient)

        if "error" in result:
            _sessions.pop(phone, None)
            return f"❌ Erreur lors de l'analyse : {result['error']}\nTapez *GO* pour réessayer."

        response = _format_result(result, patient)
        _sessions.pop(phone, None)
        return response

    # Prochaine question
    next_q = QUESTIONS[session["step"]]
    progress = f"*Question {session['step'] + 1}/8*"
    return f"✅ Noté !\n\n{progress}\n\n{next_q['text']}"
