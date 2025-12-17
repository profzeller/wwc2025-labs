const STORAGE_KEY = "wwc2025_lab3_triage_v1";

function triageInit() {
  if (!window.LAB3 || !Array.isArray(window.LAB3.events)) return;

  // ensure storage shape exists
  const state = triageLoadState();
  for (const ev of window.LAB3.events) {
    if (!state.responses[ev.id]) {
      state.responses[ev.id] = {
        classification: "",
        escalate: "",
        wanted: "",
        notes: ""
      };
    }
  }
  triageSaveState(state);

  triageRenderBadgesAll();
  triageUpdateSummary();

  // auto-open first event for convenience
  if (window.LAB3.events.length > 0) {
    openEvent(window.LAB3.events[0].id);
  }
}

function triageLoadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { responses: {} };
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return { responses: {} };
    if (!parsed.responses || typeof parsed.responses !== "object") parsed.responses = {};
    return parsed;
  } catch (e) {
    return { responses: {} };
  }
}

function triageSaveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function triageResetAll() {
  localStorage.removeItem(STORAGE_KEY);
  triageInit();
}

function openEvent(eventId) {
  const ev = window.LAB3.events.find(e => e.id === eventId);
  if (!ev) return;

  const state = triageLoadState();
  const resp = state.responses[eventId] || { classification:"", escalate:"", wanted:"", notes:"" };

  const instructor = !!window.LAB3.instructor;

  const html = `
    <h2 class="h2" style="margin-top:0;">Event Details</h2>

    <div class="codebox">
      <strong>${escapeHtml(ev.timestamp)}</strong><br/>
      Category: ${escapeHtml(ev.category)}<br/>
      Source: ${escapeHtml(ev.source)}<br/>
      Type: ${escapeHtml(ev.type)}<br/><br/>
      ${escapeHtml(ev.details)}
    </div>

    <div class="form-row" style="margin-top:12px;">
      <div class="pill">Step 1: classify</div>
      <div class="pill">Step 2: context</div>
      <div class="pill">Step 3: escalate decision</div>
    </div>

    <div style="margin-top:12px;">
      <label>Classification</label>
      <div class="radio-group">
        ${radio("classification", eventId, "noise", "Noise", resp.classification === "noise")}
        ${radio("classification", eventId, "signal", "Signal", resp.classification === "signal")}
        ${radio("classification", eventId, "context", "Needs more context", resp.classification === "context")}
      </div>
      <div class="small" style="margin-top:8px;">
        If you pick “Needs more context,” write what you’d want before deciding.
      </div>
    </div>

    <div style="margin-top:12px;">
      <label>What additional data would you want?</label>
      <textarea id="wanted-${eventId}" placeholder="Examples: prior logins for this user, asset criticality, baseline behavior, recent password changes, correlated events, etc.">${escapeHtml(resp.wanted || "")}</textarea>
    </div>

    <div style="margin-top:12px;">
      <label>Escalate?</label>
      <div class="radio-group">
        ${radio("escalate", eventId, "no", "No", resp.escalate === "no")}
        ${radio("escalate", eventId, "not_yet", "Not yet", resp.escalate === "not_yet")}
        ${radio("escalate", eventId, "yes", "Yes", resp.escalate === "yes")}
      </div>
      <div class="small" style="margin-top:8px;">
        Escalation should be rare. “Not yet” is valid if you need more context first.
      </div>
    </div>

    <div style="margin-top:12px;">
      <label>Notes / justification</label>
      <textarea id="notes-${eventId}" placeholder="Why did you classify it this way? What would make you change your mind?">${escapeHtml(resp.notes || "")}</textarea>
    </div>

    <div class="form-row" style="margin-top:12px; justify-content: space-between;">
      <button class="btn btn-secondary" type="button" onclick="triageSave('${eventId}')">Save</button>
      <button class="btn btn-danger" type="button" onclick="triageClear('${eventId}')">Clear</button>
    </div>

    <div class="callout" style="margin-top:12px;">
      <strong>Context prompts:</strong>
      <div class="small" style="margin-top:6px;">
        ${ev.prompts.map(p => "• " + escapeHtml(p)).join("<br/>")}
      </div>
    </div>

    ${instructor ? instructorBlock(ev) : ""}
  `;

  const panel = document.getElementById("detailPanel");
  panel.innerHTML = html;

  // highlight selected event button
  for (const btn of document.querySelectorAll(".event-item")) {
    btn.style.outline = "none";
  }
  const selected = document.getElementById(`eventBtn-${eventId}`);
  if (selected) selected.style.outline = "2px solid rgba(138,180,248,.55)";
}

