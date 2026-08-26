import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

// Vitest gate for the Vue component/view layer (kept separate from the
// dependency-free Node gate on web/static/webclient/js). Runs offline with no
// network access by construction (jsdom, no fetch in the test surface).
export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "jsdom",
    // Load SFC <style> blocks so computed-style assertions (e.g. the
    // command-line chip mode-gate `display:none`) see the real CSS.
    css: true,
    include: ["web/webclient-app/**/*.test.js"],
  },
});
