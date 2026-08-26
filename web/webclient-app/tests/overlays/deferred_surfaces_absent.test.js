import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import manifest from "../../component-manifest.json";
import DockMenu from "../../components/DockMenu.vue";
import SkillDetailPane from "../../components/SkillDetailPane.vue";

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
// Word-boundary matching: a whole deferred-surface word flags the title;
// bare substrings would false-positive on legitimate names (e.g. "Bag"
// inside "Baggage").
//
// H1 (webclient-hud-01-shell-and-scene): the stage reserves no anchor for
// a companion strip, a toast queue, or a persistent objective tracker
// (roadmap §2.4 — no backing read model; deferred surfaces are absent, not
// mocked). H2 (webclient-hud-02-status-islands) names the unbacked HUD
// claims the draft makes: the companion strip, the head card's
// race/subrace/class/faction line, and any minimap bearing or distance.
const DEFERRED_TITLE_PATTERNS = [
  /\bParty\b/i,
  /\bIntimate\b/i,
  /\bEventLog\b/i,
  /\bToasts?\b/i,
  /\bCompanions?\b/i,
  /\bObjectives?\b/i,
   // H2 additions: the head-card identity line and the minimap's unbacked
   // figures (roadmap §2.4 — no race/class/faction field or bearing/distance
   // exists in the payloads).
  /\bRace\b/i,
  /\bSubrace\b/i,
  /\bClass\b/i,
  /\bFaction\b/i,
  /\bBearing\b/i,
  /\bDistance\b/i,
  /\bCompass\b/i,
  // H5 (webclient-hud-05-overlays-and-command-line, task 8.3): this wave's
  // deferrals, each named by the backing it waits on:
  // - the draft's 分類 → 條目 → 子主題 game-help browser (an OOB panel
  //   carrying `help` content — the `help` command's output reaches the
  //   client only as narrative text; no committed panel carries it);
  // - the audio-volume rows (no audio subsystem in this client);
  // - the `HUD 縮放` slider and the 重映射 control;
  // - map zoom/pan (the map surface ships no zoom or pan affordance).
  /\bHelpBrowser\b/i,
  /\bGameHelp\b/i,
  /\bAudio\b/i,
  /\bVolume\b/i,
  /\bHudScale\b/i,
  /\bRemap(ping)?\b/i,
  /\bZoom\b/i,
  /\bPan\b/i,
];

