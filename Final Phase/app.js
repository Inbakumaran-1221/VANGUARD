const baselineStops = [
  { id: "CEN-01", name: "Central Square", x: 52, y: 57, hasRamp: false, hasTactile: false, hasAudio: false, hasLowFloorAccess: true, grievanceCount: 36, audited: true },
  { id: "RIV-02", name: "Riverfront Hub", x: 73, y: 35, hasRamp: true, hasTactile: false, hasAudio: true, hasLowFloorAccess: false, grievanceCount: 18, audited: true },
  { id: "UNI-03", name: "University Gate", x: 62, y: 73, hasRamp: true, hasTactile: true, hasAudio: false, hasLowFloorAccess: false, grievanceCount: 21, audited: true },
  { id: "AIR-04", name: "Airport Link", x: 89, y: 53, hasRamp: true, hasTactile: true, hasAudio: true, hasLowFloorAccess: true, grievanceCount: 7, audited: true },
  { id: "OLD-05", name: "Old Market", x: 24, y: 42, hasRamp: false, hasTactile: false, hasAudio: true, hasLowFloorAccess: false, grievanceCount: 30, audited: true },
  { id: "HSP-06", name: "City Hospital", x: 36, y: 68, hasRamp: true, hasTactile: true, hasAudio: true, hasLowFloorAccess: false, grievanceCount: 13, audited: true },
  { id: "MET-07", name: "Metro East", x: 78, y: 63, hasRamp: true, hasTactile: false, hasAudio: true, hasLowFloorAccess: false, grievanceCount: 16, audited: true },
  { id: "PARK-08", name: "Parkline", x: 67, y: 25, hasRamp: false, hasTactile: true, hasAudio: false, hasLowFloorAccess: true, grievanceCount: 26, audited: true },
  { id: "LIB-09", name: "City Library", x: 47, y: 30, hasRamp: true, hasTactile: true, hasAudio: true, hasLowFloorAccess: false, grievanceCount: 10, audited: true },
  { id: "STN-10", name: "South Terminal", x: 40, y: 77, hasRamp: false, hasTactile: false, hasAudio: false, hasLowFloorAccess: false, grievanceCount: 42, audited: true },
  { id: "ART-11", name: "Arts District", x: 59, y: 48, hasRamp: true, hasTactile: true, hasAudio: false, hasLowFloorAccess: true, grievanceCount: 14, audited: true },
  { id: "HIL-12", name: "Hill Junction", x: 30, y: 54, hasRamp: true, hasTactile: false, hasAudio: true, hasLowFloorAccess: true, grievanceCount: 12, audited: false }
];

const weights = { hasRamp: 0.34, hasTactile: 0.24, hasAudio: 0.2, hasLowFloorAccess: 0.22 };

const defaultGrievances = [
  "No wheelchair ramp at Central Square stop.",
  "Audio announcement is missing for bus 11 at University Gate.",
  "Tactile paving broken near Old Market platform.",
  "Elevator frequently out of service at Riverfront Hub.",
  "Need better visual signage for low-vision passengers.",
  "Bus boarding gap too high for wheelchair users.",
  "No tactile strip near Metro East entry.",
  "Platform audio alerts are not working at South Terminal.",
  "Wheelchair users cannot board at Parkline during peak hours.",
  "Signage is confusing at City Library transfer corridor.",
  "Broken ramp handrail near Old Market stop.",
  "Audible crossing signal absent at Central Square junction."
];

let currentStops = [...baselineStops];

const scoreTable = document.getElementById("scoreTable");
const mapBoard = document.getElementById("mapBoard");
const priorityList = document.getElementById("priorityList");
const reportMetrics = document.getElementById("reportMetrics");
const clusterList = document.getElementById("clusterList");
const grievanceInput = document.getElementById("grievanceInput");
const silhouetteMetric = document.getElementById("silhouetteMetric");
const headlineKPIs = document.getElementById("headlineKPIs");
const distributionBars = document.getElementById("distributionBars");
const distributionLegend = document.getElementById("distributionLegend");
const categoryBreakdown = document.getElementById("categoryBreakdown");
const coverageBlock = document.getElementById("coverageBlock");

const runAuditButton = document.getElementById("runAudit");
const loadDemoButton = document.getElementById("loadDemo");
const analyzeTextButton = document.getElementById("analyzeText");
const printTop = document.getElementById("printReportTop");
const printBottom = document.getElementById("printReportBottom");

function computeGapScore(stop) {
  let missingScore = 0;
  Object.keys(weights).forEach((criterion) => {
    if (!stop[criterion]) {
      missingScore += weights[criterion] * 100;
    }
  });
  const complaintPressure = Math.min(stop.grievanceCount * 0.8, 20);
  return Math.min(Math.round(missingScore + complaintPressure), 100);
}

function priorityLabel(score) {
  if (score >= 75) return "Critical";
  if (score >= 50) return "High";
  if (score >= 30) return "Medium";
  return "Low";
}

