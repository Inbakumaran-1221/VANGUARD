import { deriveMainTrigger, getAnalytics, loadState, resetDemo, runAuditUpdate, resolveApiBase } from "./shared-data.js";

const priorityList = document.getElementById("priorityList");
const scoreTable = document.getElementById("scoreTable");
const selectedStopName = document.getElementById("selectedStopName");
const featureChecklist = document.getElementById("featureChecklist");
const selectedMeta = document.getElementById("selectedMeta");
const confidenceValue = document.getElementById("confidenceValue");
const bboxLayer = document.getElementById("bboxLayer");
const imageSourceText = document.getElementById("imageSourceText");
const xaiBreakdown = document.getElementById("xaiBreakdown");
const remediationList = document.getElementById("remediationList");
const evidenceImage = document.getElementById("evidenceImage");
const trendChartCanvas = document.getElementById("trendChart");

const runAuditButton = document.getElementById("runAudit");
const loadDemoButton = document.getElementById("loadDemo");
const printTop = document.getElementById("printReportTop");

const evidenceImages = [
  "https://images.unsplash.com/photo-1519003722824-194d4455a60c?auto=format&fit=crop&w=900&q=60",
  "https://images.unsplash.com/photo-1489515217757-5fd1be406fef?auto=format&fit=crop&w=900&q=60",
  "https://images.unsplash.com/photo-1486325212027-8081e485255e?auto=format&fit=crop&w=900&q=60"
];

let map;
let markerLayer;
let liveFeedbackLayer;
let selectedStopId;
let trendChartInstance = null;

const priorityMapToggle = document.getElementById("priorityMapToggle");
if (priorityMapToggle) {
    priorityMapToggle.addEventListener("change", refresh);
}

const INDIA_BOUNDS = {
  north: 37.6,
  south: 6.4,
  west: 68.1,
  east: 97.5
};

const INDIA_DEFAULT_VIEW = [22.8, 79.8];

function isIndiaCoordinate(lat, lng) {
  return lat >= INDIA_BOUNDS.south && lat <= INDIA_BOUNDS.north && lng >= INDIA_BOUNDS.west && lng <= INDIA_BOUNDS.east;
}

function getEnglishLabel(text) {
  if (typeof text !== "string") return "Unknown Stop";
  const cleaned = text.normalize("NFKD").replace(/[^\x00-\x7F]/g, "").trim();
  return cleaned || "Unknown Stop";
}

function getMarkerColor(priority) {
  if (priority === "Critical") return "#ef4444";
  if (priority === "High") return "#f97316";
  if (priority === "Medium") return "#eab308";
  return "#22c55e";
}

function renderMap(scoredStops, onSelect) {
  if (typeof window.L === "undefined") {
    return;
  }

  const isPriorityMode = priorityMapToggle?.checked;
  const filterStops = isPriorityMode ? scoredStops.filter(s => s.priority === "Critical") : scoredStops;
  const indiaStops = filterStops.filter((stop) => isIndiaCoordinate(stop.lat, stop.lng));

  if (!map) {
    map = window.L.map("liveMap", {
      zoomControl: true,
      maxBounds: [
        [INDIA_BOUNDS.south, INDIA_BOUNDS.west],
        [INDIA_BOUNDS.north, INDIA_BOUNDS.east]
      ]
    }).setView(INDIA_DEFAULT_VIEW, 5);

    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(map);
    markerLayer = window.L.layerGroup().addTo(map);
    liveFeedbackLayer = window.L.layerGroup().addTo(map);

    setInterval(() => {
        const isPriorityMode = priorityMapToggle?.checked;
        renderLiveFeedbacks(isPriorityMode);
    }, 5000);
  }

  markerLayer.clearLayers();
  indiaStops.forEach((stop) => {
    const displayName = getEnglishLabel(stop.name);
    const color = getMarkerColor(stop.priority);
    const marker = window.L.circleMarker([stop.lat, stop.lng], {
      radius: 8,
      color: "#fff",
      weight: 2,
      fillColor: color,
      fillOpacity: 0.95
    });

    marker.bindTooltip(`${displayName} • ${stop.priority} • score ${stop.gapScore}`);
    marker.on("click", () => onSelect(stop.id));
    markerLayer.addLayer(marker);
  });

  if (indiaStops.length > 0) {
    const bounds = window.L.latLngBounds(indiaStops.map((stop) => [stop.lat, stop.lng]));
    map.fitBounds(bounds.pad(0.2));
  } else {
    map.setView(INDIA_DEFAULT_VIEW, 5);
  }
  
  renderLiveFeedbacks(isPriorityMode);
}

