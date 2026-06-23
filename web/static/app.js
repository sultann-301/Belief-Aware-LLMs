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
let selectedAttributes = new Set();
let filterMode = "entity"; // "entity" or "attribute"
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
const $btnThemeToggle = document.getElementById("btn-theme-toggle");
const $themeIcon = document.getElementById("theme-icon");

let selectedModel = "";

// Disable chat until initialization completes
$chatInput.disabled = true;
$btnSend.disabled = true;

// Mode tabs
const $tabChat = document.getElementById("tab-chat");
const $tabSim = document.getElementById("tab-simulation");
const $tabExample = document.getElementById("tab-example");
const $panelChat = document.getElementById("panel-chat");
const $panelSim = document.getElementById("panel-simulation");
const $panelExample = document.getElementById("panel-example");

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
const $btnRunExample = document.getElementById("btn-run-example");
const $exampleInputBeliefs = document.getElementById("example-input-beliefs");
const $exampleStepGrid = document.getElementById("example-step-grid");
const $exampleStorePrompt = document.getElementById("example-store-prompt");

// Graph collapse
const $btnGraphToggle = document.getElementById("btn-graph-toggle");
const $layout = document.querySelector(".layout");
let graphCollapsed = false;

// Simulation abort controller
let simAbortController = null;
let lastHopwalkGraph = null;

// ── Theme helpers ──────────────────────────────────────────────────

function cssVar(name) {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function themeCanvasColors() {
  return {
    isLight: document.documentElement.getAttribute("data-theme") === "light",
    edgeRgb: cssVar("--canvas-edge"),
    labelRgb: cssVar("--canvas-label"),
    mutedLabelRgb: cssVar("--canvas-muted-label"),
    nodeStroke: cssVar("--node-stroke"),
    accentBlue: cssVar("--accent-blue"),
    accentBlueRgb: cssVar("--accent-blue-rgb"),
    accentPurple: cssVar("--accent-purple"),
    accentPurpleRgb: cssVar("--accent-purple-rgb"),
    accentOrange: cssVar("--accent-orange"),
    accentOrangeRgb: cssVar("--accent-orange-rgb"),
    accentCyan: cssVar("--accent-cyan"),
    accentCyanRgb: cssVar("--accent-cyan-rgb"),
  };
}

function setTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
  if ($themeIcon) $themeIcon.textContent = theme === "light" ? "☾" : "☼";
  if (graphData && graphData.nodes && graphData.nodes.length > 0) renderGraph();
  const hopwalkOverlay = document.getElementById("hopwalk-overlay");
  if (
    hopwalkOverlay &&
    hopwalkOverlay.style.display !== "none" &&
    lastHopwalkGraph
  ) {
    renderHopWalkGraph(
      lastHopwalkGraph.nodes,
      lastHopwalkGraph.edges,
      lastHopwalkGraph.attributes,
    );
  }
}

if ($btnThemeToggle) {
  $btnThemeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    setTheme(current === "light" ? "dark" : "light");
  });
}

