import { indiaGrievances, indiaStops } from "./india-dataset.js";

const STORAGE_KEY = "accessaudit-state-v1";
const FEEDBACK_STORAGE_KEY = "accessaudit-feedback-v1";
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

const baselineStops = indiaStops;

const defaultGrievances = indiaGrievances;
const STATE_API_PATH = "/state";

let resolvedApiBase = null;
let syncAttemptStarted = false;

const FEATURE_PENALTIES = {
  hasRamp: 20,
  hasElevator: 16,
  hasTactile: 14,
  hasBraille: 14,
  hasAudio: 13,
  hasLowFloorAccess: 11
};

function cloneDefaultState() {
  return {
    stops: structuredClone(baselineStops),
    grievancesText: defaultGrievances.join("\n"),
    userFeedback: []
  };
}

function loadFeedbackStore() {
  const raw = localStorage.getItem(FEEDBACK_STORAGE_KEY);
  if (!raw) return [];

  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveFeedbackStore(entries) {
  localStorage.setItem(FEEDBACK_STORAGE_KEY, JSON.stringify(entries));
}

function cloneState(state) {
  return {
    stops: structuredClone(state.stops ?? []),
    grievancesText: String(state.grievancesText ?? ""),
    userFeedback: structuredClone(state.userFeedback ?? [])
  };
}

export async function resolveApiBase() {
  if (resolvedApiBase) return resolvedApiBase;

  for (const candidate of API_BASE_CANDIDATES) {
    try {
      const response = await fetch(`${candidate}/health`);
      if (response.ok) {
        resolvedApiBase = candidate;
        return candidate;
      }
    } catch {
      // Ignore and try the next candidate.
    }
  }

  return null;
}

async function syncStateToBackend(state) {
  if (syncAttemptStarted) return;
  syncAttemptStarted = true;

  try {
    const apiBase = await resolveApiBase();
    if (!apiBase) return;

    await fetch(`${apiBase}${STATE_API_PATH}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(cloneState(state))
    });
  } catch {
    // Keep localStorage as the immediate source of truth if the backend is unavailable.
  } finally {
    syncAttemptStarted = false;
  }
}

export function loadState() {
  const raw = localStorage.getItem(STORAGE_KEY);
  const feedbackFallback = loadFeedbackStore();

  if (!raw) {
    const fallback = cloneDefaultState();
    fallback.userFeedback = feedbackFallback;
    saveState(fallback);
    void syncStateToBackend(fallback);
    return fallback;
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed.stops) || typeof parsed.grievancesText !== "string") {
      throw new Error("Invalid state shape");
    }
    if (!Array.isArray(parsed.userFeedback)) {
      parsed.userFeedback = feedbackFallback;
    }

    // Keep feedback available even if older state versions omitted it.
    if (parsed.userFeedback.length === 0 && feedbackFallback.length > 0) {
      parsed.userFeedback = feedbackFallback;
      saveState(parsed);
    }

    void syncStateToBackend(parsed);

    return parsed;
  } catch {
    const fallback = cloneDefaultState();
    fallback.userFeedback = feedbackFallback;
    saveState(fallback);
    void syncStateToBackend(fallback);
    return fallback;
  }
}

export function saveState(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  if (Array.isArray(state.userFeedback)) {
    saveFeedbackStore(state.userFeedback);
  }
  window.dispatchEvent(new CustomEvent("accessaudit-state-updated"));
  void syncStateToBackend(state);
}

export function resetDemo(options = {}) {
  const { preserveFeedback = true } = options;
  const current = preserveFeedback ? loadState() : null;
  const state = cloneDefaultState();
  if (preserveFeedback) {
    state.userFeedback = current?.userFeedback ?? loadFeedbackStore();
  }
  saveState(state);
  return state;
}

export function updateGrievances(text) {
  const state = loadState();
  state.grievancesText = text;
  saveState(state);
  return state;
}

export function submitFeedback(report) {
  const state = loadState();
  if (!report?.message?.trim()) {
    return null;
  }

  const entry = {
    id: `fb-${Date.now()}`,
    stopId: report.stopId || "UNASSIGNED",
    message: report.message.trim(),
    severity: report.severity || "medium",
    lat: report.lat,
    lng: report.lng,
    createdAt: new Date().toISOString()
  };
  state.userFeedback.unshift(entry);
  state.userFeedback = state.userFeedback.slice(0, 50);

  // Keep text clustering and grievance counts aligned with submitted user reviews.
  state.grievancesText = [state.grievancesText, entry.message]
    .map((value) => String(value ?? "").trim())
    .filter(Boolean)
    .join("\n");

  const matchedStop = state.stops.find((stop) => stop.id === entry.stopId);
  if (matchedStop) {
    const nextCount = Number.isFinite(matchedStop.grievanceCount) ? matchedStop.grievanceCount + 1 : 1;
    matchedStop.grievanceCount = Math.max(0, nextCount);
    matchedStop.audited = true;
    matchedStop.lastUpdated = entry.createdAt;
  }

  saveState(state);
  return entry;
}

export function runAuditUpdate() {
  const state = loadState();
  state.stops = state.stops.map((stop) => {
    const jitter = Math.floor(Math.random() * 7) - 3;
    const trend = Array.isArray(stop.trend) ? [...stop.trend] : [];
    trend.push(Math.max(0, Math.min(100, (trend[trend.length - 1] ?? 55) + jitter)));
    const nextTrend = trend.slice(-6);
    return {
      ...stop,
      grievanceCount: Math.max(stop.grievanceCount + jitter, 0),
      audited: true,
      trend: nextTrend,
      lastUpdated: new Date().toISOString()
    };
  });
  saveState(state);
  return state;
}

function computeGapScore(stop) {
  let missingFeatures = 0;
  let deductions = [];
  let suggestions = [];

  Object.entries(FEATURE_PENALTIES).forEach(([feature, penalty]) => {
    if (!stop[feature]) {
      missingFeatures += penalty;
      const label = feature.replace('has', '').replace('LowFloorAccess', 'Low-Floor Boarding');
      deductions.push(`Missing ${label} (+${penalty} pts)`);
      suggestions.push({ fix: `Install standard ${label}`, improvement: penalty });
    }
  });

  let evidenceSeverity = 0;
  (stop.evidence ?? []).forEach((item) => {
    if (item.label.includes("missing") || item.label.includes("fault") || item.label.includes("absent")) {
      evidenceSeverity += 3;
      deductions.push(`CV found ${item.label} (+3 pts)`);
      suggestions.push({ fix: `Repair computer-vision sighted issue: ${item.label}`, improvement: 3 });
    }
  });

  const grievanceSeverity = Math.round(stop.grievanceCount * 0.45);
  if (grievanceSeverity > 0) {
      deductions.push(`High user grievance rate (+${grievanceSeverity} pts)`);
      suggestions.push({ fix: `Review and resolve citizen complaints`, improvement: grievanceSeverity });
  }

  const severityWeight = Math.min(35, evidenceSeverity + grievanceSeverity);
  const gapScore = Math.min(100, missingFeatures + severityWeight);

  suggestions.sort((a,b) => b.improvement - a.improvement);

  return {
    gapScore,
    missingFeatures,
    severityWeight,
    deductions,
    suggestions
  };
}

function priorityLabel(score) {
  if (score >= 75) return "Critical";
  if (score >= 50) return "High";
  if (score >= 30) return "Medium";
  return "Low";
}

function coverageLabel(stop) {
  const fulfilled = [stop.hasRamp, stop.hasElevator, stop.hasTactile, stop.hasBraille, stop.hasAudio, stop.hasLowFloorAccess].filter(Boolean).length;
  return `${Math.round((fulfilled / 6) * 100)}%`;
}

function computeBreakdown(stop) {
  const mobilityCompleted = [stop.hasRamp, stop.hasElevator, stop.hasLowFloorAccess].filter(Boolean).length;
  const visualCompleted = [stop.hasTactile, stop.hasBraille].filter(Boolean).length;
  const audioCompleted = [stop.hasAudio].filter(Boolean).length;

  return {
    mobility: Math.round((mobilityCompleted / 3) * 100),
    visual: Math.round((visualCompleted / 2) * 100),
    audio: Math.round((audioCompleted / 1) * 100)
  };
}

function clusterGrievances(rawText) {
  const lines = rawText.split("\n").map((line) => line.trim()).filter(Boolean);
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

  const sorted = Object.values(themes).sort((a, b) => b.count - a.count);
  const topCount = sorted[0]?.count ?? 0;
  const coherence = lines.length > 0 ? (topCount / lines.length) * 0.72 + 0.2 : 0;
  return { themeStats: sorted, coherence, grievanceLines: lines };
}

export function deriveMainTrigger(stop) {
  if (!stop.hasRamp) return "Ramp missing";
  if (!stop.hasTactile) return "No tactile paving";
  if (!stop.hasAudio) return "Audio cues absent";
  if (!stop.hasLowFloorAccess) return "Boarding gap mismatch";
  return "Needs maintenance";
}

function trendSnapshot(scoredStops) {
  const previousAverage = Math.round(
    scoredStops.reduce((sum, stop) => {
      const prevValue = stop.trend?.length > 1 ? stop.trend[stop.trend.length - 2] : stop.gapScore;
      return sum + prevValue;
    }, 0) / scoredStops.length
  );

  const currentAverage = Math.round(scoredStops.reduce((sum, stop) => sum + stop.gapScore, 0) / scoredStops.length);
  return {
    previousAverage,
    currentAverage,
    delta: currentAverage - previousAverage
  };
}

export function getAnalytics() {
  const state = loadState();
  const scoredStops = state.stops
    .map((stop) => {
      const { gapScore, missingFeatures, severityWeight, deductions, suggestions } = computeGapScore(stop);
      const breakdown = computeBreakdown(stop);
      const confidence = Math.round(
        (((stop.evidence ?? []).reduce((sum, item) => sum + (item.confidence ?? 0), 0) / Math.max((stop.evidence ?? []).length, 1)) || 0.74) * 100
      );
      return {
        ...stop,
        gapScore,
        missingFeatures,
        severityWeight,
        deductions,
        suggestions,
        confidence,
        breakdown,
        priority: priorityLabel(gapScore),
        coverage: coverageLabel(stop)
      };
    })
    .sort((a, b) => b.gapScore - a.gapScore);

  const { themeStats, coherence, grievanceLines } = clusterGrievances(state.grievancesText);
  const feedbackCount = Array.isArray(state.userFeedback) ? state.userFeedback.length : 0;
  const totalGrievances = grievanceLines.length;
  const distribution = {
    critical: scoredStops.filter((stop) => stop.gapScore >= 75).length,
    high: scoredStops.filter((stop) => stop.gapScore >= 50 && stop.gapScore < 75).length,
    medium: scoredStops.filter((stop) => stop.gapScore >= 30 && stop.gapScore < 50).length,
    low: scoredStops.filter((stop) => stop.gapScore < 30).length
  };

  const averageScore = Math.round(scoredStops.reduce((sum, stop) => sum + stop.gapScore, 0) / scoredStops.length);
  const criticalCount = scoredStops.filter((stop) => stop.priority === "Critical").length;
  const coveragePercent = Math.round((scoredStops.filter((stop) => stop.audited).length / scoredStops.length) * 100);
  const runtime = `${(1.6 + scoredStops.length * 0.33).toFixed(1)} min`;
  const accessibilityBreakdown = {
    mobility: Math.round(scoredStops.reduce((sum, stop) => sum + stop.breakdown.mobility, 0) / scoredStops.length),
    visual: Math.round(scoredStops.reduce((sum, stop) => sum + stop.breakdown.visual, 0) / scoredStops.length),
    audio: Math.round(scoredStops.reduce((sum, stop) => sum + stop.breakdown.audio, 0) / scoredStops.length)
  };
  const alerts = scoredStops
    .filter((stop) => stop.priority === "Critical")
    .map((stop) => ({
      stopId: stop.id,
      stopName: stop.name,
      message: `Critical issue detected: ${deriveMainTrigger(stop)}`,
      confidence: stop.confidence
    }));

  const trend = trendSnapshot(scoredStops);

  return {
    state,
    scoredStops,
    themeStats,
    coherence,
    grievanceLines,
    feedbackCount,
    totalGrievances,
    distribution,
    averageScore,
    criticalCount,
    coveragePercent,
    runtime,
    accessibilityBreakdown,
    alerts,
    trend
  };
}