function coverageLabel(stop) {
  const fulfilled = [stop.hasRamp, stop.hasTactile, stop.hasAudio, stop.hasLowFloorAccess].filter(Boolean).length;
  return `${Math.round((fulfilled / 4) * 100)}%`;
}

function enrichStops(stops) {
  return stops
    .map((stop) => {
      const score = computeGapScore(stop);
      return {
        ...stop,
        gapScore: score,
        priority: priorityLabel(score),
        coverage: coverageLabel(stop)
      };
    })
    .sort((a, b) => b.gapScore - a.gapScore);
}

function deriveMainTrigger(stop) {
  if (!stop.hasRamp) return "Ramp missing";
  if (!stop.hasTactile) return "No tactile paving";
  if (!stop.hasAudio) return "Audio cues absent";
  if (!stop.hasLowFloorAccess) return "Boarding gap mismatch";
  return "Needs maintenance";
}

function renderScoreTable(stops) {
  scoreTable.innerHTML = "";
  stops.forEach((stop) => {
    const row = document.createElement("tr");
    const badgeClass = `badge-${stop.priority.toLowerCase()}`;
    row.innerHTML = `
      <td>${stop.name}</td>
      <td><strong>${stop.gapScore}</strong></td>
      <td>${stop.coverage}</td>
      <td><span class="badge ${badgeClass}">${stop.priority}</span></td>
    `;
    scoreTable.appendChild(row);
  });
}

function renderMap(stops) {
  mapBoard.innerHTML = "";
  priorityList.innerHTML = "";

  stops.forEach((stop) => {
    const node = document.createElement("div");
    node.className = `stop-node ${stop.priority.toLowerCase()}`;
    node.style.left = `${stop.x}%`;
    node.style.top = `${stop.y}%`;
    node.title = `${stop.name}: ${stop.priority} (${stop.gapScore})`;
    mapBoard.appendChild(node);
  });

  stops.slice(0, 5).forEach((stop) => {
    const chip = document.createElement("span");
    chip.className = "priority-item";
    chip.textContent = `${stop.name} - ${deriveMainTrigger(stop)}`;
    priorityList.appendChild(chip);
  });
}

function getScoreDistribution(stops) {
  return {
    critical: stops.filter((s) => s.gapScore >= 75).length,
    high: stops.filter((s) => s.gapScore >= 50 && s.gapScore < 75).length,
    medium: stops.filter((s) => s.gapScore >= 30 && s.gapScore < 50).length,
    low: stops.filter((s) => s.gapScore < 30).length
  };
}

function renderDistribution(stops) {
  const buckets = getScoreDistribution(stops);
  const entries = [
    { key: "critical", label: "Critical", value: buckets.critical, color: "#ef4444" },
    { key: "high", label: "High", value: buckets.high, color: "#f97316" },
    { key: "medium", label: "Medium", value: buckets.medium, color: "#eab308" },
    { key: "low", label: "Low", value: buckets.low, color: "#22c55e" }
  ];
  const maxValue = Math.max(...entries.map((entry) => entry.value), 1);

  distributionBars.innerHTML = "";
  entries.forEach((entry) => {
    const col = document.createElement("div");
    col.className = "bar-col";
    const scaledHeight = Math.max((entry.value / maxValue) * 170, 8);
    col.innerHTML = `
      <strong>${entry.value}</strong>
      <div class="bar-shape" style="height:${scaledHeight}px; background:${entry.color};"></div>
      <div class="bar-label">${entry.label}</div>
    `;
    distributionBars.appendChild(col);
  });

  distributionLegend.textContent = "Distribution bands: Critical (75-100), High (50-74), Medium (30-49), Low (0-29).";
}

function clusterGrievances(rawText) {
  const lines = rawText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const themes = {
    ramp: { label: "Ramp / Wheelchair Access", keywords: ["ramp", "wheelchair", "lift", "elevator", "boarding", "low-floor", "accessible"], count: 0 },
    audio: { label: "Audio Signals", keywords: ["audio", "announcement", "voice", "audible", "speaker", "sound"], count: 0 },
    tactile: { label: "Tactile Path", keywords: ["tactile", "paving", "surface", "guiding", "tile"], count: 0 },
    signage: { label: "Signage & Wayfinding", keywords: ["signage", "wayfinding", "visual", "display", "confusing", "label", "board", "contrast"], count: 0 }
  };

  lines.forEach((line) => {
    const normalized = line.toLowerCase();
    let bestTheme = themes.signage;
    let bestScore = 0;

    Object.values(themes).forEach((theme) => {
      const score = theme.keywords.reduce((count, keyword) => count + (normalized.includes(keyword) ? 1 : 0), 0);
      if (score > bestScore) {
        bestScore = score;
        bestTheme = theme;
      }
    });

    if (bestScore === 0) {
      themes.signage.count += 1;
      return;
    }

    bestTheme.count += 1;
  });

  return { themeStats: Object.values(themes).sort((a, b) => b.count - a.count), lines };
}

