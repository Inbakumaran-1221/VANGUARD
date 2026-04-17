import { getAnalytics, loadState, resetDemo, runAuditUpdate } from "./shared-data.js";

const headlineKPIs = document.getElementById("headlineKPIs");
const distributionBars = document.getElementById("distributionBars");
const distributionLegend = document.getElementById("distributionLegend");
const priorityList = document.getElementById("priorityList");

const runAuditButton = document.getElementById("runAudit");
const loadDemoButton = document.getElementById("loadDemo");
const printTop = document.getElementById("printReportTop");

/* ─── Animated Counter ─── */
function animateCounter(element, target, duration = 900) {
  const start = parseInt(element.textContent, 10) || 0;
  const diff = target - start;
  if (diff === 0) {
    element.textContent = target;
    return;
  }

  const startTime = performance.now();
  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = Math.round(start + diff * eased);
    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      element.textContent = target;
    }
  }
  requestAnimationFrame(step);
}

function animateKpiValues() {
  headlineKPIs.querySelectorAll(".kpi-value").forEach((el) => {
    const text = el.textContent.trim();
    const numericMatch = text.match(/^(\d+)/);
    if (numericMatch) {
      const target = parseInt(numericMatch[1], 10);
      const suffix = text.replace(/^\d+/, "");
      el.textContent = "0" + suffix;
      const startTime = performance.now();
      function step(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / 900, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased) + suffix;
        if (progress < 1) {
          requestAnimationFrame(step);
        } else {
          el.textContent = target + suffix;
        }
      }
      requestAnimationFrame(step);
    }
  });
}

/* ─── KPI Rendering ─── */
function renderKpis(data) {
  const avgConfidence = Math.round(data.scoredStops.reduce((sum, stop) => sum + stop.confidence, 0) / data.scoredStops.length);
  headlineKPIs.innerHTML = `
    <article class="kpi blue">
      <div class="kpi-label">Total Transit Stops</div>
      <div class="kpi-value">${data.scoredStops.length}</div>
      <div class="kpi-sub">Analyzed</div>
    </article>
    <article class="kpi red">
      <div class="kpi-label">Average Score</div>
      <div class="kpi-value">${data.averageScore}</div>
      <div class="kpi-sub">/ 100 needs attention</div>
    </article>
    <article class="kpi red">
      <div class="kpi-label">Critical Gaps</div>
      <div class="kpi-value">${data.criticalCount}</div>
      <div class="kpi-sub">Require immediate action</div>
    </article>
    <article class="kpi orange">
      <div class="kpi-label">Total Grievances</div>
      <div class="kpi-value">${data.totalGrievances}</div>
      <div class="kpi-sub">Includes user feedback</div>
    </article>
    <article class="kpi red">
      <div class="kpi-label">Critical Alerts</div>
      <div class="kpi-value">${data.alerts.length}</div>
      <div class="kpi-sub">Notification triggers</div>
    </article>
    <article class="kpi blue">
      <div class="kpi-label">AI Confidence</div>
      <div class="kpi-value">${avgConfidence}%</div>
      <div class="kpi-sub">Average detection confidence</div>
    </article>
  `;
  animateKpiValues();
}

/* ─── Distribution Chart ─── */
function renderDistribution(data) {
  const entries = [
    { label: "Critical", value: data.distribution.critical, color: "#ef4444" },
    { label: "High", value: data.distribution.high, color: "#f97316" },
    { label: "Medium", value: data.distribution.medium, color: "#eab308" },
    { label: "Low", value: data.distribution.low, color: "#22c55e" }
  ];

  const maxValue = Math.max(...entries.map((entry) => entry.value), 1);
  distributionBars.innerHTML = "";

  entries.forEach((entry, index) => {
    const col = document.createElement("div");
    col.className = "bar-col";
    const targetHeight = Math.max((entry.value / maxValue) * 150, 8);
    col.innerHTML = `
      <strong>${entry.value}</strong>
      <div class="bar-shape" style="height:0px; background:${entry.color};"></div>
      <div class="bar-label">${entry.label}</div>
    `;
    distributionBars.appendChild(col);

    // Animate bar height
    requestAnimationFrame(() => {
      setTimeout(() => {
        col.querySelector(".bar-shape").style.height = `${targetHeight}px`;
      }, 80 + index * 100);
    });
  });

  distributionLegend.textContent = "Click sections in sidebar for complete details.";
}

/* ─── Priority Preview ─── */
function renderPriorityPreview(data) {
  priorityList.innerHTML = "";
  data.scoredStops.slice(0, 5).forEach((stop, index) => {
    const node = document.createElement("div");
    node.className = "metric-item";
    node.style.opacity = "0";
    node.style.transform = "translateX(-8px)";
    node.innerHTML = `<span>#${index + 1} ${stop.name}</span><strong>${stop.priority}</strong>`;
    priorityList.appendChild(node);

    // Stagger animation
    requestAnimationFrame(() => {
      setTimeout(() => {
        node.style.transition = "opacity 0.4s cubic-bezier(0.22,1,0.36,1), transform 0.4s cubic-bezier(0.22,1,0.36,1)";
        node.style.opacity = "1";
        node.style.transform = "translateX(0)";
      }, 60 + index * 70);
    });
  });
}

/* ─── Refresh ─── */
function refresh() {
  const data = getAnalytics();
  renderKpis(data);
  renderDistribution(data);
  renderPriorityPreview(data);
}

runAuditButton.addEventListener("click", () => {
  runAuditUpdate();
  refresh();
});

loadDemoButton.addEventListener("click", () => {
  resetDemo();
  refresh();
});

printTop.addEventListener("click", () => window.print());

window.addEventListener("accessaudit-state-updated", refresh);
window.addEventListener("storage", (event) => {
  if (event.key === "accessaudit-state-v1") {
    refresh();
  }
});

if (!loadState()) {
  resetDemo();
}

refresh();
