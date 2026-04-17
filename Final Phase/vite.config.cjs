const { defineConfig } = require("vite");

module.exports = defineConfig({
  server: {
    watch: {
      ignored: ["**/.venv/**", "**/.venv-windows/**", "**/node_modules/**", "**/dist/**"],
    },
  },
});