async function renderLiveFeedbacks(isPriorityMode) {
  if (!liveFeedbackLayer) return;
  const apiBase = await resolveApiBase();
  if (!apiBase) return;
  try {
      const res = await fetch(`${apiBase}/feedback?limit=50`);
      if (!res.ok) return;
      const data = await res.json();
      liveFeedbackLayer.clearLayers();
      (data.items || []).forEach(fb => {
          if (fb.lat && fb.lng && isIndiaCoordinate(fb.lat, fb.lng)) {
              if (isPriorityMode && fb.severity !== "critical") return;
              const color = getMarkerColor(fb.severity.charAt(0).toUpperCase() + fb.severity.slice(1));
              const marker = window.L.circleMarker([fb.lat, fb.lng], {
                  radius: 6,
                  color: "#000",
                  weight: 2,
                  fillColor: color,
                  fillOpacity: 0.95
              });
              marker.bindTooltip(`Live Grievance: ${fb.message} <br/> Severity: ${fb.severity}`);
              liveFeedbackLayer.addLayer(marker);
          }
      });
  } catch(e) {
      // suppress
  }
}

function renderPriority(scoredStops) {
  priorityList.innerHTML = "";
  scoredStops.slice(0, 6).forEach((stop, index) => {
    const item = document.createElement("div");
    item.className = "metric-item";
    item.style.opacity = "0";
    item.style.transform = "translateX(-6px)";
    item.innerHTML = `<span>#${index + 1} ${stop.name}</span><strong>${deriveMainTrigger(stop)}</strong>`;
    priorityList.appendChild(item);

    requestAnimationFrame(() => {
      setTimeout(() => {
        item.style.transition = "opacity 0.35s cubic-bezier(0.22,1,0.36,1), transform 0.35s cubic-bezier(0.22,1,0.36,1)";
        item.style.opacity = "1";
        item.style.transform = "translateX(0)";
      }, 40 + index * 55);
    });
  });
}

