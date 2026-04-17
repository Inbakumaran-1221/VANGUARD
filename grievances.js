import { getAnalytics, loadState, resetDemo, runAuditUpdate, saveState, submitFeedback, updateGrievances } from "./shared-data.js";

const grievanceInput = document.getElementById("grievanceInput");
const silhouetteMetric = document.getElementById("silhouetteMetric");
const clusterList = document.getElementById("clusterList");
const categoryBreakdown = document.getElementById("categoryBreakdown");
const feedbackForm = document.getElementById("feedbackForm");
const feedbackStop = document.getElementById("feedbackStop");
const feedbackSeverity = document.getElementById("feedbackSeverity");
const feedbackMessage = document.getElementById("feedbackMessage");
const feedbackList = document.getElementById("feedbackList");
const recordComplaintBtn = document.getElementById("recordComplaintBtn");

const runAuditButton = document.getElementById("runAudit");
const loadDemoButton = document.getElementById("loadDemo");
const analyzeTextButton = document.getElementById("analyzeText");
const printTop = document.getElementById("printReportTop");

const configuredApiBase = import.meta.env.VITE_API_URL;
const FEEDBACK_API_BASES = [
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

let resolvedFeedbackApiBase = null;

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function resolveFeedbackApiBase() {
  if (resolvedFeedbackApiBase) return resolvedFeedbackApiBase;

  for (const candidate of FEEDBACK_API_BASES) {
    for (let attempt = 0; attempt < 5; attempt += 1) {
      try {
        const response = await fetch(`${candidate}/health`);
        if (response.ok) {
          resolvedFeedbackApiBase = candidate;
          return candidate;
        }
      } catch {
        // Try next attempt.
      }
      await delay(300);
    }
  }

  return null;
}

async function fetchFeedbackFromDatabase() {
  const apiBase = await resolveFeedbackApiBase();
  if (!apiBase) return [];

  const response = await fetch(`${apiBase}/feedback?limit=50`);
  if (!response.ok) return [];

  const payload = await response.json();
  return Array.isArray(payload.items) ? payload.items : [];
}

async function saveFeedbackToDatabase(entry) {
  const apiBase = await resolveFeedbackApiBase();
  if (!apiBase || !entry) return null;

  const response = await fetch(`${apiBase}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(entry)
  });

  if (!response.ok) {
    return null;
  }

  const payload = await response.json();
  return payload.item ?? null;
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

function renderClusters(themeStats, coherence) {
  clusterList.innerHTML = "";
  themeStats.forEach((theme) => {
    const node = document.createElement("div");
    node.className = "cluster-item";
    node.innerHTML = `<span>${theme.label}</span><strong>${theme.count}</strong>`;
    clusterList.appendChild(node);
  });
  silhouetteMetric.textContent = coherence.toFixed(2);
}

function renderFeedbackControls(data) {
  const previousSelection = feedbackStop.value;
  const allStops = Array.isArray(data.state?.stops) ? data.state.stops : [];

  feedbackStop.innerHTML = "";

  allStops.forEach((stop) => {
    const option = document.createElement("option");
    option.value = stop.id;
    option.textContent = `${stop.name} (${stop.id})`;
    feedbackStop.appendChild(option);
  });

  if (previousSelection && allStops.some((stop) => stop.id === previousSelection)) {
    feedbackStop.value = previousSelection;
  }
}

function renderFeedbackList(data, feedbackItems = null) {
  const entries = Array.isArray(feedbackItems) ? feedbackItems : data.state.userFeedback;
  feedbackList.innerHTML = "";
  if (entries.length === 0) {
    feedbackList.innerHTML = '<div class="metric-item"><span>No feedback submitted yet</span><strong>-</strong></div>';
    return;
  }

  entries.slice(0, 8).forEach((entry) => {
    const node = document.createElement("div");
    node.className = "metric-item";
    node.innerHTML = `<span>${entry.stopId} • ${entry.message.slice(0, 48)}</span><strong>${entry.severity}</strong>`;
    feedbackList.appendChild(node);
  });
}

async function refreshFeedbackFromDatabase(data) {
  try {
    const remoteItems = await fetchFeedbackFromDatabase();
    if (remoteItems.length > 0) {
      renderFeedbackList(data, remoteItems);
      return;
    }
  } catch {
    // Fall back to local list.
  }

  renderFeedbackList(data);
}

function refresh() {
  const data = getAnalytics();
  grievanceInput.value = data.state.grievancesText;
  renderClusters(data.themeStats, data.coherence);
  renderThemeBreakdown(data.themeStats, data.grievanceLines.length);
  renderFeedbackControls(data);
  renderFeedbackList(data);
  void refreshFeedbackFromDatabase(data);
}

analyzeTextButton.addEventListener("click", () => {
  updateGrievances(grievanceInput.value);
  refresh();
});

feedbackForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = feedbackMessage.value.trim();
  if (!message) return;

  const saved = submitFeedback({
    stopId: feedbackStop.value,
    severity: feedbackSeverity.value,
    message
  });

  if (!saved) return;

  const stored = await saveFeedbackToDatabase(saved);
  if (stored) {
    const state = loadState();
    state.userFeedback = state.userFeedback.map((item) => (item.id === saved.id ? stored : item));
    saveState(state);
  }

feedbackMessage.value = "";
  refresh();
});

if (recordComplaintBtn) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    
    let isRecording = false;

    recordComplaintBtn.addEventListener("click", () => {
      if (isRecording) {
        recognition.stop();
        return;
      }
      feedbackMessage.placeholder = "Listening...";
      recognition.start();
    });

    recognition.onstart = () => {
      isRecording = true;
      recordComplaintBtn.innerHTML = "🛑 Stop Recording";
      recordComplaintBtn.style.color = "red";
    };

    recognition.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        }
      }
      
      if (finalTranscript) {
          feedbackMessage.value = (feedbackMessage.value + " " + finalTranscript).trim();
      }
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      isRecording = false;
      recordComplaintBtn.innerHTML = "🎤 Record Voice";
      recordComplaintBtn.style.color = "";
      feedbackMessage.placeholder = "Example: Braille signage missing at platform entry";
    };

    recognition.onend = () => {
      isRecording = false;
      recordComplaintBtn.innerHTML = "🎤 Record Voice";
      recordComplaintBtn.style.color = "";
      feedbackMessage.placeholder = "Example: Braille signage missing at platform entry";
    };
  } else {
    recordComplaintBtn.style.display = "none";
  }
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
