/* ================================================================
   Belief-Aware LLM — Frontend Application
   ================================================================ */

const API = "";  // same origin

// ── State ───────────────────────────────────────────────────────────

let beliefs = {};
let log = [];

// ── DOM refs ────────────────────────────────────────────────────────

const $beliefsList   = document.getElementById("beliefs-list");
const $beliefCount   = document.getElementById("belief-count");
const $inputKey      = document.getElementById("input-key");
const $inputValue    = document.getElementById("input-value");
const $btnAdd        = document.getElementById("btn-add");
const $btnResolve    = document.getElementById("btn-resolve");
const $btnReset      = document.getElementById("btn-reset");
const $btnPreset     = document.getElementById("btn-load-preset");
const $chatMessages  = document.getElementById("chat-messages");
const $chatForm      = document.getElementById("chat-form");
const $chatInput     = document.getElementById("chat-input");
const $dirtyIndicator = document.getElementById("dirty-indicator");
const $logEntries    = document.getElementById("log-entries");
const $logCount      = document.getElementById("log-count");

// ── API helpers ─────────────────────────────────────────────────────

async function api(path, opts = {}) {
    const res = await fetch(API + path, {
        headers: { "Content-Type": "application/json" },
        ...opts,
    });
    return res.json();
}

// ── Fetch & render ──────────────────────────────────────────────────

async function refresh() {
    await Promise.all([refreshBeliefs(), refreshLog()]);
}

async function refreshBeliefs() {
    beliefs = await api("/api/beliefs");
    renderBeliefs();
}

async function refreshLog() {
    log = await api("/api/log");
    renderLog();
}

// ── Render beliefs ──────────────────────────────────────────────────

function renderBeliefs() {
    const entities = Object.keys(beliefs).sort();
    let totalCount = 0;
    let hasDirty = false;

    if (entities.length === 0) {
        $beliefsList.innerHTML = '<div class="empty-state">No beliefs yet. Add one above or load a preset.</div>';
        $beliefCount.textContent = "0";
        $dirtyIndicator.style.display = "none";
        return;
    }

    let html = "";
    for (const entity of entities) {
        const items = beliefs[entity];
        totalCount += items.length;

        html += `<div class="entity-group">`;
        html += `<div class="entity-header" data-entity="${entity}">${entity}</div>`;

        for (const b of items) {
            if (b.is_dirty) hasDirty = true;
            const valClass = getValueClass(b.value);
            const displayVal = formatValue(b.value);
            const badgeClass = b.is_dirty ? "badge-dirty" : (b.is_derived ? "badge-derived" : "badge-base");
            const badgeText = b.is_dirty ? "dirty" : (b.is_derived ? "derived" : "base");

            html += `
                <div class="belief-item" data-key="${b.key}">
                    <span class="belief-key">${b.attribute}</span>
                    <span class="belief-eq">=</span>
                    <span class="belief-value ${valClass}">${displayVal}</span>
                    <span class="belief-badge ${badgeClass}">${badgeText}</span>
                    ${!b.is_derived ? `<button class="btn-icon-only" onclick="removeBelief('${b.key}')" title="Remove">✕</button>` : ""}
                </div>`;
        }
        html += `</div>`;
    }

    $beliefsList.innerHTML = html;
    $beliefCount.textContent = totalCount;
    $dirtyIndicator.style.display = hasDirty ? "flex" : "none";

    // Collapse/expand
    document.querySelectorAll(".entity-header").forEach(el => {
        el.addEventListener("click", () => {
            el.classList.toggle("collapsed");
            const items = el.parentElement.querySelectorAll(".belief-item");
            items.forEach(item => {
                item.style.display = el.classList.contains("collapsed") ? "none" : "flex";
            });
        });
    });
}

function getValueClass(val) {
    if (val === null || val === undefined) return "val-none";
    if (val === true) return "val-bool-true";
    if (val === false) return "val-bool-false";
    if (typeof val === "number") return "val-number";
    return "val-string";
}

function formatValue(val) {
    if (val === null || val === undefined) return "None";
    if (typeof val === "string") return `"${val}"`;
    return String(val);
}

// ── Render log ──────────────────────────────────────────────────────

function renderLog() {
    if (log.length === 0) {
        $logEntries.innerHTML = '<div class="empty-state">No revisions yet.</div>';
        $logCount.textContent = "0";
        return;
    }

    $logCount.textContent = log.length;

    // Show newest first
    let html = "";
    for (let i = log.length - 1; i >= 0; i--) {
        const entry = log[i];
        html += renderLogEntry(entry);
    }
    $logEntries.innerHTML = html;
}

function renderLogEntry(entry) {
    const action = entry.action;
    const actionClass = `log-action-${action}`;
    const key = entry.key;
    const oldVal = formatValue(entry.old);
    const newVal = formatValue(entry.new);

    let detail = "";
    if (action === "add") {
        detail = `<span class="log-values">${newVal}</span>`;
    } else if (action === "update") {
        detail = `<span class="log-values">${oldVal}<span class="log-arrow">→</span>${newVal}</span>`;
    } else if (action === "derived") {
        detail = `<span class="log-values">${oldVal}<span class="log-arrow">→</span>${newVal}</span>`;
        if (entry.reason) {
            detail += `<br><span class="log-reason">${entry.reason}</span>`;
        }
    } else if (action === "retract") {
        detail = `<span class="log-values">${oldVal}<span class="log-arrow">→</span>None</span>`;
    }

    return `
        <div class="log-entry">
            <span class="log-action ${actionClass}">${action}</span>
            <span class="log-key">${key}</span><br>
            ${detail}
        </div>`;
}

