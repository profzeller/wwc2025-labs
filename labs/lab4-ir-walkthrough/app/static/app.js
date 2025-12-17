const STORAGE_KEY = "wwc2025_lab4_ir_evidence_v2";

let pendingActionId = null;

document.addEventListener("DOMContentLoaded", () => {
  const dataEl = document.getElementById("lab4Data");
  if (!dataEl) return;

  let parsed = null;
  try {
    parsed = JSON.parse(dataEl.textContent || "{}");
  } catch {
    parsed = null;
  }
  if (!parsed || !parsed.incident) return;

  window.LAB4 = parsed;
  lab4Init();
});

function lab4Init() {
  const inc = window.LAB4?.incident;
  if (!inc) return;

  const state = loadState();

  if (!state.evidence) state.evidence = {};
  for (const ev of inc.evidence) {
    if (!state.evidence[ev.id]) state.evidence[ev.id] = "available";
  }

  if (!Array.isArray(state.actions_taken)) state.actions_taken = [];
  if (!state.notes) state.notes = { what:"", when:"", actions:"", status:"", escalate:"", escalateWhy:"" };

  saveState(state);

  renderActions();
  renderEvidence();
  renderSummaryAndTokens();
  restoreNotes();
  updateStepper();
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return (parsed && typeof parsed === "object") ? parsed : {};
  } catch {
    return {};
  }
}

function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function lab4Reset() {
  localStorage.removeItem(STORAGE_KEY);
  location.reload();
}

