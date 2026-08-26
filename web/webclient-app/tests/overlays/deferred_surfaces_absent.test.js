import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { h } from "vue";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import manifest from "../../component-manifest.json";
import CommandLine from "../../components/CommandLine.vue";
import CreationOverlay from "../../components/CreationOverlay.vue";
import DockMenu from "../../components/DockMenu.vue";
import HelpOverlay from "../../components/HelpOverlay.vue";
import LocalMap from "../../components/LocalMap.vue";
import MapOverlay from "../../components/MapOverlay.vue";
import NarrativeFeed from "../../components/NarrativeFeed.vue";
import OverlayHost from "../../components/OverlayHost.vue";
import SettingsOverlay from "../../components/SettingsOverlay.vue";
import SkillDetailPane from "../../components/SkillDetailPane.vue";
import { CREATION_PANEL_SAMPLE, LOCAL_MAP_SAMPLE } from "../../stories/fixtures.js";

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

// H6 (webclient-hud-06-remap-and-finalize, task 4.3): the complete unbacked
// list. Each deferred surface is named with the OOB read model it waits on,
// so a regression that builds an unbacked surface fails at the unit gate.
const DEFERRED_SURFACES = [
  {
    name: "companion/party panel",
    waitsOn: "the `party` read model (party payload)",
    testidPrefixes: ["companion-", "party-"],
  },
  {
    name: "event-log toasts",
    waitsOn: "the `event_log` read model (the toast queue)",
    testidPrefixes: ["event-log-", "toast-"],
  },
  {
    name: "persistent objective tracker",
    waitsOn: "the `objectives` read model (the persistent objectives field)",
    testidPrefixes: ["objective-"],
  },
  {
    name: "intimate/adult status collapsible",
    waitsOn: "the `intimate` / `adult` status field (no backing read model yet)",
    testidPrefixes: ["intimate-", "adult-"],
  },
];

// H6 (task 4.3, rubber-duck follow-up): the source-level absence check — the
// `web/webclient-app` sources (components + stories) must not carry any
// deferred-surface testid, proving the deferred surfaces are absent from the
// authored view layer, not merely unrendered at a given moment.
const SOURCE_DIRS = [
  join(APP_ROOT, "components"),
  join(APP_ROOT, "stories"),
];

function collectSources(dir) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) {
      files.push(...collectSources(path));
      continue;
    }
    if (entry.endsWith(".vue") || entry.endsWith(".js")) files.push(path);
  }
  return files;
}

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
    // and `Overlays/OverlayHost` (39 → 41). H6 (webclient-hud-06-remap-and-
    // finalize, task 4.2 + 5.2) removes the dead `Data/CharacterPanel` view
    // code, re-freezing the set at 40.
    expect(manifest.required).toHaveLength(40);
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

  // H6 (task 4.3 + rubber-duck follow-up): the authored view layer carries
  // no deferred-surface testid — the deferred surfaces are absent from source,
  // not merely unrendered.
  it("the authored sources carry no deferred-surface testid (source-level absence)", () => {
    const files = SOURCE_DIRS.flatMap((dir) => collectSources(dir));
    expect(files.length).toBeGreaterThan(0);
    const found = [];
    for (const surface of DEFERRED_SURFACES) {
      for (const prefix of surface.testidPrefixes) {
        for (const file of files) {
          const source = readFileSync(file, "utf-8");
          if (source.includes(`data-testid="${prefix}`) || source.includes(`data-testid=\`${prefix}`)) {
            found.push({ surface: surface.name, prefix, file });
          }
        }
      }
    }
    expect(found, `deferred-surface testids present in source: ${JSON.stringify(found)}`).toEqual([]);
  });
});

// H6 (task 4.4): every full overlay has a real trigger in the live surface
// tree, so a built-but-unreachable overlay fails the unit gate the way
// Map/Settings/Help did in B5.
describe("H6 overlay reachability: every full overlay has a live trigger", () => {
  it("the minimap island's expand control opens the map overlay", async () => {
    const wrapper = mount(LocalMap, { props: { localMap: LOCAL_MAP_SAMPLE } });
    const expand = wrapper.get('[data-testid="local-map__expand"]');
    expect(expand.exists()).toBe(true);
    await expand.trigger("click");
    expect(wrapper.emitted("open-map")).toBeTruthy();
  });

  it("the command line's settings and help buttons open the settings and help overlays", async () => {
    const wrapper = mount(CommandLine);
    const settings = wrapper.get('[data-testid="command-line-settings"]');
    const help = wrapper.get('[data-testid="command-line-help"]');
    expect(settings.exists()).toBe(true);
    expect(help.exists()).toBe(true);
    await settings.trigger("click");
    expect(wrapper.emitted("open-overlay")).toBeTruthy();
    expect(wrapper.emitted("open-overlay")[0][0]).toBe("settings");
    await help.trigger("click");
    expect(wrapper.emitted("open-overlay")[1][0]).toBe("help");
  });

  it("the narrative feed's full-log control opens the full log", async () => {
    const wrapper = mount(NarrativeFeed, {
      props: { lines: [{ kind: "sys", text: "你來到了霧骨渡口。" }] },
    });
    const control = wrapper.get('[data-testid="narrative-fulllog-control"]');
    expect(control.exists()).toBe(true);
    await control.trigger("click");
    expect(wrapper.emitted("open-full-log")).toBeTruthy();
  });

  it("the creation overlay renders its own testids and a labelled close control", () => {
    const wrapper = mount(CreationOverlay, {
      props: { creation: CREATION_PANEL_SAMPLE },
    });
    expect(wrapper.find('[data-testid="creation-overlay"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="creation-body"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="creation-overlay-close"]').exists()).toBe(true);
  });

  it("the overlay host mounts the named overlay body (the real trigger-to-overlay path)", () => {
    // Mounting the OverlayHost with a scoped slot that provides the overlay
    // body proves the named overlay is actually mounted (not just that a
    // trigger emits a name). Cycling the open-overlay name re-mounts the body.
    const wrapper = mount(OverlayHost, {
      props: { overlay: "settings", mapModel: LOCAL_MAP_SAMPLE },
      slots: {
        default: ({ overlay: name, mapModel }) =>
          name === "settings"
            ? h(SettingsOverlay, {})
            : name === "help"
              ? h(HelpOverlay, {})
              : h(MapOverlay, { localMap: mapModel }),
      },
    });
    expect(wrapper.find('[data-testid="overlay-host"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="settings-overlay"]').exists()).toBe(true);
  });
});