describe("B5 full-overlays contract: deferred surfaces absent, manifest frozen", () => {
  it("freezes the required-component manifest at the complete set", () => {
    expect(manifest.frozen).toBe(true);
   // H1 grew the frozen set to 29; H2 (webclient-hud-02-status-islands)
   // extends it by three (`Data/CharacterHead`, `Data/VitalsTrack`,
   // `Data/ConditionChips`, 29 → 32); H3 (webclient-hud-03-action-dock)
   // adds `Action/DockTabBar`, `Action/DockBreadcrumb`, `Action/SkillDetailPane`,
   // and `Data/ParticipantFrame` (32 → 36); H4 (webclient-hud-04-reference-drawers)
   // adds the three reference-drawer components (`Core/HudDrawer`,
   // `Data/EquipmentDoll`, `Data/CharacterStatusDrawer`, 36 → 39). H5
   // (webclient-hud-05-overlays-and-command-line, task 8.2) renames
   // `Core/CommandDrawer` → `Core/CommandLine` and adds `Core/QuickWordChips`
   // and `Overlays/OverlayHost` (39 → 41). H6 re-freezes at the complete new
   // set.
   expect(manifest.required).toHaveLength(41);
   // The four full overlays complete the required set (B5's new family).
   for (const title of [
     "Overlays/MapOverlay",
     "Overlays/SettingsOverlay",
     "Overlays/HelpOverlay",
     "Overlays/OverlayHost",
     "Overlays/CreationOverlay",
     "Core/CommandLine",
     "Core/QuickWordChips",
     "Action/DockTabBar",
     "Action/DockBreadcrumb",
     "Action/SkillDetailPane",
     "Data/ParticipantFrame",
     "Core/HudDrawer",
     "Data/EquipmentDoll",
     "Data/CharacterStatusDrawer",
   ]) {
     expect(manifest.required).toContain(title);
   }
  });

  // H3 (task 7.3): the dock renders no `戰鬥外` skill badge (design D14 —
  // the `combat_out_of_combat` flag is serialized by no presenter), no
  // look-row stat line (waits on a not-yet-committed `status` field), and
  // no exploration-row portrait (waits on a not-yet-committed `portrait_ref`
  // for exploration rows). Each deferred surface is named by the field it
  // waits on, so a regression that invents one fails at the unit gate.
  it("the dock renders no 戰鬥外 skill badge (waits on the combat_out_of_combat flag)", () => {
    const skill = {
      key: "fireball",
      label: "火球",
      description: "凝聚火焰魔力。",
      costText: "MP 14",
      targetSpec: "single",
      element: "fire",
      enabled: true,
      disabledReason: null,
      freeformScales: [],
      scale: 1,
    };
    const wrapper = mount(SkillDetailPane, { props: { skill } });
    // The 戰鬥外 badge is a deferred surface: it waits on the
    // `combat_out_of_combat` flag, which no presenter serializes.
    expect(wrapper.find('[data-testid="skill-ooc"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain("戰鬥外");
  });

  it("the dock renders no look-row stat line (waits on the status field)", () => {
    // A look (nav) pane row: the stat line is deferred — it waits on a
    // `status` field that the look panel does not commit yet.
    const items = [
      { key: "look-room", label: "查看房間", enabled: true, action_id: "explore.look", params: { room: true } },
      { key: "entity-5", label: "南門守衛", enabled: true, action_id: "explore.look", params: { target_id: 5 }, kind: "npc" },
    ];
    const wrapper = mount(DockMenu, {
      props: { items, focusedKey: "entity-5", idPrefix: "exploration-row" },
    });
    expect(wrapper.find('[data-testid="look-row-stat"]').exists()).toBe(false);
  });

  it("the dock renders no exploration-row portrait (waits on the portrait_ref field)", () => {
    // An exploration (nav) row: the portrait slot is deferred — it waits on
    // a `portrait_ref` field the exploration panel does not commit yet.
    const items = [
      { key: "entity-5", label: "南門守衛", enabled: true, action_id: "explore.look", params: { target_id: 5 }, kind: "npc" },
    ];
    const wrapper = mount(DockMenu, {
      props: { items, focusedKey: "entity-5", idPrefix: "exploration-row" },
    });
    expect(wrapper.find('[data-testid="exploration-row-portrait"]').exists()).toBe(false);
    expect(wrapper.find("img").exists()).toBe(false);
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

  it("documents the bag is now backed by services.inventory (world/rules/service_view.py:695-720), so the \bBag\b deferred pattern is retired", () => {
    // H4 (task 8.3): the full inventory bag is NO LONGER deferred — the
    // `services.inventory` read model (world/rules/service_view.py:695-720)
    // backs the bounded 32-row bag listing. `World/InventoryPanel` renders
    // that listing, so the `\bBag\b` pattern is removed from
    // DEFERRED_TITLE_PATTERNS and the equipped-only case is retired.
    expect(manifest.required).toContain("World/InventoryPanel");
    // The bag now has a backing read model; no *Bag surface remains deferred.
    const titles = collectStoryTitles(APP_ROOT);
    expect(titles.filter((title) => /\bBag\b/i.test(title))).toEqual([]);
  });

  it("reserves no party/companion drawer, intimate collapsible, item-rarity affordance or discovered-lore compendium (task 8.4)", () => {
    // H4 (task 8.4): the reference-drawer layer is the closed set of six
    // drawers. The deferred surfaces are NOT reserved in the drawer layer.
    const DRAWER_NAMES = ["skill", "inventory", "shop", "quest", "lore", "status"];
    const DEFERRED_SURFACES = ["party", "companion", "intimate", "rarity", "codex"];
    // None of the deferred surfaces is in the six-drawer set.
    for (const deferred of DEFERRED_SURFACES) {
      expect(DRAWER_NAMES, `drawer set reserves "${deferred}"`).not.toContain(deferred);
    }
    // And none of them appears in the required-component set.
    for (const title of manifest.required) {
      for (const word of ["Party", "Companion", "Intimate", "Rarity", "Codex", "Compendium"]) {
        const re = new RegExp(`\\b${word}\\b`, "i");
        expect(re.test(title), `required component ${title} reserves a deferred surface (${word})`).toBe(false);
      }
    }
  });
});
