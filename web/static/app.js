/* ================================================================
   Belief-Aware LLM — Frontend Application
   ================================================================ */

const API = ""; // same origin

// ── State ───────────────────────────────────────────────────────────

let beliefs = {};
let log = [];
let graphData = { nodes: [], edges: [] };
let domainInfo = {};
let currentDomain = "loan";
let selectedEntities = new Set();
let currentMode = "chat"; // "chat" or "simulation"
let updatedKeys = new Set();

// ── Domain attribute schemas (type-aware inputs) ────────────────────
const DOMAIN_SCHEMA = {
  loan: {
    "applicant.income": "int",
    "applicant.credit_score": "int",
    "applicant.debt_ratio": "float",
    "applicant.employment_status": "str",
    "applicant.employment_duration_months": "int",
    "applicant.has_collateral": "bool",
    "applicant.loan_amount_requested": "int",
    "applicant.bankruptcy_history": "bool",
    "applicant.co_signer": "bool",
    "applicant.dependents": "int",
    "loan.min_income": "int",
    "loan.min_credit": "int",
    "loan.max_debt_ratio": "float",
  },
  alien_clinic: {
    "patient.organism_type": "str",
    "patient.symptoms": "list",
    "atmosphere.ambient_pressure": "float",
    "atmosphere.dominant_gas": "str",
  },
  crime_scene: {
    "officer_smith.status": "str",
    "case.warrant_status": "bool",
    "case.cctv_status": "str",
    "case.cctv_subject": "str",
    "suspect_a.home_evidence": "str",
    "suspect_a.evidence_logger": "str",
    "suspect_a.financial_records": "str",
    "suspect_b.relation_to_victim": "str",
    "suspect_b.alibi_partner": "str",
  },
  thorncrester: {
    "environment.weather_pattern": "str",
    "environment.food_scarcity": "bool",
    "adult_thorncrester.genetic_diet": "str",
    "thorncrester_flock.genetic_structure": "str",
    "juvenile_thorncrester.digestive_enzyme": "str",
  },
};

// Simulation state
let simRunning = false;
let simTotalTurns = 0;
let simCurrentTurn = 0;
let simCorrect = 0;

// ── DOM refs ────────────────────────────────────────────────────────

const $graphCanvas = document.getElementById("graph-canvas");
const $graphTooltip = document.getElementById("graph-tooltip");
const $graphContainer = document.getElementById("graph-container");
const $inputKey = document.getElementById("input-key");
const $inputValueCont = document.getElementById("input-value-container");
const $btnAdd = document.getElementById("btn-add");
const $btnResolve = document.getElementById("btn-resolve");
const $btnReset = document.getElementById("btn-reset");
const $chatMessages = document.getElementById("chat-messages");
const $chatInput = document.getElementById("chat-input");
const $btnSend = document.getElementById("btn-send");
const $chatCondition = document.getElementById("chat-condition");
const $dirtyIndicator = document.getElementById("dirty-indicator");
const $logEntries = document.getElementById("log-entries");
const $logCount = document.getElementById("log-count");
const $domainSelector = document.getElementById("domain-selector");
const $modelSelector = document.getElementById("model-selector");
const $entityChips = document.getElementById("entity-chips");
const $beliefRows = document.getElementById("belief-rows");
const $btnAddRow = document.getElementById("btn-add-belief-row");
const $fullPrompt = document.getElementById("full-prompt");
const $fullPromptBody = document.getElementById("full-prompt-body");
const $systemPrompt = document.getElementById("system-prompt-view");
const $userPrompt = document.getElementById("user-prompt-view");
const $btnTogglePrompt = document.getElementById("btn-toggle-prompt");

let selectedModel = "";

// Mode tabs
const $tabChat = document.getElementById("tab-chat");
const $tabSim = document.getElementById("tab-simulation");
const $panelChat = document.getElementById("panel-chat");
const $panelSim = document.getElementById("panel-simulation");

// Simulation
const $simWelcome = document.getElementById("sim-welcome");
const $simTurns = document.getElementById("sim-turns");
const $simFooter = document.getElementById("sim-footer");
const $simTurnLabel = document.getElementById("sim-turn-label");
const $simProgressFill = document.getElementById("sim-progress-fill");
const $simScore = document.getElementById("sim-score");
const $btnSimStart = document.getElementById("btn-sim-start");
const $btnSimStep = document.getElementById("btn-sim-step");
const $btnSimStop = document.getElementById("btn-sim-stop");
const $simCondition = document.getElementById("sim-condition");

// Graph collapse
const $btnGraphToggle = document.getElementById("btn-graph-toggle");
const $layout = document.querySelector(".layout");
let graphCollapsed = false;

