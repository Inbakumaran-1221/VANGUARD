const fs = require("fs");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const projectRoot = path.resolve(__dirname, "..");
const backendEntry = path.join(projectRoot, "backend", "app.py");
const venvCandidates = process.platform === "win32"
  ? [
      path.join(projectRoot, ".venv-windows", "Scripts", "python.exe"),
      path.join(projectRoot, ".venv", "Scripts", "python.exe"),
    ]
  : [
      path.join(projectRoot, ".venv", "bin", "python"),
      path.join(projectRoot, ".venv-windows", "bin", "python"),
    ];

function isUsablePython(executable) {
  if (!executable) {
    return false;
  }

  const result = spawnSync(executable, ["-c", "import sys"], {
    cwd: projectRoot,
    stdio: "ignore",
    shell: false,
  });

  return !result.error && result.status === 0;
}

const fallbackCandidates = process.platform === "win32"
  ? ["python", "python3"]
  : ["python3", "python"];

const venvPython = [...venvCandidates, ...fallbackCandidates].find((candidate) => {
  return isUsablePython(candidate);
});

if (!venvPython) {
  console.error(
    "No usable Python interpreter was found. Create a virtual environment with Python 3.10+ or add python to PATH, install backend dependencies, and rerun npm run dev."
  );
  process.exit(1);
}

const child = spawn(venvPython, [backendEntry], {
  cwd: projectRoot,
  stdio: "inherit",
  env: {
    ...process.env,
    MONGODB_URI: process.env.MONGODB_URI || "mongodb://localhost:27017/",
  },
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }

  process.exit(code ?? 0);
});

child.on("error", (error) => {
  console.error(`Failed to start backend: ${error.message}`);
  process.exit(1);
});