// webclient-frame-resolver-registry: the declarative-frame resolver registry
// contract (openspec capability webclient-frame-resolution). Every assertion
// drives createFrameResolver over committed-state fixtures built from the
// exact protocol panel shapes the reducer accepts, and pins the four main
// requirements: committed-state-following + purity, the finite exploration
// table, verbatim domain rows with reproduced navigation rows, and the shared
// unresolvable marker with the server-authored reason.

import { describe, expect, it } from "vitest";
import { createFrameResolver } from "../stores/frame-resolvers.js";
import ExplorationMenu from "../lib/exploration_menu.js";
import {
  EPOCH_A,
  explorationActions,
  explorationPanel,
  localMapPanel,
  statusPanel,
} from "./store/protocol_fixtures.js";
import { SYNTH_SKILL, SYNTH_ITEM } from "./support/synthetic-data.mjs";

// File-local synthetic skill rows (test-data-independence): invented t_-keyed
// combat rows with invented prose; wire taxonomy values stay protocol-owned.
const T_A = SYNTH_SKILL.id;
const T_A_LABEL = SYNTH_SKILL.label;
const T_B = "t_gale_crescent";
const T_B_LABEL = "巒風刃";
const T_GROUP_FIRE_LABEL = "焰系";

// A committed-state object exactly as the protocol reducer surfaces it.
function committedState(overrides = {}) {
  return {
    protocolVersion: 1,
    epoch: EPOCH_A,
    revision: 1,
    mode: "exploration",
    panels: {
      status: statusPanel(),
      exploration: explorationPanel(),
      local_map: localMapPanel(),
      context_actions: explorationActions(),
    },
    ...overrides,
  };
}

function resolverFor(state) {
  return createFrameResolver({ getState: () => state });
}

function deepFreeze(value) {
  if (value && typeof value === "object") {
    Object.freeze(value);
    for (const child of Object.values(value)) deepFreeze(child);
  }
  return value;
}

describe("frame resolver — committed-state following and purity", () => {
  it("re-resolving after a newer committed snapshot names the newer exits with no stale row", () => {
    const state = committedState();
    const resolver = resolverFor(state);
    const before = resolver.resolve({ source: "exploration.root" });
    expect(before.items.map((i) => i.label)).toContain("西風酒館");

    // A newer committed snapshot replaces the exploration panel atomically.
    state.panels.exploration = explorationPanel({
      move: [
        {
          exit_ref: "west",
          label: "歸旅客棧",
          destination: "room:99",
          enabled: true,
          disabled_reason: null,
        },
      ],
    });
    state.revision = 2;

    const after = resolver.resolve({ source: "exploration.root" });
    const labels = after.items.map((i) => i.label);
    expect(labels).toContain("歸旅客棧");
    expect(labels).not.toContain("西風酒館");
    expect(labels).not.toContain("北岸大道");
  });

  it("resolving the same descriptor twice is deep-equal and mutates nothing (frozen state)", () => {
    const state = deepFreeze(committedState());
    const resolver = resolverFor(state);
    const first = resolver.resolve({ source: "exploration.root" });
    const second = resolver.resolve({ source: "exploration.root" });
    expect(second).toEqual(first);
    // Deep-equal menu identity beyond reference.
    expect(JSON.stringify(second)).toBe(JSON.stringify(first));
    // The exploration model resolves identically to a direct builder call —
    // no hidden model state participates. The root is the scene overview
    // (webclient-scene-overview-swap D1), not the tab root: it resolves to the
    // overview builder's own menu.
    expect(second).toEqual(
      ExplorationMenu.overviewMenu(state.panels.exploration, {
        currentNode: state.panels.local_map.current_node,
        suggestions: state.panels.context_actions.suggestions,
      }),
    );
  });

  it("a resolver throwing mid-build degrades to the marker without an exception", () => {
    const state = committedState();
    // A committed panel whose exit list read raises: the registry's exception
    // guard converts the throw to the shared marker (available panel, so no
    // authored reason).
    Object.defineProperty(state.panels.exploration, "move", {
      configurable: true,
      get() {
        throw new Error("boom");
      },
    });
    const resolver = resolverFor(state);
    expect(() => resolver.resolve({ source: "exploration.root" })).not.toThrow();
    expect(resolver.resolve({ source: "exploration.root" })).toEqual({
      unresolvable: true,
      reason: null,
    });
    // The guard converts every call over the poisoned panel; deleting the
    // poison restores resolution (the marker is not sticky).
    delete state.panels.exploration.move;
    state.panels.exploration.move = [];
    expect(resolver.resolve({ source: "exploration.root" }).unresolvable).toBeUndefined();
  });

  it("a resolver throwing while the exploration panel carries an unavailable reason reports it", () => {
    const state = committedState();
    // Unavailable exploration form: available false + server reason.
    state.panels.exploration = {
      schema_version: 1,
      available: false,
      reason: { code: "scene_lost", message: "這片區域暫時不可用。" },
    };
    const resolver = resolverFor(state);
    const result = resolver.resolve({ source: "exploration.root" });
    expect(result).toEqual({ unresolvable: true, reason: "這片區域暫時不可用。" });
  });
});

