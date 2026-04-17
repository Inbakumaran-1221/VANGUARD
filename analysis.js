const printTop = document.getElementById("printReportTop");
const imageUpload = document.getElementById("imageUpload");
const datasetSelector = document.getElementById("datasetSelector");
const runImageAnalysisButton = document.getElementById("runImageAnalysis");
const loadDatasetButton = document.getElementById("loadDataset");

const analysisStatus = document.getElementById("analysisStatus");
const analysisFeatures = document.getElementById("analysisFeatures");
const analysisGaps = document.getElementById("analysisGaps");
const detectionsTable = document.getElementById("detectionsTable");
const analysisPreview = document.getElementById("analysisPreview");
const analysisBboxLayer = document.getElementById("analysisBboxLayer");
const analysisSource = document.getElementById("analysisSource");
const analysisScore = document.getElementById("analysisScore");
const analysisConfidence = document.getElementById("analysisConfidence");
const analysisConfidenceValue = document.getElementById("analysisConfidenceValue");
const datasetSummary = document.getElementById("datasetSummary");

const configuredApiBase = import.meta.env.VITE_API_URL;

const API_BASE_CANDIDATES = [
  configuredApiBase,
  "http://127.0.0.1:5001",
  "http://127.0.0.1:5002",
  "http://127.0.0.1:5003",
  "http://127.0.0.1:5004",
  "http://127.0.0.1:5005",
  "http://127.0.0.1:5006",
  "http://127.0.0.1:5007",
  "http://127.0.0.1:5008",
  "http://127.0.0.1:5009",
  "http://127.0.0.1:5010"
].filter(Boolean);
const API_HEALTH_RETRIES = 18;
const API_HEALTH_DELAY_MS = 500;
const DATASET_SAMPLES = [
  {
    label: "Wheelchair Boarding Area",
    url: "assets/dataset-samples/sample-ramp.jpg"
  },
  {
    label: "Transit Platform Walkway",
    url: "assets/dataset-samples/sample-tactile.jpg"
  },
  {
    label: "Crossing and Sidewalk Zone",
    url: "assets/dataset-samples/sample-stairs.jpg"
  }
];

let selectedImageFile = null;
let selectedImageLabel = "dataset sample";
let selectedDatasetFiles = [];
let activeDatasetIndex = 0;
let detectedImageWidth = 1;
let detectedImageHeight = 1;
let activeApiBase = API_BASE_CANDIDATES[0];

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isSupportedImageFile(file) {
  if (!file) return false;
  if (file.type.startsWith("image/")) return true;
  return /\.(png|jpe?g|webp|gif|bmp|avif)$/i.test(file.name);
}

function refreshDatasetSummary() {
  if (selectedDatasetFiles.length === 0) {
    datasetSummary.textContent = "No dataset selected yet.";
    datasetSelector.innerHTML = "";
    datasetSelector.disabled = true;
    return;
  }

  datasetSelector.disabled = false;
  datasetSummary.textContent = `${selectedDatasetFiles.length} image${selectedDatasetFiles.length === 1 ? "" : "s"} loaded. Previewing ${selectedImageLabel}.`;
}

function setActiveDatasetFile(index) {
  if (selectedDatasetFiles.length === 0) {
    selectedImageFile = null;
    selectedImageLabel = "dataset sample";
    refreshDatasetSummary();
    return;
  }

  const boundedIndex = Math.max(0, Math.min(index, selectedDatasetFiles.length - 1));
  activeDatasetIndex = boundedIndex;
  const file = selectedDatasetFiles[boundedIndex];
  selectedImageFile = file;
  selectedImageLabel = file.name;
  analysisPreview.src = URL.createObjectURL(file);
  analysisSource.textContent = `Source: ${file.name}`;

  datasetSelector.innerHTML = selectedDatasetFiles
    .map((entry, entryIndex) => `<option value="${entryIndex}" ${entryIndex === boundedIndex ? "selected" : ""}>${entry.name}</option>`)
    .join("");
  refreshDatasetSummary();

  setStatus([
    { label: "Selected", value: file.name },
    { label: "Dataset", value: `${selectedDatasetFiles.length} file${selectedDatasetFiles.length === 1 ? "" : "s"}` },
    { label: "Ready", value: "Click Run Analysis" }
  ]);
}

async function loadDatasetFiles(files, sourceLabel) {
  const imageFiles = Array.from(files ?? []).filter(isSupportedImageFile);
  if (imageFiles.length === 0) {
    selectedDatasetFiles = [];
    selectedImageFile = null;
    selectedImageLabel = "dataset sample";
    datasetSummary.textContent = `No image files found in ${sourceLabel}.`;
    datasetSelector.innerHTML = "";
    datasetSelector.disabled = true;
    setStatus([
      { label: "Dataset", value: `No images in ${sourceLabel}` },
      { label: "Action", value: "Choose PNG, JPG, WebP, GIF, or BMP files" }
    ]);
    return;
  }

  selectedDatasetFiles = imageFiles;
  await setActiveDatasetFile(0);
  datasetSummary.textContent = `${selectedDatasetFiles.length} image${selectedDatasetFiles.length === 1 ? "" : "s"} loaded from ${sourceLabel}.`;
}