// Simulation abort controller
let simAbortController = null;

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
  await Promise.all([refreshGraph(), refreshLog()]);
}

async function refreshGraph(highlightKeys = []) {
  graphData = await api("/api/graph");
  updatedKeys = new Set(highlightKeys);
  renderGraph();
  updateDirtyIndicator();
}

async function refreshLog() {
  log = await api("/api/log");
  renderLog();
}

async function loadDomains() {
  const data = await api("/api/domains");
  domainInfo = data.domains;
  currentDomain = data.current;
  $domainSelector.value = currentDomain;
  updateEntityChips();
  updateAttributeDropdowns();
}

function updateDirtyIndicator() {
  const hasDirty = graphData.nodes.some((n) => n.is_dirty);
  $dirtyIndicator.style.display = hasDirty ? "flex" : "none";
}

async function loadModels() {
  try {
    const data = await api("/api/models");
    $modelSelector.innerHTML = "";
    data.models.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = m;
      $modelSelector.appendChild(opt);
    });
    if (data.models.length > 0) {
      selectedModel = data.models[0];
      $modelSelector.value = selectedModel;
    }
  } catch (err) {
    $modelSelector.innerHTML =
      '<option value="qwen3:4b">qwen3:4b (offline)</option>';
    selectedModel = "qwen3:4b";
  }
}

// ══════════════════════════════════════════════════════════════════
// DEPENDENCY GRAPH RENDERER (Canvas-based force-directed layout)
// ══════════════════════════════════════════════════════════════════

const ENTITY_COLORS = {
  applicant: "#4a9eff",
  loan: "#6c5ce7",
  patient: "#00cec9",
  case: "#fd79a8",
  suspect_a: "#e74c3c",
  suspect_b: "#f39c12",
  officer_smith: "#00b894",
  environment: "#00cec9",
  adult_thorncrester: "#e84393",
  thorncrester_flock: "#fdcb6e",
  juvenile_thorncrester: "#55efc4",
  feather_mite: "#d63031",
};

function getEntityColor(entity) {
  return ENTITY_COLORS[entity] || "#8b949e";
}

// Force simulation state
let gNodes = [];
let gEdges = [];
let animFrame = null;
let hoveredNode = null;

function renderGraph() {
  const canvas = $graphCanvas;
  const container = $graphContainer;
  const rect = container.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;

  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  canvas.style.width = rect.width + "px";
  canvas.style.height = rect.height + "px";

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const W = rect.width;
  const H = rect.height;

  // Build node map
  const nodeMap = {};
  const nodes = graphData.nodes.map((n, i) => {
    const existing = gNodes.find((gn) => gn.id === n.id);
    const node = {
      id: n.id,
      entity: n.entity,
      value: n.value,
      is_derived: n.is_derived,
      is_dirty: n.is_dirty,
      x: existing ? existing.x : W * 0.2 + Math.random() * W * 0.6,
      y: existing ? existing.y : H * 0.2 + Math.random() * H * 0.6,
      vx: 0,
      vy: 0,
      radius: n.is_derived ? 12 : 15,
      targetX: 0,
      targetY: 0,
    };
    nodeMap[n.id] = node;
    return node;
  });
  const existingNodes = gNodes; // keep reference for position persistence

  const edges = graphData.edges
    .map((e) => ({
      source: nodeMap[e.source],
      target: nodeMap[e.target],
    }))
    .filter((e) => e.source && e.target);

  // ── DAG Layout Algorithm (Layered) ──────────────────────────────
  const revAdj = {};
  graphData.edges.forEach((e) => {
    if (!revAdj[e.target]) revAdj[e.target] = [];
    revAdj[e.target].push(e.source);
  });

  const levelMap = {};
  function getLevel(id) {
    if (levelMap[id] !== undefined) return levelMap[id];
    const parents = revAdj[id] || [];
    if (parents.length === 0) return (levelMap[id] = 0);
    let maxL = 0;
    parents.forEach((p) => {
      maxL = Math.max(maxL, getLevel(p));
    });
    return (levelMap[id] = maxL + 1);
  }

  nodes.forEach((n) => getLevel(n.id));

  const nodesByLevel = {};
  let maxLevel = 0;
  nodes.forEach((n) => {
    const l = levelMap[n.id];
    if (!nodesByLevel[l]) nodesByLevel[l] = [];
    nodesByLevel[l].push(n);
    maxLevel = Math.max(maxLevel, l);
  });

  const padding = 60;
  const colWidth = (W - 2 * padding) / (maxLevel || 1);

  Object.keys(nodesByLevel).forEach((l) => {
    const layerNodes = nodesByLevel[l];
    const rowHeight = (H - 2 * padding) / layerNodes.length;
    layerNodes.forEach((n, i) => {
      n.radius = n.is_derived ? 12 : 15; // Increased size
      n.targetX = padding + l * colWidth;
      n.targetY = padding + i * rowHeight + rowHeight / 2;

      // If the node is new or lacks stable coords, start near target
      if (!existingNodes.find((en) => en.id === n.id)) {
        n.x = n.targetX - 50;
        n.y = n.targetY;
      }
    });
  });

  gNodes = nodes;
  gEdges = edges;

  // Run simulation
  let iterations = 0;
  const maxIter = 200;

  function simulate() {
    const alpha = Math.max(0.01, 1 - iterations / maxIter);

    // Repulsion (all pairs)
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i],
          b = nodes[j];
        let dx = b.x - a.x,
          dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const repulse = 2000 / (dist * dist);
        const fx = (dx / dist) * repulse * alpha;
        const fy = (dy / dist) * repulse * alpha;
        a.vx -= fx;
        a.vy -= fy;
        b.vx += fx;
        b.vy += fy;
      }
    }

    // Attraction (edges)
    for (const e of edges) {
      let dx = e.target.x - e.source.x;
      let dy = e.target.y - e.source.y;
      let dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const attract = (dist - 80) * 0.02 * alpha;
      const fx = (dx / dist) * attract;
      const fy = (dy / dist) * attract;
      e.source.vx += fx;
      e.source.vy += fy;
      e.target.vx -= fx;
      e.target.vy -= fy;
    }

    // DAG Alignment (pull nodes to their target layered slots)
    for (const n of nodes) {
      n.vx += (n.targetX - n.x) * 0.2 * alpha;
      n.vy += (n.targetY - n.y) * 0.2 * alpha;
    }

    // Apply velocity with damping
    for (const n of nodes) {
      n.vx *= 0.7; // stronger damping for stability
      n.vy *= 0.7;
      n.x += n.vx;
      n.y += n.vy;
      // Bounds
      n.x = Math.max(n.radius, Math.min(W - n.radius, n.x));
      n.y = Math.max(n.radius, Math.min(H - n.radius, n.y));
    }

    draw(ctx, W, H);
    iterations++;
    if (iterations < maxIter) {
      animFrame = requestAnimationFrame(simulate);
    }
  }

  if (animFrame) cancelAnimationFrame(animFrame);
  iterations = 0;
  simulate();
}