setTheme(localStorage.getItem("theme") || "dark");

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
      // Bounds include label space below each node.
      const labelPadX = Math.max(n.radius, 48);
      const labelPadTop = n.radius + 6;
      const labelPadBottom = n.radius + 34;
      n.x = Math.max(labelPadX, Math.min(W - labelPadX, n.x));
      n.y = Math.max(labelPadTop, Math.min(H - labelPadBottom, n.y));
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
  const theme = themeCanvasColors();

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
    ctx.strokeStyle = `rgba(${theme.edgeRgb}, 0.35)`;
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
    ctx.fillStyle = `rgba(${theme.edgeRgb}, 0.5)`;
    ctx.fill();
  }

  // Draw nodes
  for (const n of gNodes) {
    let color;
    if (n.is_dirty) {
      color = theme.accentOrange;
    } else if (n.is_derived) {
      color = theme.accentPurple;
    } else {
      color = theme.accentBlue;
    }

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
      grad.addColorStop(0, `rgba(${theme.accentOrangeRgb}, 0.4)`);
      grad.addColorStop(1, `rgba(${theme.accentOrangeRgb}, 0)`);
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
      grad.addColorStop(0, `rgba(${theme.accentBlueRgb}, 0.5)`);
      grad.addColorStop(1, `rgba(${theme.accentBlueRgb}, 0)`);
      ctx.fillStyle = grad;
      ctx.fill();

      // Add a subtle pulse or ring for updated nodes
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius + 4, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${theme.accentBlueRgb}, 0.8)`;
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

    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle =
      n === hoveredNode
        ? theme.isLight
          ? "#212529"
          : "#fff"
        : theme.nodeStroke;
    ctx.lineWidth = n === hoveredNode ? 2 : 1;
    ctx.stroke();

    // Label
    const parts = n.id.split(".");
    const entityLabel = n.entity || parts[0] || "";
    const attrLabel = parts.length > 1 ? parts.slice(1).join(".") : n.id;
    ctx.textAlign = "center";
    ctx.font = "9px Inter, sans-serif";
    ctx.fillStyle = `rgba(${theme.mutedLabelRgb}, 0.76)`;
    ctx.fillText(entityLabel, n.x, n.y + n.radius + 13);
    ctx.font = "10px Inter, sans-serif";
    ctx.fillStyle = `rgba(${theme.labelRgb}, 0.82)`;
    ctx.fillText(attrLabel, n.x, n.y + n.radius + 26);
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
    const theme = themeCanvasColors();
    let val =
      found.value !== null && found.value !== undefined ? found.value : "-";
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
    const tagColor = found.is_dirty
      ? theme.accentOrange
      : found.is_derived
        ? theme.accentPurple
        : theme.accentBlue;
    $graphTooltip.innerHTML = `<strong>${found.id}</strong><br>${found.entity} · <span style="color:${tagColor}">${tag}</span><br>Value: ${val}`;

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

  // Also build attribute chips
  updateAttributeChips();
}

// ── Attribute chip picker ───────────────────────────────────────────

function updateAttributeChips() {
  const $grid = document.getElementById("attr-chip-grid");
  if (!$grid) return;

  // Collect all keys from store graph data (base + derived)
  const allKeys = new Set();
  graphData.nodes.forEach((n) => allKeys.add(n.id));
  // Also add schema keys
  Object.keys(DOMAIN_SCHEMA[currentDomain] || {}).forEach((k) =>
    allKeys.add(k),
  );

  const sorted = Array.from(allKeys).sort();
  selectedAttributes = new Set();
  const theme = themeCanvasColors();

  $grid.innerHTML = sorted
    .map((key) => {
      const node = graphData.nodes.find((n) => n.id === key);
      let color = theme.accentBlue;
      if (node) {
        if (node.is_dirty) {
          color = theme.accentOrange;
        } else if (node.is_derived) {
          color = theme.accentPurple;
        }
      }
      return `<span class="attr-chip" data-key="${key}">
        <span class="attr-dot" style="background:${color}"></span>
        ${key}
      </span>`;
    })
    .join("");

  $grid.querySelectorAll(".attr-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const key = chip.dataset.key;
      if (selectedAttributes.has(key)) {
        selectedAttributes.delete(key);
        chip.classList.remove("selected");
      } else {
        selectedAttributes.add(key);
        chip.classList.add("selected");
      }
    });
  });

  // Search filter
  const $search = document.getElementById("attr-search");
  if ($search) {
    $search.value = "";
    $search.oninput = () => {
      const q = $search.value.toLowerCase();
      $grid.querySelectorAll(".attr-chip").forEach((chip) => {
        const key = chip.dataset.key;
        chip.classList.toggle("attr-chip-hidden", !key.includes(q));
      });
    };
  }
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
  const query = $chatInput.value.trim();
  if (!query) return null;

  let filterItems;
  if (filterMode === "attribute" && selectedAttributes.size > 0) {
    filterItems = Array.from(selectedAttributes);
  } else {
    filterItems = Array.from(selectedEntities);
  }
  if (filterItems.length === 0) return null;

  let parts = [`[ENTITY]\n${filterItems.join(", ")}`];

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
  updateEntityChips();
  updateAttributeDropdowns();
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

// ── Screenshot example run ─────────────────────────────────────────

const EXAMPLE_RUN = {
  domain: "alien_clinic",
  query:
    "What billing tier should the clinic assign?",
  inputBeliefs: [
    ["atmosphere.dominant_gas", "chlorine"],
    ["atmosphere.ambient_pressure", 4.5],
    ["patient.organism_type", "Qwerl"],
    ["patient.symptoms", ["fever"]],
  ],
  steps: [
    {
      title: "After Input: Broad Dirty Fan-Out",
      label: "14 dirty",
      note: "The update marks many downstream clinic beliefs dirty.",
      graphNodes: [
        { key: "atmosphere.dominant_gas", x: 70, y: 70 },
        { key: "patient.organism_type", x: 70, y: 175 },
        { key: "atmosphere.ambient_pressure", x: 70, y: 285 },
        { key: "patient.symptoms", x: 70, y: 365 },
        { key: "treatment.zyxostin_phase", x: 235, y: 60 },
        { key: "treatment.filinan_phase", x: 235, y: 145 },
        { key: "treatment.snevox_phase", x: 235, y: 230 },
        { key: "patient.organ_integrity", x: 235, y: 315 },
        { key: "treatment.zyxostin_danger_level", x: 400, y: 72 },
        { key: "treatment.filinan_danger_level", x: 400, y: 168 },
        { key: "treatment.snevox_danger_level", x: 400, y: 264 },
        { key: "patient.quarantine_required", x: 400, y: 360 },
        { key: "treatment.active_prescription", x: 575, y: 175 },
        { key: "patient.sensory_status", x: 710, y: 95 },
        { key: "treatment.duration_cycles", x: 710, y: 255 },
        { key: "medical.staff_requirement", x: 710, y: 350 },
        { key: "clinic.billing_tier", x: 875, y: 230 },
        { key: "patient.recovery_prospect", x: 875, y: 340 },
      ],
    },
    {
      title: "Resolved HopWalker Subgraph",
      label: "3 keys",
      note: "HopWalker extracts only the keys needed for clinic.billing_tier.",
      graphNodes: [
        { key: "treatment.active_prescription", x: 250, y: 150 },
        { key: "medical.staff_requirement", x: 250, y: 260 },
        { key: "clinic.billing_tier", x: 650, y: 205 },
      ],
    },
  ],
  targetAttributes: ["clinic.billing_tier"],
  fallbackValues: {
    "atmosphere.dominant_gas": "chlorine",
    "atmosphere.ambient_pressure": 4.5,
    "patient.organism_type": "Qwerl",
    "patient.symptoms": ["fever"],
    "treatment.active_prescription": "zyxostin",
    "medical.staff_requirement": "hazmat_team",
    "clinic.billing_tier": "class_delta",
  },
};

function formatExampleValue(value) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return value.toLocaleString("en-US");
  if (typeof value === "boolean") return String(value);
  return String(value);
}

function graphValueMap(graph = graphData) {
  const values = { ...EXAMPLE_RUN.fallbackValues };
  for (const node of graph.nodes || []) {
    if (node.value !== null && node.value !== undefined) {
      values[node.id] = node.value;
    }
  }
  return values;
}

function exampleGraphSnapshot(graph) {
  return {
    nodes: [...(graph.nodes || [])],
    edges: [...(graph.edges || [])],
  };
}

async function fetchExampleGraphSnapshot() {
  const graph = await api("/api/graph");
  return exampleGraphSnapshot(graph);
}

function graphNodeMap(graph) {
  const map = {};
  for (const node of graph?.nodes || []) map[node.id] = node;
  return map;
}

function truncateExampleLabel(value, max = 16) {
  if (value.length <= max) return value;
  return value.slice(0, max - 1) + "...";
}

function wrapExampleLabel(value, max = 13, maxLines = 2) {
  const words = value.replaceAll("_", " ").split(" ");
  const lines = [];
  let current = "";
  for (const word of words) {
    const next = current ? `${current} ${word}` : word;
    if (next.length > max && current) {
      lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) lines.push(current);
  return lines.slice(0, maxLines).map((line, index) => {
    if (index === maxLines - 1 && lines.length > maxLines) {
      return truncateExampleLabel(line, max - 1) + ".";
    }
    return truncateExampleLabel(line, max);
  });
}

function edgeEndpoint(from, to, radius = 30) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const len = Math.hypot(dx, dy) || 1;
  return {
    x1: from.x + (dx / len) * radius,
    y1: from.y + (dy / len) * radius,
    x2: to.x - (dx / len) * (radius + 5),
    y2: to.y - (dy / len) * (radius + 5),
  };
}

function renderMiniGraph(graph, step, stateIndex) {
  if (!graph) {
    return `<div class="example-graph-placeholder">Run the example to capture this graph state.</div>`;
  }

  const nodeMap = graphNodeMap(graph);
  const layoutNodes = step.graphNodes
    .map((layout) => ({ ...layout, node: nodeMap[layout.key] }))
    .filter((layout) => layout.node);
  const layoutByKey = Object.fromEntries(layoutNodes.map((layout) => [layout.key, layout]));
  const visibleKeys = new Set(layoutNodes.map((layout) => layout.key));

  const edgeHtml = (graph.edges || [])
    .filter((edge) => visibleKeys.has(edge.source) && visibleKeys.has(edge.target))
    .map((edge) => {
      const points = edgeEndpoint(layoutByKey[edge.source], layoutByKey[edge.target]);
      return `
        <line class="example-dependency-edge"
          x1="${points.x1}" y1="${points.y1}"
          x2="${points.x2}" y2="${points.y2}" />
      `;
    })
    .join("");

  const nodeHtml = layoutNodes
    .map(({ key, x, y, node }) => {
      const parts = key.split(".");
      const entity = parts[0];
      const attr = parts.slice(1).join(".");
      let cls = node.is_derived ? "derived" : "base";
      if (node.is_dirty) cls += " dirty";
      if (stateIndex === 1 && EXAMPLE_RUN.targetAttributes.includes(key)) {
        cls += " final";
      }
      const showValue = stateIndex === 1 && node.is_derived;
      const value = showValue ? formatExampleValue(node.value) : "";
      const attrLines = wrapExampleLabel(attr);
      const attrText = attrLines
        .map((line, index) => `<tspan x="0" dy="${index === 0 ? 0 : 11}">${escapeHtml(line)}</tspan>`)
        .join("");
      return `
        <g class="example-dependency-node ${cls}" transform="translate(${x} ${y})">
          <circle r="30"></circle>
          <text class="example-dependency-entity" x="0" y="-8">${escapeHtml(truncateExampleLabel(entity, 12))}</text>
          <text class="example-dependency-attr" x="0" y="4">${attrText}</text>
          ${showValue ? `<text class="example-dependency-value" x="0" y="24">${escapeHtml(truncateExampleLabel(value, 12))}</text>` : ""}
        </g>
      `;
    })
    .join("");

  return `
    <svg class="example-dependency-graph" viewBox="0 0 950 430" role="img" aria-label="Alien Clinic dependency graph">
      <g class="example-dependency-edges">${edgeHtml}</g>
      <g class="example-dependency-nodes">${nodeHtml}</g>
    </svg>
  `;
}

function renderExampleNode(key, values, variant = "") {
  const parts = key.split(".");
  const entity = parts[0] || key;
  const attr = parts.length > 1 ? parts.slice(1).join(".") : key;
  return `
    <div class="example-node ${variant}">
      <span class="example-node-entity">${escapeHtml(entity)}</span>
      <span class="example-node-attr">${escapeHtml(attr)}</span>
      <span class="example-node-value">${escapeHtml(formatExampleValue(values[key]))}</span>
    </div>
  `;
}

function renderExampleRun(values = EXAMPLE_RUN.fallbackValues, graphStates = []) {
  if (!$exampleInputBeliefs || !$exampleStepGrid) return;

  $exampleInputBeliefs.innerHTML = EXAMPLE_RUN.inputBeliefs
    .map(
      ([key]) => `
        <div class="example-belief">
          <span class="example-belief-key">${escapeHtml(key)}</span>
          <span class="example-belief-value">${escapeHtml(formatExampleValue(values[key]))}</span>
        </div>
      `,
    )
    .join("");

  $exampleStepGrid.innerHTML = EXAMPLE_RUN.steps
    .map((step, index) => {
      return `
        <div class="example-step">
          <div class="example-step-title">${escapeHtml(step.title)} <span>${step.label}</span></div>
          ${step.note ? `<div class="example-step-note">${escapeHtml(step.note)}</div>` : ""}
          ${renderMiniGraph(graphStates[index], step, index)}
        </div>
      `;
    })
    .join("");
}

async function buildExamplePrompt() {
  const data = await api("/api/hopwalk", {
    method: "POST",
    body: JSON.stringify({ attributes: EXAMPLE_RUN.targetAttributes }),
  });
  if (data.error) throw new Error(data.error);
  return [
    "[ENTITY]",
    EXAMPLE_RUN.targetAttributes.join(", "),
    "",
    "[RELEVANT BELIEFS]",
    data.prompt || "",
    "",
    "[QUERY]",
    EXAMPLE_RUN.query,
  ].join("\n");
}

async function seedExampleBeliefs() {
  for (const [key, value] of EXAMPLE_RUN.inputBeliefs) {
    await api("/api/beliefs", {
      method: "POST",
      body: JSON.stringify({ key, value }),
    });
  }
}

async function runExample() {
  if (!$btnRunExample) return;

  $btnRunExample.disabled = true;
  $btnRunExample.textContent = "Running...";
  if ($exampleStorePrompt) {
    $exampleStorePrompt.textContent =
      "Resolving graph states and building the HopWalker prompt...";
  }
  renderExampleRun();

  try {
    if (currentDomain !== EXAMPLE_RUN.domain) {
      currentDomain = EXAMPLE_RUN.domain;
      $domainSelector.value = EXAMPLE_RUN.domain;
      await api("/api/domain", {
        method: "POST",
        body: JSON.stringify({ domain: EXAMPLE_RUN.domain }),
      });
      await loadDomains();
    } else {
      await api("/api/reset", { method: "POST" });
    }

    await api("/api/resolve", { method: "POST" });
    await seedExampleBeliefs();
    const dirtyGraph = await fetchExampleGraphSnapshot();
    await api("/api/resolve", { method: "POST" });
    const resolvedGraph = await fetchExampleGraphSnapshot();
    const graphStates = [dirtyGraph, resolvedGraph];
    await refreshGraph([]);
    await refreshLog();
    renderExampleRun(graphValueMap(resolvedGraph), graphStates);

    const promptText = await buildExamplePrompt();

    await refreshGraph([]);
    await refreshLog();
    renderExampleRun(graphValueMap(resolvedGraph), graphStates);

    if ($exampleStorePrompt) {
      $exampleStorePrompt.textContent = promptText;
    }
  } catch (err) {
    if ($exampleStorePrompt) {
      $exampleStorePrompt.textContent = "Error: " + err.message;
    }
  } finally {
    $btnRunExample.disabled = false;
    $btnRunExample.textContent = "Run Alien Clinic Example";
  }
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
  $tabExample?.classList.toggle("active", mode === "example");
  $layout.classList.toggle("example-mode", mode === "example");
  $panelChat.style.display = mode === "chat" ? "flex" : "none";
  $panelSim.style.display = mode === "simulation" ? "flex" : "none";
  if ($panelExample) {
    $panelExample.style.display = mode === "example" ? "flex" : "none";
  }
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
  if (e.key === "Enter" && !e.shiftKey) {
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
$tabExample?.addEventListener("click", () => switchMode("example"));
$btnRunExample?.addEventListener("click", runExample);

$btnSimStart.addEventListener("click", () => {
  // Reset sim UI
  $simWelcome.style.display = "none";
  startSimulation();
});

$btnSimStep.addEventListener("click", stepSimulation);
$btnSimStop.addEventListener("click", stopSimulation);

$btnGraphToggle.addEventListener("click", toggleGraphPanel);

// ── Filter mode toggle ──────────────────────────────────────────────

const $btnEntityMode = document.getElementById("btn-entity-mode");
const $btnAttrMode = document.getElementById("btn-attr-mode");
const $attributeChips = document.getElementById("attribute-chips");

function setFilterMode(mode) {
  filterMode = mode;
  $btnEntityMode.classList.toggle("active", mode === "entity");
  $btnAttrMode.classList.toggle("active", mode === "attribute");
  $entityChips.style.display = mode === "entity" ? "flex" : "none";
  $attributeChips.style.display = mode === "attribute" ? "block" : "none";

  // If switching to attribute mode and prompt is v1-v3, auto-switch to v4
  if (mode === "attribute") {
    const $pv = document.getElementById("prompt-version");
    if ($pv && !$pv.value.startsWith("v4")) {
      $pv.value = "v4";
    }
  }
}

$btnEntityMode.addEventListener("click", () => setFilterMode("entity"));
$btnAttrMode.addEventListener("click", () => setFilterMode("attribute"));

// ══════════════════════════════════════════════════════════════════
// HOPWALKER VISUALIZER
// ══════════════════════════════════════════════════════════════════

const $hopwalkOverlay = document.getElementById("hopwalk-overlay");
const $hopwalkCanvas = document.getElementById("hopwalk-canvas");
const $hopwalkPromptText = document.getElementById("hopwalk-prompt-text");
const $hopwalkKeyCount = document.getElementById("hopwalk-key-count");
const $hopwalkAttrs = document.getElementById("hopwalk-attrs");
const $btnHopwalk = document.getElementById("btn-hopwalk");
const $btnHopwalkClose = document.getElementById("btn-hopwalk-close");

async function openHopWalker() {
  const attrs = Array.from(selectedAttributes);
  if (attrs.length === 0) {
    alert("Select at least one attribute to visualize.");
    return;
  }

  // Show overlay immediately with loading state
  $hopwalkOverlay.style.display = "flex";
  $hopwalkPromptText.textContent = "Loading...";
  $hopwalkKeyCount.textContent = "...";
  $hopwalkAttrs.innerHTML = attrs
    .map((a) => `<span class="hopwalk-attr-tag">${a}</span>`)
    .join("");

  try {
    const data = await api("/api/hopwalk", {
      method: "POST",
      body: JSON.stringify({ attributes: attrs }),
    });

    $hopwalkPromptText.textContent = data.prompt || "(empty)";
    $hopwalkKeyCount.textContent = `${data.prompt_keys?.length || 0} keys`;

    renderHopWalkGraph(data.nodes, data.edges, data.attributes);
  } catch (err) {
    $hopwalkPromptText.textContent = "Error: " + err.message;
  }
}

function closeHopWalker() {
  $hopwalkOverlay.style.display = "none";
}

function renderHopWalkGraph(nodes, edges, targetAttrs) {
  lastHopwalkGraph = { nodes, edges, attributes: targetAttrs };
  const canvas = $hopwalkCanvas;
  const container = canvas.parentElement;
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
  const padding = 60;
  const theme = themeCanvasColors();
  const layerColors = {
    base: theme.accentBlue,
    intermediate: theme.accentPurple,
    target: theme.accentCyan,
  };

  if (!nodes || nodes.length === 0) {
    ctx.fillStyle = `rgba(${theme.mutedLabelRgb}, 0.8)`;
    ctx.font = "14px Inter, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("No beliefs found for these attributes.", W / 2, H / 2);
    return;
  }

  // Group by layer
  const layers = { base: [], intermediate: [], target: [] };
  const nodeMap = {};
  nodes.forEach((n) => {
    layers[n.layer].push(n);
    nodeMap[n.key] = n;
  });

  const layerOrder = ["base", "intermediate", "target"];
  const activeLayerOrder = layerOrder.filter((l) => layers[l].length > 0);
  const colWidth = (W - 2 * padding) / Math.max(activeLayerOrder.length - 1, 1);

  // Position nodes
  const positions = {};
  activeLayerOrder.forEach((layer, li) => {
    const layerNodes = layers[layer];
    const x = padding + li * colWidth;
    const rowH = (H - 2 * padding) / Math.max(layerNodes.length, 1);
    layerNodes.forEach((n, ni) => {
      positions[n.key] = {
        x,
        y: padding + ni * rowH + rowH / 2,
        color: layerColors[layer],
        layer,
        node: n,
      };
    });
  });

  // Animation: draw edges first, then nodes
  const totalFrames = 60;
  let frame = 0;

  function animate() {
    frame++;
    const progress = Math.min(frame / totalFrames, 1);
    const ease = 1 - Math.pow(1 - progress, 3);

    ctx.clearRect(0, 0, W, H);

    // Layer labels
    ctx.font = "10px Inter, sans-serif";
    ctx.textAlign = "center";
    activeLayerOrder.forEach((layer, li) => {
      const x = padding + li * colWidth;
      ctx.fillStyle = layerColors[layer];
      ctx.globalAlpha = ease;
      const label =
        layer === "base"
          ? "ROOT FACTS"
          : layer === "intermediate"
            ? "INTERMEDIATE"
            : "TARGETS";
      ctx.fillText(label, x, 25);
    });
    ctx.globalAlpha = 1;

    // Draw edges with animated opacity
    edges.forEach((e) => {
      const srcPos = positions[e.source];
      const tgtPos = positions[e.target];
      if (!srcPos || !tgtPos) return;

      const edgeAlpha = ease * 0.5;
      ctx.beginPath();
      ctx.moveTo(srcPos.x, srcPos.y);

      // Curved edge
      const midX = (srcPos.x + tgtPos.x) / 2;
      const midY = (srcPos.y + tgtPos.y) / 2 - 20;
      ctx.quadraticCurveTo(midX, midY, tgtPos.x, tgtPos.y);

      ctx.strokeStyle = `rgba(${theme.edgeRgb}, ${edgeAlpha})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Arrowhead
      const angle = Math.atan2(tgtPos.y - midY, tgtPos.x - midX);
      const aLen = 7;
      ctx.beginPath();
      ctx.moveTo(tgtPos.x, tgtPos.y);
      ctx.lineTo(
        tgtPos.x - aLen * Math.cos(angle - 0.35),
        tgtPos.y - aLen * Math.sin(angle - 0.35),
      );
      ctx.lineTo(
        tgtPos.x - aLen * Math.cos(angle + 0.35),
        tgtPos.y - aLen * Math.sin(angle + 0.35),
      );
      ctx.closePath();
      ctx.fillStyle = `rgba(${theme.edgeRgb}, ${edgeAlpha * 1.5})`;
      ctx.fill();
    });

    // Draw nodes
    Object.values(positions).forEach((pos) => {
      const n = pos.node;
      const r = n.layer === "target" ? 16 : n.layer === "base" ? 14 : 12;
      const alpha = ease;

      // Glow for targets
      if (n.layer === "target") {
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r + 12, 0, Math.PI * 2);
        const grad = ctx.createRadialGradient(
          pos.x,
          pos.y,
          r,
          pos.x,
          pos.y,
          r + 12,
        );
        grad.addColorStop(0, `rgba(${theme.accentCyanRgb}, ${0.3 * alpha})`);
        grad.addColorStop(1, `rgba(${theme.accentCyanRgb}, 0)`);
        ctx.fillStyle = grad;
        ctx.fill();
      }

      // Node
      ctx.beginPath();
      if (n.layer === "target") {
        // Diamond
        ctx.moveTo(pos.x, pos.y - r);
        ctx.lineTo(pos.x + r, pos.y);
        ctx.lineTo(pos.x, pos.y + r);
        ctx.lineTo(pos.x - r, pos.y);
        ctx.closePath();
      } else if (n.layer === "intermediate") {
        // Rounded square
        const s = r * 0.85;
        ctx.roundRect(pos.x - s, pos.y - s, s * 2, s * 2, 4);
      } else {
        // Circle
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
      }
      ctx.fillStyle = pos.color;
      ctx.globalAlpha = alpha;
      ctx.fill();
      ctx.strokeStyle = theme.nodeStroke;
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.globalAlpha = 1;

      // Label
      const parts = n.key.split(".");
      const entityLabel = n.entity || parts[0] || "";
      const attrLabel = parts.length > 1 ? parts.slice(1).join(".") : n.key;
      ctx.textAlign = "center";
      ctx.font = "9px Inter, sans-serif";
      ctx.fillStyle = `rgba(${theme.mutedLabelRgb}, ${0.72 * alpha})`;
      ctx.fillText(entityLabel, pos.x, pos.y + r + 13);
      ctx.font = "bold 9px Inter, sans-serif";
      ctx.fillStyle = `rgba(${theme.labelRgb}, ${0.84 * alpha})`;
      ctx.fillText(attrLabel, pos.x, pos.y + r + 25);

      // Value below label
      if (n.value !== null && n.value !== undefined) {
        const valStr =
          String(n.value).length > 20
            ? String(n.value).slice(0, 17) + "…"
            : String(n.value);
        ctx.font = "9px 'JetBrains Mono', monospace";
        ctx.fillStyle = `rgba(${theme.mutedLabelRgb}, ${0.7 * alpha})`;
        ctx.fillText(valStr, pos.x, pos.y + r + 37);
      }
    });

    if (frame < totalFrames) {
      requestAnimationFrame(animate);
    }
  }

  animate();
}

$btnHopwalk.addEventListener("click", openHopWalker);
$btnHopwalkClose.addEventListener("click", closeHopWalker);

// Close overlay on backdrop click
$hopwalkOverlay.addEventListener("click", (e) => {
  if (e.target === $hopwalkOverlay) closeHopWalker();
});

// Close on Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && $hopwalkOverlay.style.display !== "none") {
    closeHopWalker();
  }
});

// ── Initial load ────────────────────────────────────────────────────

(async () => {
  await loadModels();
  await loadDomains();
  await refresh();
  // Build attribute chips after initial graph data is loaded
  updateAttributeChips();
  renderExampleRun();

  // Enable chat AFTER initialization is complete
  $chatInput.disabled = false;
  $btnSend.disabled = false;
})();
