import { deriveMainTrigger, getAnalytics, loadState, resetDemo, runAuditUpdate } from "./shared-data.js";

const priorityList = document.getElementById("priorityList");
const scoreTable = document.getElementById("scoreTable");
const selectedStopName = document.getElementById("selectedStopName");
const featureChecklist = document.getElementById("featureChecklist");
const selectedMeta = document.getElementById("selectedMeta");
const confidenceValue = document.getElementById("confidenceValue");
const bboxLayer = document.getElementById("bboxLayer");
const imageSourceText = document.getElementById("imageSourceText");
const scoreBreakdown = document.getElementById("scoreBreakdown");
const evidenceImage = document.getElementById("evidenceImage");

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
let selectedStopId;

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

  const indiaStops = scoredStops.filter((stop) => isIndiaCoordinate(stop.lat, stop.lng));

  if (!map) {
    map = window.L.map("liveMap", {
      zoomControl: true,
      maxBounds: [
        [INDIA_BOUNDS.south, INDIA_BOUNDS.west],
        [INDIA_BOUNDS.north, INDIA_BOUNDS.east]
      ]
    }).setView(INDIA_DEFAULT_VIEW, 5);

    window.L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; OpenStreetMap contributors &copy; CARTO"
    }).addTo(map);
    markerLayer = window.L.layerGroup().addTo(map);
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

function renderScoreBreakdown(stop) {
  scoreBreakdown.innerHTML = `
    <div class="metric"><span>Mobility Score</span><span class="value">${stop.breakdown.mobility}%</span></div>
    <div class="metric"><span>Visual Score</span><span class="value">${stop.breakdown.visual}%</span></div>
    <div class="metric"><span>Audio Score</span><span class="value">${stop.breakdown.audio}%</span></div>
  `;
}

function renderSelectedStop(scoredStops, stopId) {
  const stop = scoredStops.find((candidate) => candidate.id === stopId) ?? scoredStops[0];
  if (!stop) return;
  selectedStopId = stop.id;

  selectedStopName.textContent = `${stop.name} (${stop.priority})`;
  renderFeatureChecklist(stop);
  renderMeta(stop);
  renderEvidence(stop);
  renderScoreBreakdown(stop);
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