function draw(ctx, W, H) {
  ctx.clearRect(0, 0, W, H);

  // Draw edges
  for (const e of gEdges) {
    const dx = e.target.x - e.source.x;
    const dy = e.target.y - e.source.y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const r = e.target.radius + 6; // offset for arrowhead
    const startR = e.source.radius + 2;
    const startX = e.source.x + (dx / dist) * startR;
    const startY = e.source.y + (dy / dist) * startR;
    const endX = e.target.x - (dx / dist) * r;
    const endY = e.target.y - (dy / dist) * r;

    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.strokeStyle = "rgba(110, 118, 129, 0.35)";
    ctx.lineWidth = 1;
    ctx.stroke();

    // Arrowhead
    const angle = Math.atan2(dy, dx);
    const aLen = 6;
    ctx.beginPath();
    ctx.moveTo(endX, endY);
    ctx.lineTo(
      endX - aLen * Math.cos(angle - 0.4),
      endY - aLen * Math.sin(angle - 0.4),
    );
    ctx.lineTo(
      endX - aLen * Math.cos(angle + 0.4),
      endY - aLen * Math.sin(angle + 0.4),
    );
    ctx.closePath();
    ctx.fillStyle = "rgba(110, 118, 129, 0.5)";
    ctx.fill();
  }

  // Draw nodes
  for (const n of gNodes) {
    const color = getEntityColor(n.entity);

    // Dirty glow
    if (n.is_dirty) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 6, 0, Math.PI * 2);
      const grad = ctx.createRadialGradient(
        n.x,
        n.y,
        n.radius,
        n.x,
        n.y,
        n.radius + 6,
      );
      grad.addColorStop(0, "rgba(243, 156, 18, 0.4)");
      grad.addColorStop(1, "rgba(243, 156, 18, 0)");
      ctx.fillStyle = grad;
      ctx.fill();
    }

    // Updated glow (newly added/derived this turn)
    if (updatedKeys.has(n.id)) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 10, 0, Math.PI * 2);
      const grad = ctx.createRadialGradient(
        n.x,
        n.y,
        n.radius,
        n.x,
        n.y,
        n.radius + 10,
      );
      grad.addColorStop(0, "rgba(52, 152, 219, 0.5)"); // Sleek blue glow
      grad.addColorStop(1, "rgba(52, 152, 219, 0)");
      ctx.fillStyle = grad;
      ctx.fill();

      // Add a subtle pulse or ring for updated nodes
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 4, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(52, 152, 219, 0.8)";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Node shape
    ctx.beginPath();
    if (n.is_derived) {
      // Diamond for derived
      ctx.moveTo(n.x, n.y - n.radius);
      ctx.lineTo(n.x + n.radius, n.y);
      ctx.lineTo(n.x, n.y + n.radius);
      ctx.lineTo(n.x - n.radius, n.y);
      ctx.closePath();
    } else {
      // Circle for base
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
    }

    ctx.fillStyle = n.is_dirty ? "#f39c12" : color;
    ctx.fill();
    ctx.strokeStyle = n === hoveredNode ? "#fff" : "rgba(0,0,0,0.3)";
    ctx.lineWidth = n === hoveredNode ? 2 : 1;
    ctx.stroke();

    // Label
    const label = n.id.split(".").pop();
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "rgba(230, 237, 243, 0.7)";
    ctx.fillText(label, n.x, n.y + n.radius + 14);
  }
}