describe("frame resolver — the finite exploration table", () => {
  it("every table source resolves from a live committed snapshot with builder-identical rows", () => {
    const state = committedState();
    const resolver = resolverFor(state);
    const direct = ExplorationMenu.buildMenus(state.panels.exploration, {
      currentNode: state.panels.local_map.current_node,
      suggestions: state.panels.context_actions.suggestions,
    });
    // The root frame is the scene overview, not the tab root
    // (webclient-scene-overview-swap D1). The wait submenu is the exploration
    // family's remaining pushed frame; the move/look/interact frames are
    // retired (webclient-retire-exploration-submenus).
    for (const key of ["wait"]) {
      const resolved = resolver.resolve({ source: `exploration.${key}` });
      expect(resolved.unresolvable).toBeUndefined();
      expect(resolved).toEqual(direct.menus[key]);
    }
    const overview = resolver.resolve({ source: "exploration.root" });
    expect(overview.unresolvable).toBeUndefined();
    expect(overview).toEqual(
      ExplorationMenu.overviewMenu(state.panels.exploration, {
        currentNode: state.panels.local_map.current_node,
        suggestions: state.panels.context_actions.suggestions,
      }),
    );
    expect(overview.geometry).toBe("sections");
    expect(overview.sections.map((section) => section.key)).toEqual([
      "exits",
      "people",
      "objects",
      "footer",
    ]);
    expect(overview.sections.map((section) => section.count)).toEqual([2, 1, 1, 3]);
    // Target/keywords resolve through the same target seam the push sites use.
    // The target frame is the verb popover (`verbMenuFor`), not the
    // affordance grid (`targetMenuFor`).
    const verbMenu = resolver.resolve({ source: "exploration.target", params: { identity: 7 } });
    expect(verbMenu).toEqual(
      ExplorationMenu.verbMenuFor(direct, ExplorationMenu.targetById(direct, 7)),
    );
    expect(verbMenu.items[verbMenu.items.length - 1].goBack).toBe(true);
    expect(verbMenu.items.map((i) => i.key)).toContain("look-target");
    expect(verbMenu.grid).toBeUndefined();
    const keywords = resolver.resolve({ source: "exploration.keywords", params: { identity: 7 } });
    expect(keywords).toEqual(
      ExplorationMenu.keywordMenuFor(
        direct,
        ExplorationMenu.targetById(direct, 7),
        ExplorationMenu.scriptedAffordanceFor(ExplorationMenu.targetById(direct, 7)),
      ),
    );
    // Suggestions resolve through the shipped builder.
    const suggestions = resolver.resolve({ source: "exploration.suggestions" });
    expect(suggestions).toEqual(ExplorationMenu.suggestionsMenu(state.panels.context_actions.suggestions));
  });

  it("an unregistered source (including a reserved later-wave row) degrades to the marker", () => {
    const resolver = resolverFor(committedState());
    expect(resolver.resolve({ source: "services.board" })).toEqual({ unresolvable: true, reason: null });
    expect(resolver.resolve({ source: "combat.skill", params: { skillKey: "x" } })).toEqual({
      unresolvable: true,
      reason: null,
    });
    expect(resolver.resolve({})).toEqual({ unresolvable: true, reason: null });
    expect(resolver.resolve(null)).toEqual({ unresolvable: true, reason: null });
  });

  it("every retired exploration source resolves to the unresolvable marker", () => {
    // webclient-retire-exploration-submenus: the move/look/interact frames are
    // gone, so their descriptors are unregistered. A stray push for one
    // degrades to the shared marker and pops instead of resurrecting a pane.
    const FORMER_EXPLORATION_SOURCES = [
      "exploration.move",
      "exploration.look",
      "exploration.interact",
    ];
    const resolver = resolverFor(committedState());
    for (const source of FORMER_EXPLORATION_SOURCES) {
      expect(resolver.resolve({ source })).toEqual({ unresolvable: true, reason: null });
    }
  });

  it("suggestions degrade on unavailable/absent and resolve on generating/ready/degraded", () => {
    const state = committedState();
    const resolver = resolverFor(state);
    // The store fixture's default envelope is `generating`.
    const generating = resolver.resolve({ source: "exploration.suggestions" });
    expect(generating.items.map((i) => i.label)).toContain("AI 正在構思建議…");
    state.panels.context_actions = explorationActions({ suggestions: { status: "unavailable" } });
    expect(resolver.resolve({ source: "exploration.suggestions" })).toEqual({
      unresolvable: true,
      reason: null,
    });
    delete state.panels.context_actions;
    expect(resolver.resolve({ source: "exploration.suggestions" })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });
});

describe("frame resolver — verbatim domain rows, reproduced navigation rows", () => {
  it("a two-exit room's overview exit chips are exactly the two server exit rows", () => {
    const state = committedState();
    const resolver = resolverFor(state);
    const menu = resolver.resolve({ source: "exploration.root" });
    const panel = state.panels.exploration;
    const chips = menu.items.filter((item) => item.key.startsWith("exit-"));
    expect(chips).toHaveLength(panel.move.length);
    panel.move.forEach((exitRow, index) => {
      const row = chips[index];
      // Builder-verbatim chip shape (plain labels, payloads, disabled reasons).
      expect(JSON.parse(JSON.stringify(row))).toEqual(
        JSON.parse(
          JSON.stringify(
            ExplorationMenu.moveItems(panel, state.panels.local_map.current_node)[index],
          ),
        ),
      );
      if (exitRow.enabled) {
        // The move payload carries the canonical current_node from local_map.
        expect(row.actionId).toBe("explore.move");
        expect(row.payload).toEqual({
          exit_ref: exitRow.exit_ref,
          current_node: state.panels.local_map.current_node,
        });
      } else {
        expect(row.actionId).toBe(null);
      }
      expect(row.disabledReason).toEqual(exitRow.disabled_reason);
    });
    // The overview is the root frame: no back row and no empty placeholder.
    expect(menu.items.some((item) => item.goBack)).toBe(false);
    expect(menu.items.some((item) => item.key === "move-empty")).toBe(false);
  });

  it("a traversable exit stays activatable when local_map is unavailable (fresh character, no map-knowledge yet)", () => {
    // Reproduces the 虛境 (starting-room) bug: a brand-new character has no
    // recorded map-knowledge yet, so `local_map` legitimately reports
    // unavailable (map-knowledge spec), but the exit itself is still a
    // perfectly traversable, server-enabled row — the overview must not treat
    // "no minimap" as "no movement".
    const state = committedState();
    state.panels.local_map = {
      schema_version: 1,
      available: false,
      reason: { code: "map_unavailable", message: "區域地圖目前無法顯示" },
    };
    state.panels.context_actions = explorationActions({
      affordances: [
        {
          action_id: "explore.move",
          label: "西風酒館",
          params: { exit_ref: "east", current_node: "room:42" },
          freeform: false,
          navigation: false,
          enabled: true,
          disabled_reason: null,
        },
      ],
    });
    const resolver = resolverFor(state);
    const menu = resolver.resolve({ source: "exploration.root" });
    const enabledChip = menu.items.find((item) => item.key === "exit-east");
    expect(enabledChip.enabled).toBe(true);
    expect(enabledChip.actionId).toBe("explore.move");
    expect(enabledChip.payload).toEqual({ exit_ref: "east", current_node: "room:42" });
  });

  it("look chips and the target popover reproduce labels, actions, payloads, and disabled reasons verbatim", () => {
    const state = committedState();
    const resolver = resolverFor(state);
    const panel = state.panels.exploration;

    const overview = resolver.resolve({ source: "exploration.root" });
    const roomChip = overview.items.find((i) => i.key === "look-room");
    expect(roomChip.payload).toEqual({ room: true });
    expect(roomChip.description).toBe(panel.look.room.display_name);
    for (const entity of panel.look.entities) {
      // An entity with an interact descriptor is a person chip instead; the
      // builder's own look rows still carry the look payload.
      const lookRow = ExplorationMenu.lookItems(panel).find(
        (i) => i.key === `entity-${entity.identity}`,
      );
      expect(lookRow.label).toBe(entity.display_name);
      expect(lookRow.actionId).toBe("explore.look");
      expect(lookRow.payload).toEqual({ target_id: entity.identity });
    }

    const target = resolver.resolve({ source: "exploration.target", params: { identity: 7 } });
    const talk = target.items.find((i) => i.key === "talk-open");
    expect(talk.label).toBe("交談");
    const party = panel.interact[0].affordances.find((a) => a.action_id === "explore.party_invite");
    if (party) {
      const row = target.items.find((i) => i.key === "party-invite");
      expect(row.label).toBe(party.label);
      expect(row.disabledReason).toEqual(party.disabled_reason);
    }
    // Server-authored disabled reason survives verbatim on the locked exit.
    const locked = panel.move.find((m) => m.disabled_reason);
    const lockedChip = overview.items.find((i) => i.key === `exit-${locked.exit_ref}`);
    expect(lockedChip.disabledReason).toEqual(locked.disabled_reason);
  });

  it("the navigation source carries the bar's entries, and only while the panel is available", () => {
    // webclient-scene-overview-swap: the top navigation bar's character /
    // quest / inventory entries are no dock frame's rows any more — the bar
    // resolves them from this source, whose builder outlives the tab root
    // webclient-retire-exploration-submenus deletes.
    const state = committedState();
    const resolver = resolverFor(state);
    const nav = resolver.resolve({ source: "exploration.navigation" });
    expect(nav.unresolvable).toBeUndefined();
    expect(nav.items.map((item) => item.key)).toEqual(["character", "quests", "inventory"]);
    expect(nav.items.find((item) => item.key === "character").openCharacter).toBe(true);
    expect(nav.items.find((item) => item.key === "quests").openDrawer).toBe("quest");
    expect(nav.items.find((item) => item.key === "inventory").openDrawer).toBe("inventory");
    // A capability surface the panel does not report available is absent (no
    // dead functional entry): the source and its builder agree.
    state.panels.exploration = explorationPanel({ quests: { available: false } });
    const narrowed = resolver.resolve({ source: "exploration.navigation" });
    expect(narrowed.items.map((item) => item.key)).toEqual(["character", "inventory"]);
    const bar = ExplorationMenu.navigationItems(state.panels.exploration);
    expect(bar.filter((item) => item.key === "quests")).toHaveLength(0);

    // An unavailable exploration panel degrades to the shared marker.
    state.panels.exploration = {
      schema_version: 3,
      available: false,
      reason: { code: "scene_lost", message: "這片區域暫時不可用。" },
    };
    expect(resolver.resolve({ source: "exploration.navigation" })).toEqual({
      unresolvable: true,
      reason: "這片區域暫時不可用。",
    });
  });

  it("the root is the scene overview: chip rows, a footer, and no tab or navigation entry", () => {
    const resolver = resolverFor(committedState());
    const root = resolver.resolve({ source: "exploration.root" });
    const keys = root.items.map((i) => i.key);
    // The reading order: exits, people, objects, then the label-less footer.
    expect(root.sections.map((section) => section.key)).toEqual([
      "exits",
      "people",
      "objects",
      "footer",
    ]);
    expect(keys).toContain("exit-east");
    expect(keys).toContain("target-7");
    expect(keys).toContain("object-3");
    expect(keys).toContain("look-room");
    expect(keys).toContain("wait");
    // A generating envelope adds the footer suggestions chip (builder-owned).
    expect(keys).toContain("suggestions");
    // No tab-root entry and no navigation-carried entry survives on the root.
    for (const gone of ["move", "look", "interact", "character", "quests", "inventory", "bag"]) {
      expect(keys).not.toContain(gone);
    }
  });
});

describe("frame resolver — ownership isolation", () => {
  it("mutating a resolved menu never writes back into committed state or later resolves", () => {
    const state = committedState();
    state.panels.context_actions = explorationActions({
      suggestions: {
        status: "ready",
        cards: [
          {
            label: "進入酒館",
            action_id: "explore.move",
            params: { exit_ref: "east" },
            source: "llm",
          },
        ],
        dismissed_labels: [],
      },
    });
    const resolver = resolverFor(state);
    const target = resolver.resolve({ source: "exploration.target", params: { identity: 7 } });
    const cleanTargetJson = JSON.stringify(target);
    const before = JSON.stringify(state.panels, (k, v) => v);
    // Write through every reference the builder handed out.
    target.target.display_name = "POISONED";
    const overview = resolver.resolve({ source: "exploration.root" });
    const disabledChip = overview.items.find((i) => i.disabledReason);
    if (disabledChip) disabledChip.disabledReason.message = "POISONED";
    const suggestions = resolver.resolve({ source: "exploration.suggestions" });
    suggestions.items.forEach((item) => {
      if (item.payload && item.payload.exit_ref) item.payload.exit_ref = "POISONED";
    });
    expect(JSON.stringify(state.panels, (k, v) => v)).toBe(before);
    // A subsequent resolve derives from untouched committed state — the
    // poisoned copy is the caller's own, not the registry's.
    const after = resolver.resolve({ source: "exploration.target", params: { identity: 7 } });
    expect(JSON.stringify(after)).toBe(cleanTargetJson);
    expect(JSON.stringify(state.panels, (k, v) => v)).toBe(before);
  });
});

describe("frame resolver — the degradation marker", () => {
  it("null-reason degradations return the one frozen shared marker; authored reasons are frozen too", () => {
    const resolver = resolverFor(committedState());
    const a = resolver.resolve({ source: "services.board" });
    const b = resolver.resolve({});
    expect(a).toBe(b); // identity: the single shared sentinel
    expect(Object.isFrozen(a)).toBe(true);
    const state = committedState();
    state.panels.exploration = {
      schema_version: 1,
      available: false,
      reason: { code: "offline", message: "探索畫面目前不可用。" },
    };
    const authored = resolverFor(state).resolve({ source: "exploration.root" });
    expect(Object.isFrozen(authored)).toBe(true);
    expect(() => {
      "use strict";
      authored.reason = "tampered";
    }).toThrow();
  });

  it("suggestions belong to the exploration family: an unavailable exploration panel degrades even with a live envelope", () => {
    const state = committedState();
    state.panels.exploration = {
      schema_version: 1,
      available: false,
      reason: { code: "scene_lost", message: "這片區域已不可用。" },
    };
    // context_actions still carries a ready envelope.
    const resolver = resolverFor(state);
    expect(resolver.resolve({ source: "exploration.suggestions" })).toEqual({
      unresolvable: true,
      reason: "這片區域已不可用。",
    });
  });

  it("an unavailable context_actions envelope degrades with its own authored reason", () => {
    const state = committedState();
    state.panels.context_actions = {
      schema_version: 5,
      available: false,
      kind: "exploration",
      reason: { code: "ai_offline", message: "建議服務目前離線。" },
      actions: [],
      items: [],
    };
    const resolver = resolverFor(state);
    expect(resolver.resolve({ source: "exploration.suggestions" })).toEqual({
      unresolvable: true,
      reason: "建議服務目前離線。",
    });
  });
});

describe("frame resolver — (legacy) the degradation marker", () => {
  it("a lost target identity yields the marker with a null reason", () => {
    const state = committedState();
    const resolver = resolverFor(state);
    expect(resolver.resolve({ source: "exploration.target", params: { identity: 999 } })).toEqual({
      unresolvable: true,
      reason: null,
    });
    expect(resolver.resolve({ source: "exploration.keywords", params: {} })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });

  it("an unavailable exploration panel reports its server message verbatim", () => {
    const state = committedState();
    state.panels.exploration = {
      schema_version: 1,
      available: false,
      reason: { code: "offline", message: "探索畫面目前不可用。" },
    };
    const resolver = resolverFor(state);
    expect(resolver.resolve({ source: "exploration.root" })).toEqual({
      unresolvable: true,
      reason: "探索畫面目前不可用。",
    });
  });

  it("an absent exploration panel degrades with a null reason and never throws", () => {
    const state = committedState();
    delete state.panels.exploration;
    const resolver = resolverFor(state);
    expect(() => resolver.resolve({ source: "exploration.wait" })).not.toThrow();
    expect(resolver.resolve({ source: "exploration.wait" })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });
});

// --- webclient-services-combat-creation-frames: the completed table ---------

import CombatMenu from "../lib/combat_menu.js";
import CreationMenu from "../lib/creation_menu.js";

describe("frame resolver — retired services family (unresolvable)", () => {
  const FORMER_SERVICES_SOURCES = [
    "services.root",
    "services.guild",
    "services.board",
    "services.quests",
    "services.shop",
    "services.stock",
    "services.sell",
    "services.quest-detail",
    "services.confirm",
  ];

  it.each(FORMER_SERVICES_SOURCES)(
    "every former services source (%s) resolves to the unresolvable marker",
    (source) => {
      const resolver = resolverFor(committedState());
      expect(resolver.resolve({ source, params: { questIndex: 0 } })).toEqual({
        unresolvable: true,
        reason: null,
      });
    }
  );
});

function combatFixturePanel(overrides = {}) {
  const skill = (extra) =>
    Object.assign(
      {
        key: T_A,
        label: T_A_LABEL,
        description: "凝聚火焰魔力。",
        cost: { mp: 20 },
        target_spec: "single",
        element: "fire",
        enabled: true,
        disabled_reason: null,
        targets: [7],
        shorthands: [],
          // A freeform-scale skill: the scale step exists so the resolver's
          // selection-preservation path (rebuildForPanel) is exercised.
          freeform_scales: [
            { scale: 1, label: "1", mp_cost: 20 },
            { scale: 2, label: "2", mp_cost: 40 },
          ],
      },
      extra
    );
  return {
    schema_version: 5,
    available: true,
    kind: "combat",
    session: { session_id: "hostile:1:0", mode: "hostile", round: 1, state: "ready", reason: null },
    participants: [
      { identity: 7, token: "e1", display_name: "哥布林", team: "foes", state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null },
    ],
    root_actions: ["attack", "skills", "items", "defend", "flee"],
    secondary_actions: ["forfeit"],
    skills: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [{ group: "fire", label: T_GROUP_FIRE_LABEL, skills: [skill({}), skill({ key: T_B, label: T_B_LABEL, target_spec: "area", targets: [7], shorthands: ["all"] })] }],
      },
    ],
    suggestions: { status: "unavailable" },
    ...overrides,
  };
}

function combatState(panel = combatFixturePanel()) {
  return committedState({ mode: "combat", panels: { context_actions: panel } });
}

describe("frame resolver — the combat family (declared model-state exception)", () => {
  it("every combat source resolves from a live combat snapshot", () => {
    const panel = combatFixturePanel();
    const resolver = resolverFor(combatState(panel));
    const model = CombatMenu.buildMenus(panel, {});
    expect(resolver.resolve({ source: "combat.root" })).toEqual(model.menus.root);
    expect(resolver.resolve({ source: "combat.categories" })).toEqual(model.menus.categories);
    expect(resolver.resolve({ source: "combat.forfeit" })).toEqual(model.menus.forfeit);
    expect(resolver.resolve({ source: "combat.category", params: { categoryIndex: 0 } })).toEqual(
      CombatMenu.openCategory(model, 0)
    );
    expect(resolver.resolve({ source: "combat.group", params: { categoryIndex: 0, groupIndex: 0 } })).toEqual(
      CombatMenu.openGroup(model, 0, 0)
    );
    expect(resolver.resolve({ source: "combat.skill", params: { skillKey: T_A } })).toEqual(
      CombatMenu.openSkill(model, T_A)
    );
    expect(resolver.resolve({ source: "combat.target", params: { skillKey: T_A } })).toEqual(
      CombatMenu.openSkillTargets(model, T_A)
    );
  });

  it("repeat resolution against one committed state is idempotent", () => {
    const resolver = resolverFor(combatState());
    const first = resolver.resolve({ source: "combat.skill", params: { skillKey: T_B } });
    const model = resolver.combatModel();
    const before = JSON.stringify({ focus: model.focusSkillKey, skills: model.skills });
    const second = resolver.resolve({ source: "combat.skill", params: { skillKey: T_B } });
    expect(second).toEqual(first);
    expect(JSON.stringify({ focus: model.focusSkillKey, skills: model.skills })).toBe(before);
  });

  it("selection survives a panel replacement through rebuildForPanel", () => {
    const panel = combatFixturePanel();
    const state = combatState(panel);
    const resolver = resolverFor(state);
    resolver.resolve({ source: "combat.root" });
    const model = resolver.combatModel();
    // Client-local selections (the store's combat interactions).
    model.focusSkillKey = T_A;
    CombatMenu.chooseScale(model, T_A, 2);
    CombatMenu.toggleArea(model, T_B, 7);
    // A panel replacement (round advances) preserves the still-valid scale.
    const replaced = combatFixturePanel();
    replaced.session.round = 2;
    state.panels.context_actions = replaced;
    const target = resolver.resolve({ source: "combat.target", params: { skillKey: T_A } });
    expect(target.items[0].payload.scale).toBe(2);
    // Shipped rebuildForPanel semantics (its own docstring): a panel
    // replacement keeps the still-valid scale and DETERMINISTICALLY resets
    // the AREA candidates to their default (no selection = all candidates).
    expect(resolver.combatModel().skillByKey[T_B].selected).toEqual([]);
    // Second resolution: idempotent, no further model change.
    expect(resolver.resolve({ source: "combat.target", params: { skillKey: T_A } })).toEqual(target);
  });

  it("a non-combat committed state clears the model — re-adoption starts fresh", () => {
    const state = combatState();
    const resolver = resolverFor(state);
    resolver.resolve({ source: "combat.root" });
    CombatMenu.chooseScale(resolver.combatModel(), T_A, 2);
    // Leaving combat (an exploration-form panel commits).
    state.mode = "exploration";
    state.panels.context_actions = explorationPanel();
    expect(resolver.resolve({ source: "combat.root" })).toEqual({ unresolvable: true, reason: null });
    // A byte-identical combat panel is re-adopted: no stale selection.
    state.mode = "combat";
    delete state.panels.context_actions;
    const fresh = combatFixturePanel();
    state.panels.context_actions = fresh;
    const target = resolver.resolve({ source: "combat.target", params: { skillKey: T_A } });
    // Fresh adoption starts at the default scale 1 — NOT the previous ×2.
    expect(target.items[0].payload.scale).toBe(1);
    expect(resolver.combatModel().focusSkillKey).toBe(null);
  });

  it("an absent skill key degrades like a lost identity", () => {
    const resolver = resolverFor(combatState());
    expect(resolver.resolve({ source: "combat.skill", params: { skillKey: "vanished" } })).toEqual({
      unresolvable: true,
      reason: null,
    });
    expect(resolver.resolve({ source: "combat.category", params: { categoryIndex: 4 } })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });
});

function creationPanelFixture(overrides = {}) {
  return {
    schema_version: 1,
    available: true,
    presets: [{ key: "sword", display_name: "見習劍士", race_description: "人類", emphasis: "力量", background: "商隊護衛" }],
    custom: { races: [], affinity_elements: [], point_pool: 0 },
    draft: null,
    ...overrides,
  };
}

describe("frame resolver — the creation family", () => {
  it("root and presets resolve to the builder menus", () => {
    const panel = creationPanelFixture();
    const resolver = resolverFor(committedState({ mode: "creation", panels: { creation: panel } }));
    const model = CreationMenu.buildMenus(panel);
    expect(resolver.resolve({ source: "creation.root" })).toEqual(model.menus.root);
    expect(resolver.resolve({ source: "creation.presets" })).toEqual(model.menus.presets);
  });

  it("form frames resolve to the shared empty marker frame", () => {
    const resolver = resolverFor(committedState({ mode: "creation", panels: { creation: creationPanelFixture() } }));
    expect(resolver.resolve({ source: "creation.form", params: { view: "custom" } })).toEqual({
      items: [],
      focusKey: null,
    });
    expect(resolver.resolve({ source: "creation.form", params: { view: "concept" } })).toEqual({
      items: [],
      focusKey: null,
    });
    expect(resolver.resolve({ source: "creation.form", params: { view: "bogus" } })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });

  it("confirm frames carry the stage's exact server-facing items", () => {
    const resolver = resolverFor(committedState({ mode: "creation", panels: { creation: creationPanelFixture() } }));
    expect(resolver.resolve({ source: "creation.confirm", params: { kind: "preset", presetKey: "sword" } })).toEqual(
      CreationMenu.activateConfirm("sword")
    );
    expect(resolver.resolve({ source: "creation.confirm", params: { kind: "custom" } })).toEqual(
      CreationMenu.activateConfirm(null)
    );
    expect(resolver.resolve({ source: "creation.confirm", params: { kind: "reset" } })).toEqual(
      CreationMenu.confirmMenu("確認清除角色草稿？此操作無法回復。", CreationMenu.RESET_ACTION, {}, CreationMenu.RESET_DISPLAY)
    );
    expect(resolver.resolve({ source: "creation.confirm", params: {} })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });

  it("an absent creation panel degrades every creation source", () => {
    const resolver = resolverFor(committedState({ mode: "creation", panels: {} }));
    expect(resolver.resolve({ source: "creation.root" })).toEqual({ unresolvable: true, reason: null });
    expect(resolver.resolve({ source: "creation.confirm", params: { kind: "custom" } })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });
});