function setStatus(items) {
  analysisStatus.innerHTML = "";
  items.forEach((item) => {
    const node = document.createElement("div");
    node.className = "metric-item";
    node.innerHTML = `<span>${item.label}</span><strong>${item.value}</strong>`;
    analysisStatus.appendChild(node);
  });
}

function renderFeatures(features) {
  const ordered = [
    { key: "ramp", label: "Ramp" },
    { key: "stairs", label: "Stairs" },
    { key: "tactile", label: "Tactile Path" },
    { key: "braille", label: "Braille" }
  ];

  analysisFeatures.innerHTML = "";
  ordered.forEach((entry) => {
    const rawValue = features?.[entry.key];
    const isUnknown = rawValue === null || rawValue === undefined;
    const enabled = rawValue === true;
    const node = document.createElement("div");
    node.className = `check-item ${isUnknown ? "unknown" : enabled ? "ok" : "missing"}`;
    node.innerHTML = `<span>${entry.label}</span><strong>${isUnknown ? "?" : enabled ? "✔" : "✖"}</strong>`;
    analysisFeatures.appendChild(node);
  });
}

function renderGaps(gaps) {
  analysisGaps.innerHTML = "";
  if (!gaps || gaps.length === 0) {
    const okNode = document.createElement("div");
    okNode.className = "metric-item";
    okNode.innerHTML = "<span>Gap Status</span><strong>No critical gaps detected</strong>";
    analysisGaps.appendChild(okNode);
    return;
  }

  gaps.forEach((gap) => {
    const node = document.createElement("div");
    node.className = "metric-item alert-critical";
    node.innerHTML = `<span>Gap</span><strong>${gap}</strong>`;
    analysisGaps.appendChild(node);
  });
}

function renderDetections(detections) {
  detectionsTable.innerHTML = "";
  if (!detections || detections.length === 0) {
    const empty = document.createElement("tr");
    empty.innerHTML = "<td colspan=\"3\">No objects detected. Try lower confidence, clearer image, or a custom accessibility model.</td>";
    detectionsTable.appendChild(empty);
    return;
  }

  detections.forEach((det) => {
    const row = document.createElement("tr");
    const bbox = `${det.bbox.x1}, ${det.bbox.y1}, ${det.bbox.x2}, ${det.bbox.y2}`;
    row.innerHTML = `
      <td>${det.class}</td>
      <td>${Math.round(det.confidence * 100)}%</td>
      <td>${bbox}</td>
    `;
    detectionsTable.appendChild(row);
  });
}

function renderOverlayBoxes(detections) {
  analysisBboxLayer.innerHTML = "";
  if (!detections || detections.length === 0 || detectedImageWidth <= 1 || detectedImageHeight <= 1) {
    return;
  }

  detections.forEach((det) => {
    const left = (det.bbox.x1 / detectedImageWidth) * 100;
    const top = (det.bbox.y1 / detectedImageHeight) * 100;
    const width = ((det.bbox.x2 - det.bbox.x1) / detectedImageWidth) * 100;
    const height = ((det.bbox.y2 - det.bbox.y1) / detectedImageHeight) * 100;

    const box = document.createElement("div");
    box.className = "bbox";
    box.style.left = `${Math.max(0, left)}%`;
    box.style.top = `${Math.max(0, top)}%`;
    box.style.width = `${Math.max(2, width)}%`;
    box.style.height = `${Math.max(2, height)}%`;
    box.innerHTML = `<span>${det.class} (${Math.round(det.confidence * 100)}%)</span>`;
    analysisBboxLayer.appendChild(box);
  });
}

function computeAccessibilityScore(features) {
  const checks = ["ramp", "tactile", "braille"];
  const knownValues = checks
    .map((key) => features?.[key])
    .filter((value) => value === true || value === false);

  if (knownValues.length === 0) {
    return null;
  }

  const positives = knownValues.filter((value) => value === true).length;
  return Math.round((positives / knownValues.length) * 100);
}

async function resolveApiBase() {
  for (const candidate of API_BASE_CANDIDATES) {
    for (let attempt = 0; attempt < API_HEALTH_RETRIES; attempt += 1) {
      try {
        const response = await fetch(`${candidate}/health`);
        if (response.ok) {
          activeApiBase = candidate;
          return candidate;
        }
      } catch {
        // Try again after a short delay in case the backend is still booting.
      }
      await delay(API_HEALTH_DELAY_MS);
    }
  }
  throw new Error("Backend unavailable. Start npm run dev or npm run backend:dev and wait for the backend to finish starting.");
}