// Mouse interaction
$graphCanvas.addEventListener("mousemove", (e) => {
  const rect = $graphCanvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  let found = null;
  for (const n of gNodes) {
    const dx = mx - n.x,
      dy = my - n.y;
    if (Math.sqrt(dx * dx + dy * dy) < n.radius + 4) {
      found = n;
      break;
    }
  }

  hoveredNode = found;
  if (found) {
    $graphTooltip.style.display = "block";
    let val =
      found.value !== null && found.value !== undefined ? found.value : "—";
    if (Array.isArray(val)) {
      val =
        `<ul style="margin:4px 0 0 12px;padding:0;font-size:11px;">` +
        val.map((v) => `<li>${v}</li>`).join("") +
        `</ul>`;
    }
    const tag = found.is_dirty
      ? "dirty"
      : found.is_derived
        ? "derived"
        : "base";
    $graphTooltip.innerHTML = `<strong>${found.id}</strong><br>${found.entity} · <span style="color:${found.is_dirty ? "#f39c12" : found.is_derived ? "#6c5ce7" : "#4a9eff"}">${tag}</span><br>Value: ${val}`;

    // Position tooltip using fixed coords, clamped to viewport
    let tx = e.clientX + 14;
    let ty = e.clientY - 10;
    const tw = $graphTooltip.offsetWidth;
    const th = $graphTooltip.offsetHeight;
    if (tx + tw > window.innerWidth - 8) tx = e.clientX - tw - 14;
    if (ty + th > window.innerHeight - 8) ty = window.innerHeight - th - 8;
    if (ty < 8) ty = 8;
    $graphTooltip.style.left = tx + "px";
    $graphTooltip.style.top = ty + "px";

    $graphCanvas.style.cursor = "pointer";
  } else {
    $graphTooltip.style.display = "none";
    $graphCanvas.style.cursor = "default";
  }

  // Redraw for hover highlight
  const container = $graphContainer.getBoundingClientRect();
  const ctx = $graphCanvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw(ctx, container.width, container.height);
});

$graphCanvas.addEventListener("mouseleave", () => {
  hoveredNode = null;
  $graphTooltip.style.display = "none";
});

// Resize handler
window.addEventListener("resize", () => {
  if (graphData.nodes.length > 0) renderGraph();
});

// ── Render log ──────────────────────────────────────────────────────

function renderLog() {
  if (log.length === 0) {
    $logEntries.innerHTML = '<div class="empty-state">No revisions yet.</div>';
    $logCount.textContent = "0";
    return;
  }

  $logCount.textContent = log.length;
  let html = "";
  for (let i = log.length - 1; i >= 0; i--) {
    html += renderLogEntry(log[i]);
  }
  $logEntries.innerHTML = html;
}

function renderLogEntry(entry) {
  const action = entry.action;
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
    if (entry.reason)
      detail += `<br><span class="log-reason">${entry.reason}</span>`;
  } else if (action === "retract") {
    detail = `<span class="log-values">${oldVal}<span class="log-arrow">→</span>None</span>`;
  }

  return `<div class="log-entry"><span class="log-action log-action-${action}">${action}</span><span class="log-key">${key}</span><br>${detail}</div>`;
}

function formatValue(val) {
  if (val === null || val === undefined) return "None";
  if (typeof val === "string") return `"${val}"`;
  return String(val);
}

// ══════════════════════════════════════════════════════════════════
// ENTITY CHIPS & PROMPT BUILDER
// ══════════════════════════════════════════════════════════════════

