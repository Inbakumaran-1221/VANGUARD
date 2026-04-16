const feedbackTable = document.getElementById("feedbackAdminTable");
const feedbackCount = document.getElementById("feedbackCount");
const filterForm = document.getElementById("feedbackFilterForm");
const filterCity = document.getElementById("filterCity");
const filterSeverity = document.getElementById("filterSeverity");
const reloadButton = document.getElementById("reloadFeedback");
const exportCsvButton = document.getElementById("exportCsv");
const exportCsvTopButton = document.getElementById("exportCsvTop");

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

let resolvedApiBase = null;
let currentRows = [];

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function resolveApiBase() {
  if (resolvedApiBase) return resolvedApiBase;

  for (const candidate of API_BASE_CANDIDATES) {
    for (let attempt = 0; attempt < 6; attempt += 1) {
      try {
        const response = await fetch(`${candidate}/health`);
        if (response.ok) {
          resolvedApiBase = candidate;
          return candidate;
        }
      } catch {
        // Continue retries.
      }
      await delay(300);
    }
  }

  throw new Error("Backend unavailable. Start npm run dev and reload this page.");
}

function toQueryParams(filters) {
  const params = new URLSearchParams();
  if (filters.city) params.set("city", filters.city);
  if (filters.severity) params.set("severity", filters.severity);
  params.set("limit", "200");
  return params.toString();
}

function formatDate(dateIso) {
  const date = new Date(dateIso);
  return Number.isNaN(date.getTime()) ? "-" : date.toLocaleString();
}

function renderCityOptions(rows) {
  const selected = filterCity.value;
  const cities = [...new Set(rows.map((row) => row.city).filter(Boolean))].sort();

  filterCity.innerHTML = "<option value=''>All Cities</option>";
  cities.forEach((city) => {
    const option = document.createElement("option");
    option.value = city;
    option.textContent = city;
    filterCity.appendChild(option);
  });

  if (selected) {
    filterCity.value = cities.includes(selected) ? selected : "";
  }
}

function renderTable(rows) {
  feedbackTable.innerHTML = "";

  if (rows.length === 0) {
    const row = document.createElement("tr");
    row.innerHTML = "<td colspan='7'>No feedback rows found for selected filters.</td>";
    feedbackTable.appendChild(row);
    feedbackCount.textContent = "0 records";
    return;
  }

  rows.forEach((entry) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${entry.id}</td>
      <td>${entry.city ?? "Unknown"}</td>
      <td>${entry.stopId}</td>
      <td><span class="badge badge-${entry.severity}">${entry.severity}</span></td>
      <td>${entry.message}</td>
      <td>${formatDate(entry.createdAt)}</td>
      <td>
        <button class="btn btn-ghost" data-action="edit" data-id="${entry.id}" type="button">Edit</button>
        <button class="btn btn-secondary" data-action="delete" data-id="${entry.id}" type="button">Delete</button>
      </td>
    `;
    feedbackTable.appendChild(row);
  });

  feedbackCount.textContent = `${rows.length} records`;
}

async function loadFeedback() {
  const apiBase = await resolveApiBase();
  const filters = {
    city: filterCity.value,
    severity: filterSeverity.value
  };

  const response = await fetch(`${apiBase}/feedback?${toQueryParams(filters)}`);
  if (!response.ok) {
    throw new Error("Failed to load feedback records.");
  }

  const payload = await response.json();
  currentRows = Array.isArray(payload.items) ? payload.items : [];
  renderCityOptions(currentRows);
  renderTable(currentRows);
}

async function deleteFeedback(id) {
  const apiBase = await resolveApiBase();
  const response = await fetch(`${apiBase}/feedback/${id}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Delete failed.");
  }
}

async function editFeedback(entry) {
  const nextMessage = window.prompt("Update feedback message:", entry.message);
  if (nextMessage === null) return;

  const nextSeverity = window.prompt("Update severity (low/medium/high/critical):", entry.severity);
  if (nextSeverity === null) return;

  const apiBase = await resolveApiBase();
  const response = await fetch(`${apiBase}/feedback/${entry.id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      message: nextMessage,
      severity: nextSeverity
    })
  });

  if (!response.ok) {
    throw new Error("Edit failed. Use valid severity values.");
  }
}

function exportCsv() {
  resolveApiBase()
    .then((apiBase) => {
      const filters = {
        city: filterCity.value,
        severity: filterSeverity.value
      };
      const query = toQueryParams(filters);
      window.open(`${apiBase}/feedback/export.csv?${query}`, "_blank", "noopener");
    })
    .catch((error) => {
      window.alert(error.message);
    });
}

feedbackTable.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const action = button.dataset.action;
  const id = button.dataset.id;
  const entry = currentRows.find((row) => row.id === id);
  if (!entry) return;

  try {
    if (action === "delete") {
      const confirmed = window.confirm(`Delete feedback ${entry.id}?`);
      if (!confirmed) return;
      await deleteFeedback(entry.id);
    }

    if (action === "edit") {
      await editFeedback(entry);
    }

    await loadFeedback();
  } catch (error) {
    window.alert(error.message);
  }
});

filterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await loadFeedback();
  } catch (error) {
    window.alert(error.message);
  }
});

reloadButton.addEventListener("click", async () => {
  try {
    await loadFeedback();
  } catch (error) {
    window.alert(error.message);
  }
});

exportCsvButton.addEventListener("click", exportCsv);
exportCsvTopButton.addEventListener("click", exportCsv);

loadFeedback().catch((error) => {
  feedbackTable.innerHTML = `<tr><td colspan='7'>${error.message}</td></tr>`;
});
