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
    const before = resolver.resolve({ source: "exploration.move" });
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

    const after = resolver.resolve({ source: "exploration.move" });
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
    // no hidden model state participates.
    const direct = ExplorationMenu.buildMenus(state.panels.exploration, {
      currentNode: state.panels.local_map.current_node,
      suggestions: state.panels.context_actions.suggestions,
    });
    expect(second.items).toEqual(direct.menus.root.items);
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
    expect(() => resolver.resolve({ source: "exploration.move" })).not.toThrow();
    expect(resolver.resolve({ source: "exploration.move" })).toEqual({
      unresolvable: true,
      reason: null,
    });
    // The guard converts every call over the poisoned panel; deleting the
    // poison restores resolution (the marker is not sticky).
    delete state.panels.exploration.move;
    state.panels.exploration.move = [];
    expect(resolver.resolve({ source: "exploration.move" }).unresolvable).toBeUndefined();
  });

  it("a resolver throwing while the exploration panel carries an unavailable reason reports it", () => {
    const state = committedState();
    // Unavailable exploration form: available false + server reason.
    state.panels.exploration = {
      schema_version: 1,
      available: false,
      reason: { code: "scene_lost", message: "這片區域暂时不可用。" },
    };
    const resolver = resolverFor(state);
    const result = resolver.resolve({ source: "exploration.move" });
    expect(result).toEqual({ unresolvable: true, reason: "這片區域暂时不可用。" });
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
    for (const key of ["root", "move", "look", "interact", "wait"]) {
      const resolved = resolver.resolve({ source: `exploration.${key}` });
      expect(resolved.unresolvable).toBeUndefined();
      expect(resolved).toEqual(direct.menus[key]);
    }
    // Target/keywords resolve through the same target seam the push sites use.
    const targetMenu = resolver.resolve({ source: "exploration.target", params: { identity: 7 } });
    expect(targetMenu).toEqual(
      ExplorationMenu.targetMenuFor(direct, ExplorationMenu.targetById(direct, 7)),
    );
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
  it("a two-exit room's move frame is exactly the two server exit rows plus the builder back row", () => {
    const state = committedState();
    const resolver = resolverFor(state);
    const menu = resolver.resolve({ source: "exploration.move" });
    const panel = state.panels.exploration;
    expect(menu.items).toHaveLength(panel.move.length + 1);
    panel.move.forEach((exitRow, index) => {
      const row = menu.items[index];
      // Builder-verbatim row shape (labels, disabled suffix, payloads).
      expect(JSON.parse(JSON.stringify(row))).toEqual(
        JSON.parse(
          JSON.stringify(
            ExplorationMenu.buildMenus(panel, {
              currentNode: state.panels.local_map.current_node,
              suggestions: null,
            }).menus.move.items[index],
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
    expect(menu.items[menu.items.length - 1].goBack).toBe(true);
  });

  it("look and target frames reproduce labels, sub-lines, actions, payloads, and disabled reasons verbatim", () => {
    const state = committedState();
    const resolver = resolverFor(state);
    const panel = state.panels.exploration;

    const look = resolver.resolve({ source: "exploration.look" });
    const roomRow = look.items.find((i) => i.key === "look-room");
    expect(roomRow.payload).toEqual({ room: true });
    expect(roomRow.description).toBe(panel.look.room.display_name);
    for (const entity of panel.look.entities) {
      const row = look.items.find((i) => i.key === `entity-${entity.identity}`);
      expect(row.label).toBe(entity.display_name);
      expect(row.actionId).toBe("explore.look");
      expect(row.payload).toEqual({ target_id: entity.identity });
    }

    const target = resolver.resolve({ source: "exploration.target", params: { identity: 7 } });
    const scripted = target.items.find((i) => i.key === "talk-scripted");
    expect(scripted.label).toBe("交談");
    const party = panel.interact[0].affordances.find((a) => a.action_id === "explore.party_invite");
    if (party) {
      const row = target.items.find((i) => i.key === "party-invite");
      expect(row.label).toBe(party.label);
      expect(row.disabledReason).toEqual(party.disabled_reason);
    }
    // Server-authored disabled reason survives verbatim on the locked exit.
    const locked = panel.move.find((m) => m.disabled_reason);
    const move = resolver.resolve({ source: "exploration.move" });
    const lockedRow = move.items.find((i) => i.key === `exit-${locked.exit_ref}`);
    expect(lockedRow.disabledReason).toEqual(locked.disabled_reason);
  });

  it("the root reproduces the client-owned navigation rows the dock contract requires", () => {
    const resolver = resolverFor(committedState());
    const root = resolver.resolve({ source: "exploration.root" });
    const keys = root.items.map((i) => i.key);
    expect(keys).toContain("move");
    expect(keys).toContain("look");
    expect(keys).toContain("interact");
    expect(keys).toContain("wait");
    // A generating envelope adds the suggestions root entry (builder-owned).
    expect(keys).toContain("suggestions");
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
    const move = resolver.resolve({ source: "exploration.move" });
    const disabledRow = move.items.find((i) => i.disabledReason);
    if (disabledRow) disabledRow.disabledReason.message = "POISONED";
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
    expect(() => resolver.resolve({ source: "exploration.look" })).not.toThrow();
    expect(resolver.resolve({ source: "exploration.look" })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });
});

// --- webclient-services-combat-creation-frames: the completed table ---------

import ServiceMenu from "../lib/service_menu.js";
import CombatMenu from "../lib/combat_menu.js";
import CreationMenu from "../lib/creation_menu.js";

function guildSurface() {
  return {
    registration: {
      enabled: true,
      action_id: "guild.register",
      label: "登記公會",
      disabled_reason: null,
    },
    board: [
      {
        definition_key: "q-wolves",
        display_name: "狼患",
        objective_summary: "清除商路狼群",
        reward_summary: "報酬 500 銅",
        accept: { enabled: true, action_id: "guild.quest_accept", label: "接取", disabled_reason: null },
      },
    ],
    quests: [
      {
        quest_id: "q-1",
        display_name: "商路巡視",
        state: "active",
        detail: "沿商路巡視一輪。",
        abandon: { enabled: true, action_id: "guild.quest_abandon", label: "放棄", disabled_reason: null },
        turnin: { enabled: false, action_id: "guild.quest_turnin", label: "回報", disabled_reason: { code: "incomplete", message: "目標尚未完成。" } },
      },
      {
        quest_id: "q-2",
        display_name: "失落的貨箱",
        state: "active",
        detail: "找回遺失的貨箱。",
        abandon: { enabled: false, action_id: "guild.quest_abandon", label: "放棄", disabled_reason: { code: "locked", message: "此任務無法放棄。" } },
        turnin: { enabled: true, action_id: "guild.quest_turnin", label: "回報", disabled_reason: null },
      },
    ],
    rank: null,
  };
}

function shopSurface() {
  return {
    open: true,
    stock: [
      {
        item_key: "potion",
        display_name: "治療藥水",
        buy_copper: 50,
        stock: 4,
        buy: { enabled: true, action_id: "shop.buy", quantity: { min: 1, max: 9 }, disabled_reason: null },
      },
    ],
    sellable: [
      {
        item_key: "pelt",
        display_name: "獸皮",
        sell_copper: 12,
        held: 3,
        sell: { enabled: true, action_id: "shop.sell", quantity: { min: 1, max: 3 }, disabled_reason: null },
      },
    ],
  };
}

function servicesPanel(overrides = {}) {
  return {
    schema_version: 1,
    available: true,
    guild: guildSurface(),
    shop: shopSurface(),
    ...overrides,
  };
}

function servicesState(panel = servicesPanel()) {
  return committedState({ mode: "exploration", panels: { services: panel } });
}

describe("frame resolver — the services family", () => {
  it("every services source resolves to the builder menu verbatim", () => {
    const resolver = resolverFor(servicesState());
    const model = ServiceMenu.buildMenus(servicesPanel());
    for (const key of ["root", "guild", "board", "quests", "shop", "stock", "sell"]) {
      expect(resolver.resolve({ source: `services.${key}` })).toEqual(model.menus[key]);
    }
  });

  it("quest-detail resolves by the row index the quest rows carry", () => {
    const resolver = resolverFor(servicesState());
    const model = ServiceMenu.buildMenus(servicesPanel());
    const menu = resolver.resolve({ source: "services.quest-detail", params: { questIndex: 1 } });
    expect(menu).toEqual(ServiceMenu.questMenuFor(model, servicesPanel().guild.quests[1]));
    expect(menu.items.map((i) => i.key)).toEqual([
      "quest-detail",
      "quest-abandon-q-2",
      "quest-turnin-q-2",
    ]);
  });

  it("an out-of-range questIndex is the identity-loss marker", () => {
    const resolver = resolverFor(servicesState());
    expect(resolver.resolve({ source: "services.quest-detail", params: { questIndex: 9 } })).toEqual({
      unresolvable: true,
      reason: null,
    });
    expect(resolver.resolve({ source: "services.quest-detail", params: {} })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });

  it("the confirm frame derives from the composed quest row's server fields", () => {
    const resolver = resolverFor(servicesState());
    // q-1: the enabled abandon row carries the confirm fields.
    expect(resolver.resolve({ source: "services.confirm", params: { questIndex: 0 } })).toEqual(
      ServiceMenu.confirmMenu("確認放棄", "guild.quest_abandon", { quest_id: "q-1" }, null)
    );
    // q-2: the disabled abandon row has no confirmation → degrade, no fabrication.
    expect(resolver.resolve({ source: "services.confirm", params: { questIndex: 1 } })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });

  it("a vanished quest degrades like a lost identity, keeping any server reason", () => {
    const panel = servicesPanel();
    const resolver = resolverFor(servicesState(panel));
    expect(resolver.resolve({ source: "services.quest-detail", params: { questIndex: 0 } }).items).toBeTruthy();
    // A committed update removes the quest: the open frame degrades.
    panel.guild.quests = [];
    expect(resolver.resolve({ source: "services.quest-detail", params: { questIndex: 0 } })).toEqual({
      unresolvable: true,
      reason: null,
    });
  });

  it("an unavailable services panel reports its server message verbatim", () => {
    const resolver = resolverFor(
      servicesState({ available: false, reason: { code: "offline", message: "服務目前不可用。" } })
    );
    expect(resolver.resolve({ source: "services.guild" })).toEqual({
      unresolvable: true,
      reason: "服務目前不可用。",
    });
    expect(resolver.resolve({ source: "services.quest-detail", params: { questIndex: 0 } })).toEqual({
      unresolvable: true,
      reason: "服務目前不可用。",
    });
  });
});

function combatFixturePanel(overrides = {}) {
  const skill = (extra) =>
    Object.assign(
      {
        key: "fire_ball",
        label: "火球術",
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
        groups: [{ group: "fire", label: "火", skills: [skill({}), skill({ key: "wind_blade", label: "風刃術", target_spec: "area", targets: [7], shorthands: ["all"] })] }],
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
    expect(resolver.resolve({ source: "combat.skill", params: { skillKey: "fire_ball" } })).toEqual(
      CombatMenu.openSkill(model, "fire_ball")
    );
    expect(resolver.resolve({ source: "combat.target", params: { skillKey: "fire_ball" } })).toEqual(
      CombatMenu.openSkillTargets(model, "fire_ball")
    );
  });

  it("repeat resolution against one committed state is idempotent", () => {
    const resolver = resolverFor(combatState());
    const first = resolver.resolve({ source: "combat.skill", params: { skillKey: "wind_blade" } });
    const model = resolver.combatModel();
    const before = JSON.stringify({ focus: model.focusSkillKey, skills: model.skills });
    const second = resolver.resolve({ source: "combat.skill", params: { skillKey: "wind_blade" } });
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
    model.focusSkillKey = "fire_ball";
    CombatMenu.chooseScale(model, "fire_ball", 2);
    CombatMenu.toggleArea(model, "wind_blade", 7);
    // A panel replacement (round advances) preserves the still-valid scale.
    const replaced = combatFixturePanel();
    replaced.session.round = 2;
    state.panels.context_actions = replaced;
    const target = resolver.resolve({ source: "combat.target", params: { skillKey: "fire_ball" } });
    expect(target.items[0].payload.scale).toBe(2);
    // Shipped rebuildForPanel semantics (its own docstring): a panel
    // replacement keeps the still-valid scale and DETERMINISTICALLY resets
    // the AREA candidates to their default (no selection = all candidates).
    expect(resolver.combatModel().skillByKey.wind_blade.selected).toEqual([]);
    // Second resolution: idempotent, no further model change.
    expect(resolver.resolve({ source: "combat.target", params: { skillKey: "fire_ball" } })).toEqual(target);
  });

  it("a non-combat committed state clears the model — re-adoption starts fresh", () => {
    const state = combatState();
    const resolver = resolverFor(state);
    resolver.resolve({ source: "combat.root" });
    CombatMenu.chooseScale(resolver.combatModel(), "fire_ball", 2);
    // Leaving combat (an exploration-form panel commits).
    state.mode = "exploration";
    state.panels.context_actions = explorationPanel();
    expect(resolver.resolve({ source: "combat.root" })).toEqual({ unresolvable: true, reason: null });
    // A byte-identical combat panel is re-adopted: no stale selection.
    state.mode = "combat";
    delete state.panels.context_actions;
    const fresh = combatFixturePanel();
    state.panels.context_actions = fresh;
    const target = resolver.resolve({ source: "combat.target", params: { skillKey: "fire_ball" } });
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