function updateEntityChips() {
  const info = domainInfo[currentDomain];
  if (!info) return;
  const ents = info.entities;
  selectedEntities = new Set(ents); // select all by default

  $entityChips.innerHTML = ents
    .map(
      (e) =>
        `<span class="entity-chip selected" data-entity="${e}">${e}</span>`,
    )
    .join("");

  $entityChips.querySelectorAll(".entity-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const ent = chip.dataset.entity;
      if (selectedEntities.has(ent)) {
        selectedEntities.delete(ent);
        chip.classList.remove("selected");
      } else {
        selectedEntities.add(ent);
        chip.classList.add("selected");
      }
    });
  });
}

// ── Attribute dropdown helpers ───────────────────────────────────────

function updateAttributeDropdowns() {
  const attrs = Object.keys(DOMAIN_SCHEMA[currentDomain] || {});
  const html =
    `<option value="">-- attribute --</option>` +
    attrs.map((a) => `<option value="${a}">${a}</option>`).join("");

  // Sidebar select
  $inputKey.innerHTML = html;
  $inputValueCont.innerHTML = `<input type="text" id="input-value" placeholder="value" spellcheck="false">`;

  // React to selection changes
  $inputKey.onchange = () => {
    const type = DOMAIN_SCHEMA[currentDomain][$inputKey.value];
    $inputValueCont.innerHTML = renderValueInput(type, "input-value", "");
  };
}

function renderValueInput(type, id, className) {
  const idAttr = id ? `id="${id}"` : "";
  if (type === "bool") {
    return `<select ${idAttr} class="${className} br-value">
            <option value="true">true</option>
            <option value="false">false</option>
        </select>`;
  } else if (type === "int" || type === "float" || type === "numeric") {
    const step = type === "int" ? "1" : "any";
    return `<input type="number" ${idAttr} class="${className} br-value" placeholder="0" step="${step}">`;
  } else if (type === "list") {
    return `<input type="text" ${idAttr} class="${className} br-value" placeholder="item1, item2" title="Comma-separated list">`;
  } else {
    return `<input type="text" ${idAttr} class="${className} br-value" placeholder="value" spellcheck="false">`;
  }
}

function castValue(key, rawValue) {
  const type = DOMAIN_SCHEMA[currentDomain][key];
  if (!type) return rawValue;
  if (type === "int") return parseInt(rawValue, 10);
  if (type === "float" || type === "numeric") return parseFloat(rawValue);
  if (type === "bool") return rawValue === "true" || rawValue === true;
  if (type === "list") {
    return rawValue
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  }
  return rawValue;
}

// ── Belief Row (Chat Prompt Builder) ────────────────────────────────

function addBeliefRow() {
  const attrs = Object.keys(DOMAIN_SCHEMA[currentDomain] || {});
  const opts =
    `<option value="">-- attribute --</option>` +
    attrs.map((a) => `<option value="${a}">${a}</option>`).join("");

  const row = document.createElement("div");
  row.className = "belief-row";
  row.innerHTML = `
        <select class="br-key">${opts}</select>
        <span style="color:var(--text-muted);font-size:11px">=</span>
        <div class="br-value-container">
            <input type="text" class="br-value" placeholder="value" spellcheck="false">
        </div>
        <button class="btn-remove-row" title="Remove">✕</button>
    `;

  const select = row.querySelector(".br-key");
  const container = row.querySelector(".br-value-container");
  select.onchange = () => {
    const type = DOMAIN_SCHEMA[currentDomain][select.value];
    container.innerHTML = renderValueInput(type, "", "");
  };

  row
    .querySelector(".btn-remove-row")
    .addEventListener("click", () => row.remove());
  $beliefRows.appendChild(row);
}

function buildStructuredInput() {
  const entities = Array.from(selectedEntities);
  if (entities.length === 0) return null;

  const query = $chatInput.value.trim();
  if (!query) return null;

  let parts = [`[ENTITY]\n${entities.join(", ")}`];

  // Collect belief rows
  const rows = $beliefRows.querySelectorAll(".belief-row");
  const beliefLines = [];
  rows.forEach((row) => {
    const key = row.querySelector(".br-key").value;
    const valEl = row.querySelector(".br-value");
    if (key && valEl && valEl.value) {
      const casted = castValue(key, valEl.value);
      const display = Array.isArray(casted) ? JSON.stringify(casted) : casted;
      beliefLines.push(`${key} = ${display}`);
    }
  });
  if (beliefLines.length > 0) {
    parts.push(`[NEW BELIEF]\n${beliefLines.join("\n")}`);
  }

  parts.push(`[QUERY]\n${query}`);
  return parts.join("\n\n");
}

// ── Actions ─────────────────────────────────────────────────────────

