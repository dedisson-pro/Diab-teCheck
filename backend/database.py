import os, sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "diabete.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pregnancies     REAL, glucose REAL, blood_pressure REAL,
            skin_thickness  REAL, insulin REAL, bmi REAL,
            dpf             REAL, age REAL,
            risk_probability REAL, risk_level TEXT, prediction TEXT,
            is_at_risk      INTEGER,
            ai_report       TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_prediction(data: dict) -> int:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO predictions
        (pregnancies, glucose, blood_pressure, skin_thickness, insulin,
         bmi, dpf, age, risk_probability, risk_level, prediction, is_at_risk, ai_report)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("Pregnancies"), data.get("Glucose"), data.get("BloodPressure"),
        data.get("SkinThickness"), data.get("Insulin"), data.get("BMI"),
        data.get("DiabetesPedigreeFunction"), data.get("Age"),
        data.get("risk_probability"), data.get("risk_level"),
        data.get("prediction"), int(data.get("is_at_risk", False)),
        data.get("ai_report")
    ))
    pred_id = cur.lastrowid
    conn.commit(); conn.close()
    return pred_id

def get_all_predictions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM predictions ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    at_risk = conn.execute("SELECT COUNT(*) FROM predictions WHERE is_at_risk=1").fetchone()[0]
    avg_risk = conn.execute("SELECT AVG(risk_probability) FROM predictions").fetchone()[0]
    avg_glucose = conn.execute("SELECT AVG(glucose) FROM predictions").fetchone()[0]
    conn.close()
    return {
        "total": total,
        "at_risk": at_risk,
        "not_at_risk": total - at_risk,
        "avg_risk_pct": round(avg_risk or 0, 1),
        "avg_glucose": round(avg_glucose or 0, 1)
    }