function triageSave(eventId) {
  const state = triageLoadState();
  const resp = state.responses[eventId] || {};

  const cls = getRadioValue(`classification-${eventId}`);
  const esc = getRadioValue(`escalate-${eventId}`);
  const wanted = document.getElementById(`wanted-${eventId}`)?.value || "";
  const notes = document.getElementById(`notes-${eventId}`)?.value || "";

  resp.classification = cls || "";
  resp.escalate = esc || "";
  resp.wanted = wanted;
  resp.notes = notes;

  state.responses[eventId] = resp;
  triageSaveState(state);

  triageRenderBadges(eventId);
  triageUpdateSummary();
}

function triageClear(eventId) {
  const state = triageLoadState();
  state.responses[eventId] = { classification:"", escalate:"", wanted:"", notes:"" };
  triageSaveState(state);

  // refresh current panel
  openEvent(eventId);

  triageRenderBadges(eventId);
  triageUpdateSummary();
}

function triageRenderBadgesAll() {
  for (const ev of window.LAB3.events) {
    triageRenderBadges(ev.id);
  }
}

function triageRenderBadges(eventId) {
  const state = triageLoadState();
  const resp = state.responses[eventId] || {};
  const box = document.getElementById(`badges-${eventId}`);
  if (!box) return;

  const badges = [];

  if (resp.classification === "noise") badges.push(`<span class="badge badge-noise">Noise</span>`);
  if (resp.classification === "signal") badges.push(`<span class="badge badge-signal">Signal</span>`);
  if (resp.classification === "context") badges.push(`<span class="badge badge-context">Needs context</span>`);

  if (resp.escalate === "yes") badges.push(`<span class="badge badge-escalate">Escalate</span>`);

  box.innerHTML = badges.join("");
}

function triageUpdateSummary() {
  const state = triageLoadState();

  let noise = 0, signal = 0, context = 0, esc = 0;

  for (const ev of window.LAB3.events) {
    const r = state.responses[ev.id] || {};
    if (r.classification === "noise") noise++;
    if (r.classification === "signal") signal++;
    if (r.classification === "context") context++;
    if (r.escalate === "yes") esc++;
  }

  setText("countNoise", noise);
  setText("countSignal", signal);
  setText("countContext", context);
  setText("countEscalate", esc);
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = String(val);
}

function radio(groupName, eventId, value, label, checked) {
  const id = `${groupName}-${eventId}-${value}`;
  const name = `${groupName}-${eventId}`;
  return `
    <label class="radio" for="${id}">
      <input type="radio" id="${id}" name="${name}" value="${value}" ${checked ? "checked" : ""}>
      <span>${escapeHtml(label)}</span>
    </label>
  `;
}

function getRadioValue(name) {
  const el = document.querySelector(`input[name="${name}"]:checked`);
  return el ? el.value : "";
}

function instructorBlock(ev) {
  if (!ev.instructor_notes) return "";
  return `
    <details style="margin-top:12px;">
      <summary style="cursor:pointer; font-weight:650;">Instructor Guidance</summary>
      <div class="callout callout-good" style="margin-top:10px;">
        <strong>Guidance:</strong>
        <div class="small" style="margin-top:6px;">
          ${ev.instructor_notes.map(n => "• " + escapeHtml(n)).join("<br/>")}
        </div>
      </div>
    </details>
  `;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