async function addBelief() {
  const key = $inputKey.value;
  const valEl = document.getElementById("input-value");
  if (!key || !valEl) return;

  const value = castValue(key, valEl.value);

  await api("/api/beliefs", {
    method: "POST",
    body: JSON.stringify({ key, value }),
  });

  $inputKey.value = "";
  updateAttributeDropdowns();
  $inputKey.focus();
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
  $chatMessages.innerHTML = `
        <div class="chat-welcome">
            <div class="chat-welcome-icon">◈</div>
            <p>Ask a question about the current belief state.</p>
            <p class="chat-welcome-sub">The LLM will reason over clean, resolved beliefs.</p>
        </div>`;
  await refresh();
}

async function switchDomain(domainKey) {
  currentDomain = domainKey;
  await api("/api/domain", {
    method: "POST",
    body: JSON.stringify({ domain: domainKey }),
  });
  updateEntityChips();
  updateAttributeDropdowns();
  // Clear chat
  $chatMessages.innerHTML = `
        <div class="chat-welcome">
            <div class="chat-welcome-icon">◈</div>
            <p>Ask a question about the current belief state.</p>
            <p class="chat-welcome-sub">Domain switched to <strong>${domainInfo[domainKey].label}</strong>.</p>
        </div>`;
  // Clear belief rows
  $beliefRows.innerHTML = "";
  if ($systemPrompt) $systemPrompt.textContent = "";
  if ($userPrompt) $userPrompt.textContent = "";
  if ($fullPromptBody) $fullPromptBody.style.display = "none";
  if ($btnTogglePrompt) $btnTogglePrompt.textContent = "Show";
  await refresh();
}

// ── Chat ────────────────────────────────────────────────────────────

async function sendChat() {
  const condition = $chatCondition.value;
  const structured = buildStructuredInput();
  if (!structured) return;

  // Remove welcome
  const welcome = $chatMessages.querySelector(".chat-welcome");
  if (welcome) welcome.remove();

  // Show query
  const queryMatch = structured.match(/\[QUERY\]\s*\n?([\s\S]*)/i);
  const displayText = queryMatch ? queryMatch[1].trim() : structured;
  const userMsgEl = appendChatMsg(displayText, "user");

  // Typing indicator
  const typingEl = document.createElement("div");
  typingEl.className = "chat-typing";
  typingEl.innerHTML = "<span></span><span></span><span></span>";
  $chatMessages.appendChild(typingEl);
  scrollChat();

  $chatInput.disabled = true;
  $btnSend.disabled = true;

  try {
    const promptVersion = document.getElementById("prompt-version").value;
    const data = await api("/api/query", {
      method: "POST",
      body: JSON.stringify({
        input: structured,
        condition,
        model: selectedModel,
        prompt_version: promptVersion,
      }),
    });
    typingEl.remove();
    if (data.error) {
      appendChatMsg(data.error, "error");
    } else {
      if (data.prompt) {
        if (userMsgEl) {
          const promptBlock = document.createElement("div");
          promptBlock.className = "prompt-msg-inline";
          promptBlock.innerHTML = formatPromptBlock(data.prompt);
          userMsgEl.appendChild(promptBlock);
        }
        if ($systemPrompt && $userPrompt) {
          $systemPrompt.textContent = data.prompt.system || "";
          $userPrompt.textContent = data.prompt.user || "";
        }
      }
      appendChatMsg(data.response, "ai");
    }
  } catch (err) {
    typingEl.remove();
    appendChatMsg("Network error: " + err.message, "error");
  }

  $chatInput.disabled = false;
  $btnSend.disabled = false;
  $chatInput.value = "";
  $chatInput.focus();
  // Clear belief rows after sending
  $beliefRows.innerHTML = "";
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
  } else if (type === "prompt") {
    el.className = "chat-msg chat-msg-prompt";
    el.innerHTML = formatPromptBlock(text);
  } else {
    el.className = "chat-msg chat-msg-error";
    el.textContent = text;
  }
  $chatMessages.appendChild(el);
  scrollChat();
  return el;
}

function formatAIResponse(text) {
  let html = escapeHtml(text);
  html = html.replace(
    /^(REASONING:)/m,
    '<span class="reasoning-label">Reasoning</span>',
  );
  html = html.replace(
    /^(ANSWER:)/m,
    '<span class="answer-label">Answer</span>',
  );
  return html;
}