// ── Actions ─────────────────────────────────────────────────────────

async function addBelief() {
    const key = $inputKey.value.trim();
    const value = $inputValue.value.trim();
    if (!key) return;

    await api("/api/beliefs", {
        method: "POST",
        body: JSON.stringify({ key, value: value || null }),
    });

    $inputKey.value = "";
    $inputValue.value = "";
    $inputKey.focus();
    await refresh();
}

async function removeBelief(key) {
    await api(`/api/beliefs/${key}`, { method: "DELETE" });
    await refresh();
}

async function resolveAll() {
    $btnResolve.disabled = true;
    $btnResolve.textContent = "Resolving…";
    await api("/api/resolve", { method: "POST" });
    $btnResolve.disabled = false;
    $btnResolve.innerHTML = '<span class="btn-icon">⟳</span> Resolve';
    await refresh();
}

async function resetStore() {
    if (!confirm("Reset the entire belief store? This cannot be undone.")) return;
    await api("/api/reset", { method: "POST" });
    // Clear chat
    $chatMessages.innerHTML = `
        <div class="chat-welcome">
            <div class="chat-welcome-icon">◈</div>
            <p>Ask a question about the current belief state.</p>
            <p class="chat-welcome-sub">The LLM will reason over clean, resolved beliefs.</p>
        </div>`;
    await refresh();
}

async function loadPreset() {
    const preset = {
        "applicant.income": 6000,
        "applicant.credit_score": 720,
        "applicant.co_signer": false,
        "applicant.debt_ratio": 0.20,
        "applicant.employment_status": "employed",
        "applicant.bankruptcy_history": false,
        "applicant.employment_duration_months": 36,
        "applicant.has_collateral": false,
        "applicant.loan_amount_requested": 10000,
        "loan.min_income": 5000,
        "loan.min_credit": 650,
        "loan.max_debt_ratio": 0.4,
    };

    for (const [key, value] of Object.entries(preset)) {
        await api("/api/beliefs", {
            method: "POST",
            body: JSON.stringify({ key, value }),
        });
    }

    // Auto-resolve after loading preset
    await api("/api/resolve", { method: "POST" });
    await refresh();
}

// ── Chat ────────────────────────────────────────────────────────────

async function sendChat(structuredInput) {
    // Remove welcome message
    const welcome = $chatMessages.querySelector(".chat-welcome");
    if (welcome) welcome.remove();

    // Show the query part in the UI
    const queryMatch = structuredInput.match(/\[QUERY\]\s*\n?([\s\S]*)/i);
    const displayText = queryMatch ? queryMatch[1].trim() : structuredInput;
    appendChatMsg(displayText, "user");

    // Add typing indicator
    const typingEl = document.createElement("div");
    typingEl.className = "chat-typing";
    typingEl.innerHTML = "<span></span><span></span><span></span>";
    $chatMessages.appendChild(typingEl);
    scrollChat();

    $chatInput.disabled = true;

    try {
        const data = await api("/api/query", {
            method: "POST",
            body: JSON.stringify({ input: structuredInput }),
        });

        typingEl.remove();

        if (data.error) {
            appendChatMsg(data.error, "error");
        } else {
            appendChatMsg(data.response, "ai");
        }
    } catch (err) {
        typingEl.remove();
        appendChatMsg("Network error: " + err.message, "error");
    }

    $chatInput.disabled = false;
    $chatInput.focus();
    await refresh();
}

function appendChatMsg(text, type) {
    const el = document.createElement("div");

    if (type === "user") {
        el.className = "chat-msg chat-msg-user";
        el.textContent = text;
    } else if (type === "ai") {
        el.className = "chat-msg chat-msg-ai";
        el.innerHTML = formatAIResponse(text);
    } else {
        el.className = "chat-msg chat-msg-error";
        el.textContent = text;
    }

    $chatMessages.appendChild(el);
    scrollChat();
}

function formatAIResponse(text) {
    // Highlight REASONING: and ANSWER: labels
    let html = escapeHtml(text);
    html = html.replace(
        /^(REASONING:)/m,
        '<span class="reasoning-label">Reasoning</span>'
    );
    html = html.replace(
        /^(ANSWER:)/m,
        '<span class="answer-label">Answer</span>'
    );
    return html;
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function scrollChat() {
    requestAnimationFrame(() => {
        $chatMessages.scrollTop = $chatMessages.scrollHeight;
    });
}

// ── Event listeners ─────────────────────────────────────────────────

$btnAdd.addEventListener("click", addBelief);
$inputKey.addEventListener("keydown", e => { if (e.key === "Enter") $inputValue.focus(); });
$inputValue.addEventListener("keydown", e => { if (e.key === "Enter") addBelief(); });

$btnResolve.addEventListener("click", resolveAll);
$btnReset.addEventListener("click", resetStore);
$btnPreset.addEventListener("click", loadPreset);

$chatForm.addEventListener("submit", e => {
    e.preventDefault();
    const q = $chatInput.value.trim();
    if (!q) return;
    $chatInput.value = "";
    sendChat(q);
});

// Cmd/Ctrl+Enter to submit, plain Enter for newlines
$chatInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        $chatForm.dispatchEvent(new Event("submit"));
    }
});

// ── Initial load ────────────────────────────────────────────────────

refresh();