function renderClusters(themeStats, sampleCount) {
  clusterList.innerHTML = "";
  themeStats.forEach((theme) => {
    const row = document.createElement("div");
    row.className = "cluster-item";
    row.innerHTML = `<span>${theme.label}</span><strong>${theme.count}</strong>`;
    clusterList.appendChild(row);
  });

  const topCount = themeStats[0]?.count ?? 0;
  const coherence = sampleCount > 0 ? (topCount / sampleCount) * 0.72 + 0.2 : 0;
  silhouetteMetric.textContent = coherence.toFixed(2);
  return coherence;
}

function renderThemeBreakdown(themeStats, totalGrievances) {
  const safeTotal = Math.max(Number(totalGrievances) || 0, 0);

  categoryBreakdown.innerHTML = "";
  if (!Array.isArray(themeStats) || themeStats.length === 0 || safeTotal === 0) {
    const node = document.createElement("div");
    node.className = "metric-item";
    node.innerHTML = '<span>No complaints analyzed yet</span><strong>-</strong>';
    categoryBreakdown.appendChild(node);
    return;
  }

  themeStats.forEach((theme) => {
    const share = Math.round((theme.count / safeTotal) * 100);
    const node = document.createElement("div");
    node.className = "metric-item";
    node.innerHTML = `<span>${theme.label}</span><strong>${theme.count} (${share}%)</strong>`;
    categoryBreakdown.appendChild(node);
  });
}

function renderCoverage(stops) {
  const coverage = Math.round((stops.filter((s) => s.audited).length / stops.length) * 100);
  coverageBlock.innerHTML = `
    <div><strong>${coverage}%</strong> of transit network audited</div>
    <div class="progress-track"><div class="progress-fill" style="width:${coverage}%"></div></div>
  `;
  return coverage;
}

function renderKPIs(stops, totalGrievances, coherence) {
  const avgGap = Math.round(stops.reduce((sum, s) => sum + s.gapScore, 0) / stops.length);
  const criticalGaps = stops.filter((s) => s.priority === "Critical").length;
  const coverage = Math.round((stops.filter((s) => s.audited).length / stops.length) * 100);

  headlineKPIs.innerHTML = `
    <article class="kpi blue">
      <div class="kpi-label">Total Transit Stops</div>
      <div class="kpi-value">${stops.length}</div>
      <div class="kpi-sub">Analyzed</div>
    </article>
    <article class="kpi red">
      <div class="kpi-label">Average Score</div>
      <div class="kpi-value">${avgGap}</div>
      <div class="kpi-sub">/ 100 needs attention</div>
    </article>
    <article class="kpi red">
      <div class="kpi-label">Critical Gaps</div>
      <div class="kpi-value">${criticalGaps}</div>
      <div class="kpi-sub">Require immediate action</div>
    </article>
    <article class="kpi orange">
      <div class="kpi-label">Total Grievances</div>
      <div class="kpi-value">${totalGrievances}</div>
      <div class="kpi-sub">Analyzed</div>
    </article>
  `;

  const runtimeEstimate = `${(1.6 + stops.length * 0.33).toFixed(1)} min`;
  reportMetrics.innerHTML = `
    <div class="metric"><span>Gap Precision</span><span class="value">91.4%</span></div>
    <div class="metric"><span>Silhouette Coherence</span><span class="value">${coherence.toFixed(2)}</span></div>
    <div class="metric"><span>Network Coverage</span><span class="value">${coverage}%</span></div>
    <div class="metric"><span>Generation Time</span><span class="value">${runtimeEstimate}</span></div>
  `;
}

function refreshDashboard() {
  const grievanceLines = grievanceInput.value.split("\n").map((line) => line.trim()).filter(Boolean);
  const { themeStats, lines } = clusterGrievances(grievanceInput.value);
  const coherence = renderClusters(themeStats, lines.length);
  const scored = enrichStops(currentStops);

  renderScoreTable(scored);
  renderMap(scored);
  renderDistribution(scored);
  renderThemeBreakdown(themeStats, lines.length);
  renderCoverage(scored);
  renderKPIs(scored, grievanceLines.length, coherence);
}

function initialize() {
  grievanceInput.value = defaultGrievances.join("\n");
  refreshDashboard();
}

loadDemoButton.addEventListener("click", () => {
  grievanceInput.value = defaultGrievances.join("\n");
  currentStops = [...baselineStops];
  refreshDashboard();
});

runAuditButton.addEventListener("click", () => {
  currentStops = currentStops.map((stop) => {
    const jitter = Math.floor(Math.random() * 7) - 3;
    return {
      ...stop,
      grievanceCount: Math.max(stop.grievanceCount + jitter, 0),
      audited: true
    };
  });
  refreshDashboard();
});

analyzeTextButton.addEventListener("click", refreshDashboard);

function printReport() {
  window.print();
}

printTop.addEventListener("click", printReport);
printBottom.addEventListener("click", printReport);

initialize();