function formatPromptBlock(prompt) {
  const system = escapeHtml(prompt.system || "");
  const user = escapeHtml(prompt.user || "");
  return `
        <div class="prompt-msg-title">Full Prompt Sent</div>
        <div class="prompt-msg-section">
            <button class="prompt-collapse" type="button">System Prompt</button>
            <pre class="prompt-collapsible" style="display:none">${system}</pre>
        </div>
        <div class="prompt-msg-section">
            <div class="prompt-msg-label">User Prompt</div>
            <pre>${user}</pre>
        </div>
    `;
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

// Toggle system prompt visibility inside user bubbles
$chatMessages.addEventListener("click", (evt) => {
  const btn = evt.target.closest(".prompt-collapse");
  if (!btn) return;
  const section = btn.closest(".prompt-msg-section");
  if (!section) return;
  const pre = section.querySelector(".prompt-collapsible");
  if (!pre) return;
  const isHidden = pre.style.display === "none";
  pre.style.display = isHidden ? "block" : "none";
});

// ══════════════════════════════════════════════════════════════════
// SIMULATION MODE
// ══════════════════════════════════════════════════════════════════

async function startSimulation() {
  const condition = $simCondition.value;

  const data = await api("/api/simulate/start", {
    method: "POST",
    body: JSON.stringify({
      domain: currentDomain,
      condition,
      model: selectedModel,
    }),
  });

  if (data.error) {
    alert(data.error);
    return;
  }

  // Clear any previous highlights and refresh graph for initial state
  await refreshGraph([]);

  simRunning = true;
  simTotalTurns = data.total_turns;
  simCurrentTurn = 0;
  simCorrect = 0;

  $simWelcome.style.display = "none";
  $simTurns.style.display = "flex";
  $simTurns.innerHTML = "";
  $simFooter.style.display = "flex";

  updateSimProgress();
}

async function stepSimulation() {
  if (!simRunning) return;

  $btnSimStep.disabled = true;
  $btnSimStep.textContent = "Running…";

  simAbortController = new AbortController();

  try {
    const res = await fetch(API + "/api/simulate/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: simAbortController.signal,
    });
    const data = await res.json();

    // If simulation was stopped while waiting, ignore the result
    if (!simRunning) return;

    if (data.error && data.done) {
      $btnSimStep.textContent = "Done ✓";
      simRunning = false;
      return;
    }

    simCurrentTurn = data.turn;
    if (data.hit) simCorrect++;

    // Build turn card
    const card = document.createElement("div");
    card.className = "sim-turn-card";

    const resultClass = data.hit ? "sim-result-correct" : "sim-result-wrong";
    const resultText = data.hit
      ? `✓ ${data.llm_answer}`
      : `✗ ${data.llm_answer || "—"} (correct: ${data.correct})`;

    let injectedHtml = "";
    if (
      data.injected_beliefs &&
      Object.keys(data.injected_beliefs).length > 0
    ) {
      const lines = Object.entries(data.injected_beliefs)
        .map(([k, v]) => `${k} = ${v}`)
        .join("\n");
      injectedHtml = `<div class="sim-injected">Injected: ${escapeHtml(lines)}</div>`;
    }

    let optionsHtml = "";
    for (const [letter, text] of Object.entries(data.options)) {
      let cls = "";
      if (letter === data.correct) cls = "correct-answer";
      else if (letter === data.llm_answer && !data.hit) cls = "wrong-answer";
      optionsHtml += `<div class="sim-option ${cls}">${letter}) ${text}</div>`;
    }

    card.innerHTML = `
            <div class="sim-turn-header">
                <span class="sim-turn-number">Turn ${data.turn}</span>
                <span class="sim-turn-result ${resultClass}">${resultText}</span>
            </div>
            <div class="sim-turn-body">
                ${injectedHtml}
                <div class="sim-question">${escapeHtml(data.question)}</div>
                <div class="sim-options">${optionsHtml}</div>
                <div class="sim-llm-response">${escapeHtml(data.llm_response)}</div>
            </div>
        `;

    $simTurns.appendChild(card);
    card.scrollIntoView({ behavior: "smooth", block: "end" });

    // Refresh graph to show updates
    await refreshGraph(data.updated_keys || []);

    updateSimProgress();

    if (data.done) {
      $btnSimStep.textContent = "Done ✓";
      simRunning = false;
    } else {
      $btnSimStep.disabled = false;
      $btnSimStep.textContent = "Next Turn →";
    }
  } catch (err) {
    if (err.name === "AbortError") return; // stopped by user
    $btnSimStep.disabled = false;
    $btnSimStep.textContent = "Next Turn →";
    alert("Error: " + err.message);
  } finally {
    simAbortController = null;
  }
}

function updateSimProgress() {
  $simTurnLabel.textContent = `Turn ${simCurrentTurn} / ${simTotalTurns}`;
  $simProgressFill.style.width = `${(simCurrentTurn / simTotalTurns) * 100}%`;
  $simScore.textContent = `${simCorrect} / ${simCurrentTurn}`;
}

// ── Mode switching ──────────────────────────────────────────────────