function lab4GoTo(which) {
  const map = {
    actions: "actionsPanel",
    record: "recordPanel",
    escalate: "escalatePanel"
  };
  const id = map[which];
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderActions() {
  const inc = window.LAB4.incident;
  const state = loadState();
  const max = inc.rules.max_first_actions;
  const takenSet = new Set(state.actions_taken || []);

  const list = document.getElementById("actionList");
  if (!list) return;

  const html = inc.actions.map(a => {
    const taken = takenSet.has(a.id);
    const disabledTake = (!taken && (state.actions_taken || []).length >= max);

    const preserveBadges = (a.preserves || []).map(x =>
      `<span class="badge badge-preserve">Preserve: ${escapeHtml(labelForEvidence(x))}</span>`
    ).join("");

    const destroyBadges = (a.destroys || []).map(x =>
      `<span class="badge badge-destroy">May lose: ${escapeHtml(labelForEvidence(x))}</span>`
    ).join("");

    const riskBadges = (a.risks || []).map(x =>
      `<span class="badge badge-risk">${escapeHtml(x)}</span>`
    ).join("");

    return `
      <div class="action-item" id="action-${a.id}">
        <div class="action-top">
          <div class="action-title">${escapeHtml(a.title)}</div>
          <span class="tag">${escapeHtml(a.phase)}</span>
        </div>
        <div class="action-desc">${escapeHtml(a.description)}</div>

        <div class="action-effects">
          ${preserveBadges}
          ${destroyBadges}
          ${riskBadges}
        </div>

        <div class="action-btns">
          <button class="btn" type="button" onclick="previewAction('${a.id}')">Preview</button>
          <button class="btn btn-secondary" type="button"
                  onclick="takeActionDirect('${a.id}')"
                  ${taken || disabledTake ? "disabled" : ""}>
            Take action
          </button>
          ${taken ? `<span class="pill pill-warn">Taken</span>` : ``}
          ${disabledTake && !taken ? `<span class="pill">No tokens left</span>` : ``}
        </div>
      </div>
    `;
  }).join("");

  list.innerHTML = html;
}

function renderEvidence() {
  const inc = window.LAB4.incident;
  const state = loadState();

  const list = document.getElementById("evidenceList");
  if (!list) return;

  const html = inc.evidence.map(e => {
    const st = state.evidence?.[e.id] || "available";
    const cls = st === "preserved" ? "state-preserved" : (st === "lost" ? "state-lost" : "state-available");
    const label = st === "preserved" ? "Preserved" : (st === "lost" ? "Lost" : "Available");

    return `
      <div class="evidence-item">
        <div class="evidence-top">
          <div class="evidence-title">${escapeHtml(e.title)}</div>
          <span class="state ${cls}">${label}</span>
        </div>
        <div class="evidence-desc">${escapeHtml(e.description)}</div>
      </div>
    `;
  }).join("");

  list.innerHTML = html;
}

function renderSummaryAndTokens() {
  const inc = window.LAB4.incident;
  const state = loadState();
  const max = inc.rules.max_first_actions;

  let preserved = 0, lost = 0;
  for (const e of inc.evidence) {
    const st = state.evidence?.[e.id] || "available";
    if (st === "preserved") preserved++;
    if (st === "lost") lost++;
  }

  setText("countPreserved", preserved);
  setText("countLost", lost);
  setText("countChosen", (state.actions_taken || []).length);
  setText("countEscalate", state.notes?.escalate === "yes" ? 1 : 0);

  const taken = (state.actions_taken || []).length;
  const left = Math.max(0, max - taken);
  setText("tokensLeft", left);
  setText("actionsTaken", taken);

  updateStepper();
}

function updateStepper() {
  const inc = window.LAB4.incident;
  const state = loadState();
  const max = inc.rules.max_first_actions;

  const taken = (state.actions_taken || []).length;
  const anyEvidenceChanged = hasEvidenceChanged(state);
  const hasRecordText =
    (state.notes?.what || "").trim() ||
    (state.notes?.when || "").trim() ||
    (state.notes?.actions || "").trim() ||
    (state.notes?.status || "").trim();

  markStep("stepRoles", true);
  markStep("stepActions", taken > 0);
  markStep("stepOutcome", anyEvidenceChanged || taken >= max);
  markStep("stepRecord", !!hasRecordText);
  markStep("stepEscalate", (state.notes?.escalate || "").trim().length > 0);
}

function markStep(id, active) {
  const el = document.getElementById(id);
  if (!el) return;
  if (active) el.classList.add("active");
  else el.classList.remove("active");
}

function hasEvidenceChanged(state) {
  const inc = window.LAB4.incident;
  for (const e of inc.evidence) {
    const st = state.evidence?.[e.id] || "available";
    if (st !== "available") return true;
  }
  return false;
}

function previewAction(actionId) {
  const inc = window.LAB4.incident;
  const action = inc.actions.find(a => a.id === actionId);
  if (!action) return;

  pendingActionId = actionId;

  setTextNode("modalTitle", `Preview: ${action.title}`);
  setTextNode("modalDesc", action.description);

  const preserveList = (action.preserves || []).map(id => `• ${labelForEvidence(id)}`).join("\n") || "• (none)";
  const loseList = (action.destroys || []).map(id => `• ${labelForEvidence(id)}`).join("\n") || "• (none)";
  const riskList = (action.risks || []).map(r => `• ${r}`).join("\n") || "• (none)";

  setTextNode("modalPreserve", preserveList);
  setTextNode("modalLose", loseList);
  setTextNode("modalRisks", riskList);

  const takeBtn = document.getElementById("modalTakeBtn");
  if (takeBtn) {
    const state = loadState();
    const max = inc.rules.max_first_actions;
    const taken = (state.actions_taken || []).length;
    const already = (state.actions_taken || []).includes(actionId);
    takeBtn.disabled = already || taken >= max;
    takeBtn.textContent = already ? "Already taken" : (taken >= max ? "No tokens left" : "Take action");
  }

  openModal();
}

function takeActionDirect(actionId) {
  previewAction(actionId);
}

function confirmTakeAction() {
  if (!pendingActionId) return;
  takeAction(pendingActionId);
  closeModal();
}

function takeAction(actionId) {
  const inc = window.LAB4.incident;
  const state = loadState();
  const max = inc.rules.max_first_actions;

  state.actions_taken = state.actions_taken || [];
  if (state.actions_taken.includes(actionId)) return;
  if (state.actions_taken.length >= max) return;

  const action = inc.actions.find(a => a.id === actionId);
  if (!action) return;

  state.evidence = state.evidence || {};

  for (const eid of (action.preserves || [])) {
    if (state.evidence[eid] !== "lost") state.evidence[eid] = "preserved";
  }
  for (const eid of (action.destroys || [])) {
    if (state.evidence[eid] !== "preserved") state.evidence[eid] = "lost";
  }

  state.actions_taken.push(actionId);

  const line = `- ${action.title} (${action.phase}) — ${action.description}`;
  state.notes = state.notes || {};
  state.notes.actions = (state.notes.actions || "").trim();
  state.notes.actions = (state.notes.actions ? (state.notes.actions + "\n") : "") + line;

  saveState(state);

  renderActions();
  renderEvidence();
  renderSummaryAndTokens();
  restoreNotes();
  toast("Action taken. Check the Evidence Board for impact.");
}

function lab4SaveNotes() {
  const state = loadState();
  state.notes = state.notes || {};

  state.notes.what = document.getElementById("irWhat")?.value || "";
  state.notes.when = document.getElementById("irWhen")?.value || "";
  state.notes.actions = document.getElementById("irActions")?.value || state.notes.actions || "";
  state.notes.status = document.getElementById("irStatus")?.value || "";
  state.notes.escalateWhy = document.getElementById("escalateWhy")?.value || "";

  saveState(state);
  renderSummaryAndTokens();
  toast("Notes saved (stored in this browser).");
}

function lab4FillTemplate() {
  const inc = window.LAB4.incident;
  const state = loadState();
  state.notes = state.notes || {};

  const now = inc.report.time;
  if (!(state.notes.what || "").trim()) {
    state.notes.what =
      "Confirmed: User reported unexpected MFA prompts.\n" +
      "Suspected: Unauthorized access attempt or account compromise.\n" +
      "Plan: Preserve identity evidence and check for persistence indicators before containment changes state.";
  }

  if (!(state.notes.when || "").trim()) {
    state.notes.when =
      `- ${now} — User report received\n` +
      `- (Add observed timestamps from sign-in history / MFA events)\n`;
  }

  if (!(state.notes.status || "").trim()) {
    state.notes.status =
      "Status: Under investigation. Evidence preservation in progress. Containment decisions pending initial findings.";
  }

  saveState(state);
  restoreNotes();
  renderSummaryAndTokens();
  toast("Template filled.");
}

function lab4SetEscalate(val) {
  const state = loadState();
  state.notes = state.notes || {};
  state.notes.escalate = val;
  saveState(state);
  renderSummaryAndTokens();
}

function restoreNotes() {
  const state = loadState();
  const n = state.notes || {};

  if (document.getElementById("irWhat")) document.getElementById("irWhat").value = n.what || "";
  if (document.getElementById("irWhen")) document.getElementById("irWhen").value = n.when || "";
  if (document.getElementById("irActions")) document.getElementById("irActions").value = n.actions || "";
  if (document.getElementById("irStatus")) document.getElementById("irStatus").value = n.status || "";
  if (document.getElementById("escalateWhy")) document.getElementById("escalateWhy").value = n.escalateWhy || "";

  const esc = n.escalate || "";
  document.querySelectorAll('input[name="escalate"]').forEach(r => { r.checked = (r.value === esc); });
}

function labelForEvidence(eid) {
  const inc = window.LAB4.incident;
  const e = inc.evidence.find(x => x.id === eid);
  return e ? e.title : eid;
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = String(val);
}

function setTextNode(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = String(val ?? "");
}

function openModal() {
  const bg = document.getElementById("modalBackdrop");
  if (bg) bg.style.display = "flex";
}

function closeModal() {
  const bg = document.getElementById("modalBackdrop");
  if (bg) bg.style.display = "none";
  pendingActionId = null;
}

let toastTimer = null;
function toast(message) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.style.display = "block";

  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.style.display = "none"; }, 3200);
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
