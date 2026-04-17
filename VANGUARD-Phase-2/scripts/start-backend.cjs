const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

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

const venvPython = venvCandidates.find((candidate) => fs.existsSync(candidate));

if (!venvPython) {
  console.error(
    "Python virtual environment not found. Create .venv-windows on Windows or .venv on POSIX, install backend dependencies, and rerun npm run dev."
  );
  process.exit(1);
}

const child = spawn(venvPython, [backendEntry], {
  cwd: projectRoot,
  stdio: "inherit",
  env: process.env,
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