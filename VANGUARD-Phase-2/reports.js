import { deriveMainTrigger, getAnalytics, loadState, resetDemo, runAuditUpdate } from "./shared-data.js";

const coverageBlock = document.getElementById("coverageBlock");
const reportMetrics = document.getElementById("reportMetrics");
const distributionBars = document.getElementById("distributionBars");
const distributionLegend = document.getElementById("distributionLegend");
const priorityList = document.getElementById("priorityList");
const trendMetrics = document.getElementById("trendMetrics");
const trendBars = document.getElementById("trendBars");
const accessibilityBreakdown = document.getElementById("accessibilityBreakdown");
const alertList = document.getElementById("alertList");

const runAuditButton = document.getElementById("runAudit");
const loadDemoButton = document.getElementById("loadDemo");
const printTop = document.getElementById("printReportTop");
const printBottom = document.getElementById("printReportBottom");

function renderCoverage(data) {
  coverageBlock.innerHTML = `
    <div><strong>${data.coveragePercent}%</strong> of transit network audited</div>
    <div class="progress-track"><div class="progress-fill" style="width:0%"></div></div>
  `;
  // Animate progress bar
  requestAnimationFrame(() => {
    setTimeout(() => {
      coverageBlock.querySelector(".progress-fill").style.width = `${data.coveragePercent}%`;
    }, 200);
  });
}

function renderMetrics(data) {
  reportMetrics.innerHTML = `
    <div class="metric"><span>Gap Precision</span><span class="value">91.4%</span></div>
    <div class="metric"><span>Silhouette Coherence</span><span class="value">${data.coherence.toFixed(2)}</span></div>
    <div class="metric"><span>Coverage of Network</span><span class="value">${data.coveragePercent}%</span></div>
    <div class="metric"><span>Report Generation Time</span><span class="value">${data.runtime}</span></div>
  `;
}

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

    requestAnimationFrame(() => {
      setTimeout(() => {
        col.querySelector(".bar-shape").style.height = `${targetHeight}px`;
      }, 100 + index * 80);
    });
  });

  distributionLegend.textContent = "Separate report page keeps export content focused.";
}

function renderInterventions(data) {
  priorityList.innerHTML = "";
  data.scoredStops.slice(0, 6).forEach((stop, index) => {
    const node = document.createElement("div");
    node.className = "metric-item";
    node.style.opacity = "0";
    node.style.transform = "translateX(-6px)";
    node.innerHTML = `<span>#${index + 1} ${stop.name}</span><strong>${deriveMainTrigger(stop)}</strong>`;
    priorityList.appendChild(node);

    requestAnimationFrame(() => {
      setTimeout(() => {
        node.style.transition = "opacity 0.35s cubic-bezier(0.22,1,0.36,1), transform 0.35s cubic-bezier(0.22,1,0.36,1)";
        node.style.opacity = "1";
        node.style.transform = "translateX(0)";
      }, 40 + index * 55);
    });
  });
}

function renderTrend(data) {
  trendMetrics.innerHTML = `
    <div class="metric"><span>Previous Average</span><span class="value">${data.trend.previousAverage}</span></div>
    <div class="metric"><span>Current Average</span><span class="value">${data.trend.currentAverage}</span></div>
    <div class="metric"><span>Delta</span><span class="value">${data.trend.delta > 0 ? "+" : ""}${data.trend.delta}</span></div>
  `;

  const beforeHeight = Math.max(data.trend.previousAverage, 8);
  const afterHeight = Math.max(data.trend.currentAverage, 8);
  trendBars.innerHTML = `
    <div class="bar-col"><strong>${data.trend.previousAverage}</strong><div class="bar-shape" style="height:0px; background:#93c5fd"></div><div class="bar-label">Before</div></div>
    <div class="bar-col"><strong>${data.trend.currentAverage}</strong><div class="bar-shape" style="height:0px; background:#2563eb"></div><div class="bar-label">After</div></div>
  `;

  const shapes = trendBars.querySelectorAll(".bar-shape");
  requestAnimationFrame(() => {
    setTimeout(() => { shapes[0].style.height = `${beforeHeight}px`; }, 150);
    setTimeout(() => { shapes[1].style.height = `${afterHeight}px`; }, 250);
  });
}

function renderAccessibilityBreakdown(data) {
  accessibilityBreakdown.innerHTML = `
    <div class="metric"><span>Mobility Score</span><span class="value">${data.accessibilityBreakdown.mobility}%</span></div>
    <div class="metric"><span>Visual Score</span><span class="value">${data.accessibilityBreakdown.visual}%</span></div>
    <div class="metric"><span>Audio Score</span><span class="value">${data.accessibilityBreakdown.audio}%</span></div>
  `;
}

function renderAlerts(data) {
  alertList.innerHTML = "";
  if (data.alerts.length === 0) {
    alertList.innerHTML = '<div class="metric-item"><span>No active critical alerts</span><strong>OK</strong></div>';
    return;
  }

  data.alerts.forEach((alert, index) => {
    const node = document.createElement("div");
    node.className = "metric-item alert-critical";
    node.style.opacity = "0";
    node.style.transform = "translateY(6px)";
    node.innerHTML = `<span>${alert.stopName}: ${alert.message}</span><strong>${alert.confidence}%</strong>`;
    alertList.appendChild(node);

    requestAnimationFrame(() => {
      setTimeout(() => {
        node.style.transition = "opacity 0.35s ease, transform 0.35s ease";
        node.style.opacity = "1";
        node.style.transform = "translateY(0)";
      }, 50 + index * 60);
    });
  });
}

function refresh() {
  const data = getAnalytics();
  renderCoverage(data);
  renderMetrics(data);
  renderDistribution(data);
  renderInterventions(data);
  renderTrend(data);
  renderAccessibilityBreakdown(data);
  renderAlerts(data);
}

runAuditButton.addEventListener("click", () => {
  runAuditUpdate();
  refresh();
});

loadDemoButton.addEventListener("click", () => {
  resetDemo();
  refresh();
});

function printReport() {
  window.print();
}

printTop.addEventListener("click", printReport);
printBottom.addEventListener("click", printReport);

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
