import { getAnalytics, loadState, resetDemo, runAuditUpdate } from "./shared-data.js";

const headlineKPIs = document.getElementById("headlineKPIs");
const distributionBars = document.getElementById("distributionBars");
const distributionLegend = document.getElementById("distributionLegend");
const priorityList = document.getElementById("priorityList");

const runAuditButton = document.getElementById("runAudit");
const loadDemoButton = document.getElementById("loadDemo");
const printTop = document.getElementById("printReportTop");
const generateReportBtn = document.getElementById("generateReportBtn");
const suggestedActionsList = document.getElementById("suggestedActionsList");

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

/* ─── Smart Intervention Planner ─── */
function generateSuggestions(stop) {
  const suggestions = [];
  let estimatedImprovement = 0;

  if (stop.gapScore < 40) {
    suggestions.push("Add ramp and improve pathways");
    estimatedImprovement += 20;
  }
  if (stop.grievanceCount > 10) {
    suggestions.push("High user impact area – prioritize fixes");
    estimatedImprovement += 15;
  }
  if (stop.confidence < 70) {
    suggestions.push("Needs further inspection");
    estimatedImprovement += 5;
  }

  if (suggestions.length === 0) {
    suggestions.push("Standard maintenance check");
    estimatedImprovement += 2;
  }

  return { suggestions, estimatedImprovement };
}

function renderSuggestedActions(data) {
  if (!suggestedActionsList) return;
  suggestedActionsList.innerHTML = "";

  const topStops = data.scoredStops.slice(0, 5);

  topStops.forEach((stop, index) => {
    const { suggestions, estimatedImprovement } = generateSuggestions(stop);

    const node = document.createElement("div");
    node.className = "metric-item";
    node.style.opacity = "0";
    node.style.flexDirection = "column";
    node.style.alignItems = "flex-start";
    
    node.innerHTML = `
      <div style="display: flex; justify-content: space-between; width: 100%;">
        <strong>${stop.name} <span style="font-size:0.75rem; color:var(--muted); margin-left: 0.5rem">${stop.priority}</span></strong>
        <strong style="color:var(--low);">+${estimatedImprovement} score</strong>
      </div>
      <ul style="margin: 0.4rem 0 0 1.2rem; font-size: 0.85em; color: var(--muted);">
        ${suggestions.map(s => `<li>${s}</li>`).join('')}
      </ul>
    `;
    suggestedActionsList.appendChild(node);

    requestAnimationFrame(() => {
      setTimeout(() => {
        node.style.transition = "opacity 0.5s ease-in";
        node.style.opacity = "1";
      }, 100 + index * 100);
    });
  });
}

/* ─── Refresh ─── */
function refresh() {
  const data = getAnalytics();
  renderKpis(data);
  renderDistribution(data);
  renderPriorityPreview(data);
  renderSuggestedActions(data);
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

if (generateReportBtn) {
  generateReportBtn.addEventListener("click", () => {
    if (typeof window.jspdf === "undefined") {
        alert("jsPDF is loading, please try again.");
        return;
    }
    const data = getAnalytics();
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    
    doc.setFont("helvetica", "bold");
    doc.setFontSize(22);
    doc.text("Policy Impact Report", 14, 20);
    
    doc.setFontSize(14);
    doc.text("1. Key Performance Indicators (KPIs)", 14, 35);
    
    doc.setFont("helvetica", "normal");
    doc.setFontSize(12);
    const avgConfidence = Math.round(data.scoredStops.reduce((sum, stop) => sum + stop.confidence, 0) / data.scoredStops.length);
    
    doc.text(`- Total Transit Stops: ${data.scoredStops.length}`, 14, 45);
    doc.text(`- Average Score: ${data.averageScore}`, 14, 52);
    doc.text(`- Critical Gaps: ${data.criticalCount}`, 14, 59);
    doc.text(`- Total Grievances: ${data.totalGrievances}`, 14, 66);
    doc.text(`- AI Confidence: ${avgConfidence}%`, 14, 73);
    
    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.text("2. Priority Stops (Top 5)", 14, 90);
    
    doc.setFont("helvetica", "normal");
    doc.setFontSize(12);
    data.scoredStops.slice(0, 5).forEach((stop, idx) => {
        doc.text(`${idx + 1}. ${stop.name} - Priority: ${stop.priority}`, 14, 100 + (idx * 7));
    });
    
    doc.setFont("helvetica", "bold");
    doc.setFontSize(14);
    doc.text("3. Issue Summary (Distribution)", 14, 145);
    
    doc.setFont("helvetica", "normal");
    doc.setFontSize(12);
    doc.text(`- Critical: ${data.distribution.critical}`, 14, 155);
    doc.text(`- High: ${data.distribution.high}`, 14, 162);
    doc.text(`- Medium: ${data.distribution.medium}`, 14, 169);
    doc.text(`- Low: ${data.distribution.low}`, 14, 176);
    
    doc.save("Policy_Impact_Report.pdf");
  });
}

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
