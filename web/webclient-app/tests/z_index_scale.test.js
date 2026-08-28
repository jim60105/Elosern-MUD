// fix-webclient-hud-integration-gaps (task 4.2): fast source-level guard
// for the z-index scale. Proves the component CSS references the shared
// tokens and that `--z-offline` outranks `--z-surface-modal` numerically.
// It is a cheap first line of defense, not a proof of real paint order:
// the real-browser stacking proof lives in
// web/tests/browser/test_browser_reconnect.py (task 4.1).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

function styleBlock(file) {
  const source = readFileSync(join(APP_ROOT, file), "utf-8");
  const match = source.match(/<style[^>]*>[\s\S]*<\/style>/);
  return match ? match[0] : "";
}

function extractRule(css, selector) {
  const escaped = selector.replace(/([.{}#&[\]()])/g, "\\$&");
  const re = new RegExp(escaped + "\\s*\\{[\\s\\S]*?\\}", "m");
  const match = re.exec(css);
  return match ? match[0] : "";
}

// (b) the four full-screen surfaces and the drawer scrim, each with its
// expected shared-tier declaration (the scrim derives from the modal tier).
const SURFACE_RULES = [
  ["components/HudDrawer.vue", ".hud-drawer-scrim", "z-index: calc(var(--z-surface-modal) - 100)"],
  ["components/HudDrawer.vue", ".hud-drawer", "z-index: var(--z-surface-modal)"],
  ["components/ArtPanel.vue", ".art-panel__fullview", "z-index: var(--z-surface-modal)"],
  ["components/SceneBackdrop.vue", ".scene-backdrop .scene-backdrop__fullview", "z-index: var(--z-surface-modal)"],
  ["components/FullLogOverlay.vue", ".fulllog-overlay", "z-index: var(--z-surface-modal)"],
  ["components/InventoryPanel.vue", ".inventory-confirm", "z-index: calc(var(--z-surface-modal) + 100)"],
];

describe("z-index scale (fix-webclient-hud-integration-gaps)", () => {
  it("(a) the offline overlay consumes the reserved --z-offline tier", () => {
    const css = styleBlock("components/AppShell.vue");
    const rule = extractRule(css, ".elosern-app-shell #elosern-offline-overlay");
    expect(rule, "#elosern-offline-overlay must reference --z-offline").toContain("z-index: var(--z-offline)");
  });

  it("(b) every full-screen surface consumes the shared modal tier", () => {
    for (const [file, selector, expected] of SURFACE_RULES) {
      const css = styleBlock(file);
      const rule = extractRule(css, selector);
      expect(
        rule,
        `${selector} (${file}) must reference the shared z-index token`,
      ).toContain(expected);
    }
  });

  it("(c) --z-offline is numerically greater than --z-surface-modal", () => {
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf-8");
    const surfaceModal = Number(tokens.match(/--z-surface-modal:\s*(\d+)/)[1]);
    const offline = Number(tokens.match(/--z-offline:\s*(\d+)/)[1]);
    expect(surfaceModal).toBe(3000);
    expect(offline).toBe(9000);
    expect(offline).toBeGreaterThan(surfaceModal);
  });
});
