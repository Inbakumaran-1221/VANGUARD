const THEME_KEY = "accessaudit-theme";
const root = document.documentElement;

function getInitialTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  if (saved === "dark" || saved === "light") {
    return saved;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function updateToggleButtons(theme) {
  const isDark = theme === "dark";
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.textContent = isDark ? "Day Mode" : "Night Mode";
    button.setAttribute("aria-label", isDark ? "Switch to day mode" : "Switch to night mode");
  });
}

function applyTheme(theme) {
  root.setAttribute("data-theme", theme);
  updateToggleButtons(theme);
}

function toggleTheme() {
  const current = root.getAttribute("data-theme") === "dark" ? "dark" : "light";
  const next = current === "dark" ? "light" : "dark";
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
}

applyTheme(getInitialTheme());

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    button.addEventListener("click", toggleTheme);
  });

  updateToggleButtons(root.getAttribute("data-theme") || "light");
});