function renderTable(scoredStops, onSelect) {
  scoreTable.innerHTML = "";
  scoredStops.forEach((stop) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td><button class="link-button" data-stop-id="${stop.id}">${stop.name}</button></td>
      <td><strong>${stop.gapScore}</strong></td>
      <td>${stop.confidence}%</td>
      <td>${stop.coverage}</td>
      <td><span class="badge badge-${stop.priority.toLowerCase()}">${stop.priority}</span></td>
    `;
    scoreTable.appendChild(row);

    const selectButton = row.querySelector("button[data-stop-id]");
    selectButton.addEventListener("click", () => onSelect(stop.id));
  });
}

function renderFeatureChecklist(stop) {
  const items = [
    { label: "Ramp", value: stop.hasRamp },
    { label: "Elevator", value: stop.hasElevator },
    { label: "Tactile Path", value: stop.hasTactile },
    { label: "Braille", value: stop.hasBraille },
    { label: "Audio", value: stop.hasAudio },
    { label: "Low Floor", value: stop.hasLowFloorAccess }
  ];

  featureChecklist.innerHTML = "";
  items.forEach((item, index) => {
    const node = document.createElement("div");
    node.className = `check-item ${item.value ? "ok" : "missing"}`;
    node.style.opacity = "0";
    node.style.transform = "scale(0.92)";
    node.innerHTML = `<span>${item.label}</span><strong>${item.value ? "✔" : "✖"}</strong>`;
    featureChecklist.appendChild(node);

    requestAnimationFrame(() => {
      setTimeout(() => {
        node.style.transition = "opacity 0.3s ease, transform 0.3s cubic-bezier(0.34,1.56,0.64,1)";
        node.style.opacity = "1";
        node.style.transform = "scale(1)";
      }, 30 + index * 40);
    });
  });
}

function renderMeta(stop) {
  selectedMeta.innerHTML = `
    <div class="metric-item"><span>Coordinates</span><strong>${stop.lat.toFixed(4)}, ${stop.lng.toFixed(4)}</strong></div>
    <div class="metric-item"><span>Last Updated</span><strong>${new Date(stop.lastUpdated).toLocaleString()}</strong></div>
    <div class="metric-item"><span>Gap Formula</span><strong>${stop.missingFeatures} + ${stop.severityWeight}</strong></div>
  `;
}

function renderEvidence(stop) {
  confidenceValue.textContent = `${stop.confidence}%`;
  imageSourceText.textContent = `Source: ${stop.imageSource}`;
  evidenceImage.src = evidenceImages[Math.abs(stop.id.split("")[0].charCodeAt(0)) % evidenceImages.length];

  bboxLayer.innerHTML = "";
  (stop.evidence ?? []).forEach((item) => {
    const box = document.createElement("div");
    box.className = "bbox";
    box.style.left = `${item.box[0]}%`;
    box.style.top = `${item.box[1]}%`;
    box.style.width = `${item.box[2]}%`;
    box.style.height = `${item.box[3]}%`;
    box.innerHTML = `<span>${item.label} (${Math.round(item.confidence * 100)}%)</span>`;
    bboxLayer.appendChild(box);
  });
}

function renderXAIBreakdown(stop) {
  xaiBreakdown.innerHTML = `
    <div class="metric"><span>Mobility Sub-score</span><span class="value">${stop.breakdown.mobility}%</span></div>
    <div class="metric"><span>Visual Sub-score</span><span class="value">${stop.breakdown.visual}%</span></div>
    <div class="metric"><span>Audio Sub-score</span><span class="value">${stop.breakdown.audio}%</span></div>
  `;
  
  const deductionsHtml = (stop.deductions || []).map(d => `<div class="metric-item" style="font-size:0.8rem; margin-top:0.25rem;"><span>${d}</span></div>`).join("");
  
  if (deductionsHtml) {
      xaiBreakdown.innerHTML += `
        <div style="margin-top: 1rem; padding-top: 0.5rem; border-top: 1px solid var(--line);">
           <strong style="font-size:0.82rem; color: var(--muted); text-transform: uppercase;">Deduction Reasons:</strong>
           ${deductionsHtml}
        </div>
      `;
  }
}

function renderRemediation(stop) {
  if (!remediationList) return;
  remediationList.innerHTML = "";
  
  if (!stop.suggestions || stop.suggestions.length === 0) {
      remediationList.innerHTML = '<div class="metric-item"><span>Stop is fully accessible!</span></div>';
      return;
  }
  
  stop.suggestions.slice(0, 4).forEach((sug) => {
     const node = document.createElement("div");
     node.className = "metric-item";
     node.innerHTML = `<span style="font-size:0.8rem; overflow:hidden; text-overflow:ellipsis; max-width:70%; white-space:nowrap;">${sug.fix}</span><strong style="color:var(--low);">-${sug.improvement} pts</strong>`;
     remediationList.appendChild(node);
  });
}

function renderTrendChart(stop) {
  if (!trendChartCanvas || typeof window.Chart === "undefined") return;
  const ctx = trendChartCanvas.getContext("2d");
  
  if (trendChartInstance) {
    trendChartInstance.destroy();
  }

  const pastScores = stop.trend || [];
  const currentScore = stop.gapScore;
  
  let predictedScore = currentScore;
  if (pastScores.length > 0) {
      const lastPast = pastScores[pastScores.length - 1];
      const delta = currentScore - lastPast;
      predictedScore = Math.max(0, Math.min(100, currentScore + delta));
  }

  const labels = pastScores.map((_, i) => `T-${pastScores.length - i}`).concat(["Current", "Predicted"]);
  const dataPoints = [...pastScores, currentScore, predictedScore];

  const pointBgColors = dataPoints.map((_, i) => i === dataPoints.length - 1 ? '#f97316' : (i === dataPoints.length - 2 ? '#2563eb' : '#94a3b8'));
  const pointSizes = dataPoints.map((_, i) => i >= dataPoints.length - 2 ? 6 : 4);

  trendChartInstance = new window.Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Gap Score',
        data: dataPoints,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        fill: true,
        pointBackgroundColor: pointBgColors,
        pointRadius: pointSizes,
        pointHoverRadius: 8,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
            callbacks: {
                label: function(context) {
                    if (context.dataIndex === dataPoints.length - 1) return `Predicted: ${context.parsed.y}`;
                    if (context.dataIndex === dataPoints.length - 2) return `Current: ${context.parsed.y}`;
                    return `Past Score: ${context.parsed.y}`;
                }
            }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          ticks: { stepSize: 20 }
        }
      }
    }
  });
}

function renderSelectedStop(scoredStops, stopId) {
  const stop = scoredStops.find((candidate) => candidate.id === stopId) ?? scoredStops[0];
  if (!stop) return;
  selectedStopId = stop.id;

  selectedStopName.textContent = `${stop.name} (${stop.priority})`;
  renderFeatureChecklist(stop);
  renderMeta(stop);
  renderEvidence(stop);
  renderXAIBreakdown(stop);
  renderRemediation(stop);
  renderTrendChart(stop);
}

function refresh() {
  const data = getAnalytics();
  renderMap(data.scoredStops, (stopId) => renderSelectedStop(data.scoredStops, stopId));
  renderPriority(data.scoredStops);
  renderTable(data.scoredStops, (stopId) => renderSelectedStop(data.scoredStops, stopId));
  renderSelectedStop(data.scoredStops, selectedStopId);
}

runAuditButton.addEventListener("click", () => {
  runAuditUpdate();
  refresh();
});

loadDemoButton.addEventListener("click", () => {
  resetDemo();
  refresh();
});

async function generatePDFReport() {
    const data = getAnalytics();
    if (!selectedStopId) {
        alert("Please select a stop to export a report.");
        return;
    }
    const stop = data.scoredStops.find(s => s.id === selectedStopId);
    if (!stop) return;
    
    if (typeof pdfMake === "undefined") {
        alert("pdfMake is still loading. Please try again.");
        return;
    }

    const docDefinition = {
      content: [
           { text: `AccessAudit Report: ${stop.name}`, style: 'header' },
           { text: `Accessibility Gap Score: ${stop.gapScore}`, style: 'subheader' },
           { text: `Priority Level: ${stop.priority}`, margin: [0, 5, 0, 15] },
           { text: 'Top Grievance Themes in Network', style: 'sectionHeader' },
           {
               ul: data.themeStats.slice(0,3).map(t => `${t.label}: ${t.count} mentions`)
           },
           { text: 'Recent Verified Uploads', style: 'sectionHeader', margin: [0, 15, 0, 5] },
           {
               ol: data.state.userFeedback.slice(0,5).map(fb => `[${fb.severity.toUpperCase()}] ${fb.message}`)
           }
      ],
      styles: {
         header: { fontSize: 22, bold: true, margin: [0, 0, 0, 10] },
         subheader: { fontSize: 16, bold: true, margin: [0, 10, 0, 5] },
         sectionHeader: { fontSize: 14, bold: true, decoration: 'underline', margin: [0, 10, 0, 5] }
      }
    };
    pdfMake.createPdf(docDefinition).download(`Audit_${stop.name.replace(/\s+/g, '_')}.pdf`);
}

printTop.addEventListener("click", generatePDFReport);

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
