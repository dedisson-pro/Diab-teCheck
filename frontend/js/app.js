const API = "/api";
let currentContext = {};
let chatHistory   = [];

// ── ICÔNES SVG ────────────────────────────────────────────────
const IC = {
  pulse:  '<svg class="ic" aria-hidden="true"><use href="#ic-pulse"/></svg>',
  search: '<svg class="ic" aria-hidden="true"><use href="#ic-search"/></svg>',
  chart:  '<svg class="ic" aria-hidden="true"><use href="#ic-chart"/></svg>',
  check:  '<svg class="ic" aria-hidden="true"><use href="#ic-check"/></svg>',
  bulb:   '<svg class="ic" aria-hidden="true"><use href="#ic-bulb"/></svg>',
  alert:  '<svg class="ic" aria-hidden="true"><use href="#ic-alert"/></svg>',
  hist:   '<svg class="ic" aria-hidden="true"><use href="#ic-history"/></svg>',
  dash:   '<svg class="ic" aria-hidden="true"><use href="#ic-dashboard"/></svg>',
};

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
  txt.innerHTML = '<span style="opacity:.7">Analyse en cours…</span>';

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
    txt.innerHTML = IC.search + " Analyser le risque";
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
  badge.innerHTML = risk
    ? IC.alert + " " + escapeHtml(pred.prediction)
    : IC.check + " " + escapeHtml(pred.prediction);
  badge.className = "pred-badge " + (risk ? (pct >= 70 ? "risk" : "medium") : "ok");

  // Listes
  renderList("listRisk", anal.facteurs_risque || []);
  renderList("listPos",  anal.facteurs_positifs || []);
  renderList("listReco", anal.recommandations || []);

  // Urgence
  const urg = document.getElementById("urgenceBox");
  const urgVal = (anal.urgence_consultation || "").toLowerCase();
  if (urgVal === "oui") {
    urg.innerHTML = IC.alert + " Consultation médicale urgente recommandée";
    urg.className = "urgence-box urgence-oui";
    urg.classList.remove("hidden");
  } else if (urgVal === "non") {
    urg.innerHTML = IC.check + " Pas de consultation urgente requise";
    urg.className = "urgence-box urgence-non";
    urg.classList.remove("hidden");
  } else {
    urg.innerHTML = IC.bulb + " Une consultation médicale est à envisager";
    urg.className = "urgence-box urgence-envisager";
    urg.classList.remove("hidden");
  }

  // Disclaimer
  document.getElementById("disclaimer").textContent = anal.disclaimer || "";

  // Reset chat
  document.getElementById("chatBox").innerHTML =
    `<div class="chat-msg ai">${IC.pulse} ${escapeHtml(anal.resume || "Analyse disponible ci-dessus.")}</div>`;
}

function renderList(id, items) {
  const ul = document.getElementById(id);
  ul.innerHTML = items.map(i => `<li>${escapeHtml(i)}</li>`).join("") || "<li>Aucun élément</li>";
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
    box.innerHTML += `<div class="chat-msg ai">${formatReply(reply)}</div>`;
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
          <div class="h-name">Âge ${p.age || "?"} ans &mdash; Glucose ${p.glucose || "?"} mg/dL &mdash; IMC ${p.bmi || "?"}</div>
          <div class="h-date">${new Date(p.created_at).toLocaleString("fr-FR")}</div>
        </div>
        <div class="h-badge ${p.is_at_risk ? 'risk' : 'ok'}">
          ${p.is_at_risk ? IC.alert : IC.check}${escapeHtml(String(p.risk_probability || "?"))}% &mdash; ${escapeHtml(p.risk_level || "?")}
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
      { icon: IC.pulse, val: stats.total,           lbl: "Prédictions totales" },
      { icon: IC.alert, val: stats.at_risk,          lbl: "Patients à risque" },
      { icon: IC.check, val: stats.not_at_risk,      lbl: "Pas de risque" },
      { icon: IC.chart, val: (stats.avg_risk_pct||0)+"%", lbl: "Risque moyen" },
      { icon: IC.search, val: stats.avg_glucose,     lbl: "Glucose moyen (mg/dL)" },
    ].map(s => `
      <div class="stat-card">
        <div class="stat-icon">${s.icon}</div>
        <div class="stat-val">${s.val}</div>
        <div class="stat-lbl">${s.lbl}</div>
      </div>`).join("");
  } catch { grid.innerHTML = "<p style='color:red'>Erreur de chargement.</p>"; }
}

function escapeHtml(str) {
  return String(str).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

// Le texte est échappé avant toute mise en forme : seules nos propres balises sont insérées.
function formatReply(str) {
  return escapeHtml(str)
    .replace(/^#{1,6}\s*(.+)$/gm, "<strong>$1</strong>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^\s*[*-]\s+/gm, "• ")
    .replace(/\*(\S[^*\n]*?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br>");
}