function switchMode(mode) {
  currentMode = mode;
  $tabChat.classList.toggle("active", mode === "chat");
  $tabSim.classList.toggle("active", mode === "simulation");
  $panelChat.style.display = mode === "chat" ? "flex" : "none";
  $panelSim.style.display = mode === "simulation" ? "flex" : "none";
}

// ── Graph collapse/expand ───────────────────────────────────────────

const $panelGraph = document.getElementById("panel-graph");
const $resizeHandle = document.getElementById("resize-handle");
let graphSavedWidth = 380; // remember width before collapse

function toggleGraphPanel() {
  graphCollapsed = !graphCollapsed;
  $layout.classList.toggle("graph-collapsed", graphCollapsed);
  if (graphCollapsed) {
    graphSavedWidth = $panelGraph.offsetWidth;
  } else {
    $panelGraph.style.width = graphSavedWidth + "px";
    setTimeout(() => renderGraph(), 50);
  }
}

// ── Drag-resize the graph sidebar ───────────────────────────────────

(function initResize() {
  let startX = 0;
  let startW = 0;

  function onMouseDown(e) {
    if (graphCollapsed) return;
    e.preventDefault();
    startX = e.clientX;
    startW = $panelGraph.offsetWidth;
    $resizeHandle.classList.add("dragging");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }

  function onMouseMove(e) {
    const delta = e.clientX - startX;
    const newW = Math.min(
      Math.max(startW + delta, 180),
      window.innerWidth * 0.7,
    );
    $panelGraph.style.width = newW + "px";
  }

  function onMouseUp() {
    $resizeHandle.classList.remove("dragging");
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    graphSavedWidth = $panelGraph.offsetWidth;
    renderGraph(); // re-render at the new size
  }

  $resizeHandle.addEventListener("mousedown", onMouseDown);
})();

// ── Stop simulation ─────────────────────────────────────────────────

function stopSimulation() {
  simRunning = false;
  if (simAbortController) {
    simAbortController.abort();
    simAbortController = null;
  }
  $btnSimStep.disabled = false;
  $btnSimStep.textContent = "Done (stopped)";
  $btnSimStep.disabled = true;

  // Add a stopped indicator card
  const card = document.createElement("div");
  card.className = "sim-turn-card";
  card.innerHTML = `
        <div class="sim-turn-header">
            <span class="sim-turn-number">Simulation Stopped</span>
            <span class="sim-turn-result sim-result-pending">■ Halted</span>
        </div>
        <div class="sim-turn-body">
            <div class="sim-question" style="color:var(--text-muted)">Stopped at turn ${simCurrentTurn} / ${simTotalTurns}. Final score: ${simCorrect} / ${simCurrentTurn}.</div>
        </div>
    `;
  $simTurns.appendChild(card);
  card.scrollIntoView({ behavior: "smooth", block: "end" });
}

// ── Event listeners ─────────────────────────────────────────────────

$btnAdd.addEventListener("click", addBelief);
$inputKey.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const valEl = document.getElementById("input-value");
    if (valEl) valEl.focus();
  }
});
// Delegate Enter-key on the value input (it's dynamically swapped)
document
  .getElementById("input-value-container")
  .addEventListener("keydown", (e) => {
    if (e.key === "Enter") addBelief();
  });

$btnResolve.addEventListener("click", resolveAll);
$btnReset.addEventListener("click", resetStore);

$btnSend.addEventListener("click", sendChat);
$btnTogglePrompt?.addEventListener("click", () => {
  if (!$fullPromptBody || !$btnTogglePrompt) return;
  const isHidden = $fullPromptBody.style.display === "none";
  $fullPromptBody.style.display = isHidden ? "block" : "none";
  $btnTogglePrompt.textContent = isHidden ? "Hide" : "Show";
});
$chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
    e.preventDefault();
    sendChat();
  }
});

$btnAddRow.addEventListener("click", addBeliefRow);

$domainSelector.addEventListener("change", (e) => {
  switchDomain(e.target.value);
});

$modelSelector.addEventListener("change", (e) => {
  selectedModel = e.target.value;
});

$tabChat.addEventListener("click", () => switchMode("chat"));
$tabSim.addEventListener("click", () => switchMode("simulation"));

$btnSimStart.addEventListener("click", () => {
  // Reset sim UI
  $simWelcome.style.display = "none";
  startSimulation();
});

$btnSimStep.addEventListener("click", stepSimulation);
$btnSimStop.addEventListener("click", stopSimulation);

$btnGraphToggle.addEventListener("click", toggleGraphPanel);

// ── Initial load ────────────────────────────────────────────────────

(async () => {
  await loadModels();
  await loadDomains();
  await refresh();
})();
