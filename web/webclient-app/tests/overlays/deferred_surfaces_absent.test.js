import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import manifest from "../../component-manifest.json";

// B5 (webclient-vue-06-showcase-overlays): the deferred-surfaces-absent and
// frozen-manifest contract. A surface with no backing OOB read model today
// (roadmap §7 — no Party panel, no intimate/adult status collapsible, no
// full inventory bag, no event-log Toasts) MUST NOT be built or mocked, and
// the required-component manifest is frozen at the complete set (design D2/D3;
// the delta spec's "deferred surfaces are absent, not mocked" + "manifest is
// frozen" scenarios).
const APP_ROOT = join(process.cwd(), "web/webclient-app");

function collectStoryTitles(dir) {
  const titles = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      titles.push(...collectStoryTitles(path));
      continue;
    }
    if (!entry.endsWith(".stories.js")) continue;
    const source = readFileSync(path, "utf-8");
    const match = source.match(/title:\s*["'`]([^"'`]+)["'`]/);
    if (match) titles.push(match[1]);
  }
  return titles;
}

// The exact deferred surfaces from roadmap §7, matched against the component
// set and the registered story titles.
const DEFERRED_TITLE_PATTERNS = [
  /Party/i,
  /Intimate/i,
  /Bag/i,
  /EventLog/i,
  /Toasts?/i,
];

describe("B5 full-overlays contract: deferred surfaces absent, manifest frozen", () => {
  it("freezes the required-component manifest at the complete set", () => {
    expect(manifest.frozen).toBe(true);
    expect(manifest.required).toHaveLength(25);
    // The four full overlays complete the required set (B5's new family).
    for (const title of [
      "Overlays/MapOverlay",
      "Overlays/SettingsOverlay",
      "Overlays/HelpOverlay",
      "Overlays/CreationOverlay",
    ]) {
      expect(manifest.required).toContain(title);
    }
  });

  it("asserts the deferred surfaces are absent from the required set", () => {
    for (const title of manifest.required) {
      for (const pattern of DEFERRED_TITLE_PATTERNS) {
        expect(
          pattern.test(title),
          `required component ${title} looks like a deferred surface`,
        ).toBe(false);
      }
    }
  });

  it("asserts no registered story title is a deferred surface", () => {
    const titles = collectStoryTitles(APP_ROOT);
    expect(titles.length).toBeGreaterThan(0);
    for (const title of titles) {
      for (const pattern of DEFERRED_TITLE_PATTERNS) {
        expect(
          pattern.test(title),
          `registered story ${title} looks like a deferred surface`,
        ).toBe(false);
      }
    }
  });

  it("keeps the equipped-only InventoryPanel (never a full bag)", () => {
    expect(manifest.required).toContain("World/InventoryPanel");
    // The full inventory bag is deferred: no *Bag component or story exists.
    const titles = collectStoryTitles(APP_ROOT);
    expect(titles.filter((title) => /Bag/i.test(title))).toEqual([]);
  });
});