async function pickSampleAsFile(sample) {
  const response = await fetch(sample.url);
  const blob = await response.blob();
  const file = new File([blob], `${sample.label.toLowerCase().replace(/\s+/g, "-")}.jpg`, {
    type: blob.type || "image/jpeg"
  });
  selectedDatasetFiles = [file];
  selectedImageFile = file;
  selectedImageLabel = sample.label;
  activeDatasetIndex = 0;
  analysisPreview.src = URL.createObjectURL(file);
  analysisSource.textContent = `Source: ${sample.label}`;
  datasetSelector.innerHTML = `<option value="0" selected>${sample.label}</option>`;
  datasetSelector.disabled = false;
  refreshDatasetSummary();
}

async function loadDataset() {
  const sampleFiles = await Promise.all(DATASET_SAMPLES.map(async (sample) => {
    const response = await fetch(sample.url);
    const blob = await response.blob();
    return new File([blob], `${sample.label.toLowerCase().replace(/\s+/g, "-")}.jpg`, {
      type: blob.type || "image/jpeg"
    });
  }));

  selectedDatasetFiles = sampleFiles;
  selectedImageFile = sampleFiles[0] ?? null;
  selectedImageLabel = DATASET_SAMPLES[0]?.label ?? "dataset sample";
  activeDatasetIndex = 0;
  setStatus([
    { label: "Dataset", value: "Loading bundled sample set" },
    { label: "Backend", value: activeApiBase }
  ]);

  try {
    await setActiveDatasetFile(0);
    setStatus([
      { label: "Dataset", value: `${selectedDatasetFiles.length} bundled samples loaded` },
      { label: "Backend", value: activeApiBase },
      { label: "Ready", value: "Click Run Analysis" }
    ]);
  } catch {
    setStatus([
      { label: "Dataset", value: "Failed to fetch sample" },
      { label: "Action", value: "Upload your own image" }
    ]);
  }
}

async function runAnalysis() {
  if (!selectedImageFile) {
    setStatus([
      { label: "Status", value: "Select or load an image first" },
      { label: "Action", value: "Use Upload or Load Dataset" }
    ]);
    return;
  }

  setStatus([
    { label: "Status", value: "Running YOLO detection" },
    { label: "Source", value: selectedImageLabel }
  ]);

  const formData = new FormData();
  formData.append("image", selectedImageFile);
  formData.append("file", selectedImageFile);
  formData.append("confidence", analysisConfidence.value);

  try {
    const apiBase = await resolveApiBase();
    const response = await fetch(`${apiBase}/analyze`, {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      const payload = await response.json();
      throw new Error(payload.error || "Image analysis failed");
    }

    const payload = await response.json();
    if (Array.isArray(payload.detections) && typeof payload.count === "number" && !payload.summary) {
      renderDetections(payload.detections);
      renderOverlayBoxes(payload.detections);
      analysisScore.textContent = "N/A";
      setStatus([
        { label: "Status", value: "Raw response mode" },
        { label: "Objects", value: String(payload.count) },
        { label: "Backend", value: apiBase }
      ]);
      return;
    }

    const score = computeAccessibilityScore(payload.features);
    analysisScore.textContent = score === null ? "N/A" : `${score}%`;

    renderFeatures(payload.features);
    renderGaps(payload.gaps);
    renderDetections(payload.detections);
    renderOverlayBoxes(payload.detections);

    setStatus([
      { label: "Status", value: payload.inconclusive ? "Analysis inconclusive" : "Analysis complete" },
      { label: "Objects", value: String(payload.summary.detectedObjects) },
      { label: "Model", value: `${payload.summary.model} @ ${payload.summary.confidenceUsed}` },
      { label: "Backend", value: apiBase }
    ]);
  } catch (error) {
    setStatus([
      { label: "Status", value: "Analysis failed" },
      { label: "Error", value: error.message }
    ]);
  }
}

imageUpload.addEventListener("change", (event) => {
  void loadDatasetFiles(event.target.files, "your upload");
});

datasetSelector.addEventListener("change", (event) => {
  const nextIndex = Number(event.target.value);
  if (Number.isFinite(nextIndex)) {
    void setActiveDatasetFile(nextIndex);
  }
});

analysisPreview.addEventListener("load", () => {
  detectedImageWidth = Math.max(analysisPreview.naturalWidth || 1, 1);
  detectedImageHeight = Math.max(analysisPreview.naturalHeight || 1, 1);
});

analysisConfidence.addEventListener("input", () => {
  analysisConfidenceValue.textContent = analysisConfidence.value;
});

runImageAnalysisButton.addEventListener("click", runAnalysis);
loadDatasetButton.addEventListener("click", loadDataset);
printTop.addEventListener("click", () => window.print());

renderFeatures({ ramp: false, stairs: false, tactile: false, braille: false });
renderGaps(["Run analysis to generate gap report"]);
renderDetections([]);
setStatus([
  { label: "Backend", value: "Checking connectivity" },
  { label: "Action", value: "Load dataset or upload image" }
]);

resolveApiBase()
  .then((apiBase) => {
    setStatus([
      { label: "Backend", value: `${apiBase} connected` },
      { label: "Action", value: "Load dataset or upload image" }
    ]);
  })
  .catch(() => {
    setStatus([
      { label: "Backend", value: "Offline" },
      { label: "Action", value: "Start server with npm run backend:dev" }
    ]);
  });
