const API = "/api";
let currentContext = {};
let chatHistory   = [];

// ── TABS ──────────────────────────────────────────────────────
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"), p => p.classList.add("hidden"));
    btn.classList.add("active");
    const tabId = "tab-" + btn.dataset.tab;
    document.getElementById(tabId).classList.remove("hidden");
    document.getElementById(tabId).classList.add("active");
    if (btn.dataset.tab === "history")   loadHistory();
    if (btn.dataset.tab === "dashboard") loadDashboard();
  });
});

// ── PRÉDICTION ────────────────────────────────────────────────
document.getElementById("predictForm").addEventListener("submit", async e => {
  e.preventDefault();
  const btn = document.getElementById("btnPredict");
  const txt = document.getElementById("btnTxt");
  btn.disabled = true;
  txt.textContent = "⏳ Analyse en cours…";

  const form = new FormData(e.target);
  const body = {};
  form.forEach((v, k) => { body[k] = parseFloat(v); });

  try {
    const resp = await fetch(`${API}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await resp.json();
    if (data.error) { alert("Erreur : " + data.error); return; }
    currentContext = { ...data.prediction, ...body };
    chatHistory = [];
    renderResult(data);
    document.getElementById("resultCard").classList.remove("hidden");
    document.getElementById("resultCard").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alert("Erreur de connexion au serveur.");
  } finally {
    btn.disabled = false;
    txt.textContent = "🔍 Analyser le risque";
  }
});

function renderResult(data) {
  const { prediction: pred, analysis: anal } = data;
  const pct  = pred.risk_probability || 0;
  const lvl  = pred.risk_level || "";
  const risk = pred.is_at_risk;

  // Jauge circulaire
  const circumference = 2 * Math.PI * 50;
  const offset = circumference - (pct / 100) * circumference;
  const ring = document.getElementById("ringFill");
  ring.style.strokeDashoffset = offset;
  ring.style.stroke = risk ? (pct >= 70 ? "#C62828" : "#E65100") : "#2E7D32";
  document.getElementById("gaugePct").textContent = pct + "%";
  document.getElementById("gaugeLbl").textContent = lvl;

  // Badge résultat
  const badge = document.getElementById("predBadge");
  badge.textContent = risk ? "⚠️ " + pred.prediction : "✅ " + pred.prediction;
  badge.className = "pred-badge " + (risk ? (pct >= 70 ? "risk" : "medium") : "ok");

  // Listes
  renderList("listRisk", anal.facteurs_risque || []);
  renderList("listPos",  anal.facteurs_positifs || []);
  renderList("listReco", anal.recommandations || []);

  // Urgence
  const urg = document.getElementById("urgenceBox");
  const urgVal = (anal.urgence_consultation || "").toLowerCase();
  if (urgVal === "oui") {
    urg.textContent = "🚨 Consultation médicale urgente recommandée";
    urg.className = "urgence-box urgence-oui";
    urg.classList.remove("hidden");
  } else if (urgVal === "non") {
    urg.textContent = "✅ Pas de consultation urgente requise";
    urg.className = "urgence-box urgence-non";
    urg.classList.remove("hidden");
  } else {
    urg.textContent = "💡 Une consultation médicale est à envisager";
    urg.className = "urgence-box urgence-envisager";
    urg.classList.remove("hidden");
  }

  // Disclaimer
  document.getElementById("disclaimer").textContent = anal.disclaimer || "";

  // Reset chat
  document.getElementById("chatBox").innerHTML =
    `<div class="chat-msg ai">🩺 ${anal.resume || "Analyse disponible ci-dessus."}</div>`;
}

function renderList(id, items) {
  const ul = document.getElementById(id);
  ul.innerHTML = items.map(i => `<li>${i}</li>`).join("") || "<li>Aucun élément</li>";
}

// ── CHAT ──────────────────────────────────────────────────────
document.getElementById("btnSend").addEventListener("click", sendChat);
document.getElementById("chatInput").addEventListener("keydown", e => {
  if (e.key === "Enter") sendChat();
});

async function sendChat() {
  const input = document.getElementById("chatInput");
  const msg   = input.value.trim();
  if (!msg) return;
  input.value = "";

  const box = document.getElementById("chatBox");
  box.innerHTML += `<div class="chat-msg user">${escapeHtml(msg)}</div>`;
  box.scrollTop = box.scrollHeight;
  chatHistory.push({ role: "user", content: msg });

  try {
    const resp = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, context: currentContext, history: chatHistory })
    });
    const data = await resp.json();
    const reply = data.reply || "Désolé, je n'ai pas pu répondre.";
    chatHistory.push({ role: "assistant", content: reply });
    box.innerHTML += `<div class="chat-msg ai">${escapeHtml(reply)}</div>`;
    box.scrollTop = box.scrollHeight;
  } catch {
    box.innerHTML += `<div class="chat-msg ai">Erreur de connexion à l'agent IA.</div>`;
  }
}

// ── HISTORIQUE ────────────────────────────────────────────────
async function loadHistory() {
  const list = document.getElementById("historyList");
  list.innerHTML = "<p style='color:#8A95A8'>Chargement…</p>";
  try {
    const resp = await fetch(`${API}/history`);
    const preds = await resp.json();
    if (!preds.length) { list.innerHTML = "<p style='color:#8A95A8'>Aucune prédiction enregistrée.</p>"; return; }
    list.innerHTML = preds.map(p => `
      <div class="history-item">
        <div>
          <div class="h-name">👤 Âge ${p.age || "?"} ans — Glucose ${p.glucose || "?"} mg/dL — IMC ${p.bmi || "?"}</div>
          <div class="h-date">${new Date(p.created_at).toLocaleString("fr-FR")}</div>
        </div>
        <div class="h-badge ${p.is_at_risk ? 'risk' : 'ok'}">
          ${p.is_at_risk ? "⚠️ " : "✅ "}${p.risk_probability || "?"}% — ${p.risk_level || "?"}
        </div>
      </div>`).join("");
  } catch { list.innerHTML = "<p style='color:red'>Erreur de chargement.</p>"; }
}

// ── DASHBOARD ─────────────────────────────────────────────────
async function loadDashboard() {
  const grid = document.getElementById("statsGrid");
  grid.innerHTML = "<p style='color:#8A95A8;grid-column:1/-1'>Chargement…</p>";
  try {
    const resp  = await fetch(`${API}/stats`);
    const stats = await resp.json();
    grid.innerHTML = [
      { icon: "🩺", val: stats.total,          lbl: "Prédictions totales" },
      { icon: "⚠️", val: stats.at_risk,         lbl: "Patients à risque" },
      { icon: "✅", val: stats.not_at_risk,     lbl: "Pas de risque" },
      { icon: "📊", val: stats.avg_risk_pct+"%",lbl: "Risque moyen" },
      { icon: "🔬", val: stats.avg_glucose,     lbl: "Glucose moyen (mg/dL)" },
    ].map(s => `
      <div class="stat-card">
        <div class="stat-icon">${s.icon}</div>
        <div class="stat-val">${s.val}</div>
        <div class="stat-lbl">${s.lbl}</div>
      </div>`).join("");
  } catch { grid.innerHTML = "<p style='color:red'>Erreur de chargement.</p>"; }
}

function escapeHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
