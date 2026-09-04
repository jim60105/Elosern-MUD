// complete-ui-command-echo D6: the per-surface behavioral proof. One table
// row per dispatch surface; every row asserts the exact echo line, exactly
// one input line per deliberate activation, the `ui_action` envelope's
// byte-identity (the descriptor — forwarded or filled — never enters it),
// and literal-text rendering. Silences are explicit expected-silence rows:
// no dispatch path may fall silent unannounced.
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import ServiceMenu from "../../lib/service_menu.js";
import COVERAGE_MANIFEST from "../../../static/webclient/js/tests/command_echo_coverage_manifest.json";
import {
  SERVICES_PANEL_SAMPLE,
  CREATION_PANEL_SAMPLE,
} from "../../stories/fixtures.js";
import * as fx from "./protocol_fixtures.js";

const ENVELOPE_KEYS = [
  "action_id",
  "base_revision",
  "payload",
  "presentation_epoch",
  "protocol_version",
  "request_id",
];

// The shared coverage manifest (single id source for the Node catalog gate,
// this behavioral table, and the Python registry pin).
const REGISTERED_MUTATION_IDS = COVERAGE_MANIFEST.registeredMutationActionIds;
const SILENT_IDS = COVERAGE_MANIFEST.silentPresentationControlIds;

const FREEFORM_SCALES = [
  { scale: 0.25, label: "1/4", mp_cost: 4 },
  { scale: 0.5, label: "1/2", mp_cost: 7 },
  { scale: 1, label: "1", mp_cost: 14 },
  { scale: 2, label: "2", mp_cost: 28 },
  { scale: 4, label: "4", mp_cost: 56 },
];

function nestedSkills(skills) {
  return [
    {
      category: "innate_gift",
      label: "天賦",
      groups: [{ group: null, label: null, skills }],
    },
  ];
}

const SKILL_ATTACK = {
  key: "basic_attack",
  label: "攻擊",
  description: "基本攻擊，對單一目標造成傷害。",
  cost: {},
  target_spec: "single",
  element: null,
  enabled: true,
  disabled_reason: null,
  targets: [7, 8],
  shorthands: [],
};

const SKILL_WIND = {
  key: "wind_blade",
  label: "風刃術",
  description: "以風刃襲擊單一目標。",
  cost: { mp: 14 },
  target_spec: "single",
  element: null,
  enabled: true,
  disabled_reason: null,
  targets: [7, 8],
  shorthands: [],
  freeform_scales: FREEFORM_SCALES,
};

const SKILL_FIRE = {
  key: "fire_ball",
  label: "火球術",
  description: "轟擊範圍內的所有敵人。",
  cost: { mp: 10 },
  target_spec: "area",
  element: null,
  enabled: true,
  disabled_reason: null,
  targets: [7, 8],
  shorthands: ["all-enemies"],
};

describe("per-surface command echo (complete-ui-command-echo D6)", () => {
  let store;
  let sender;

  function openExploration(extraPanels = {}) {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        {
          protocol_version: 1,
          presentation_epoch: fx.EPOCH_A,
          revision: 1,
          mode: "exploration",
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            context_actions: fx.explorationActions(),
            local_map: fx.localMapPanel(),
            services: SERVICES_PANEL_SAMPLE,
            ...extraPanels,
          },
          layout_version: 1,
          server_time: fx.serverTime(),
        },
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  function enterCombat(skills, revision = 2) {
    const result = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision,
          mode: "combat",
          panels: { context_actions: fx.combatActions({ skills: nestedSkills(skills) }) },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  function enterCreation(revision = 2) {
    const result = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision,
          mode: "creation",
          panels: { creation: CREATION_PANEL_SAMPLE },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  function echoLines() {
    return store.narrative.filter((line) => line.kind === "in").map((line) => line.text);
  }

  function lastEnvelope() {
    return sender.sent.actions[sender.sent.actions.length - 1];
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  // Each row: activate one surface deliberately, then assert exactly the one
  // echo (or the declared silence) and a descriptor-free envelope.
  const SURFACES = [
    {
      id: "backpack row: confirmed item use",
      ids: ["inventory.use"],
      prepare() {
        openExploration();
        // The drawer row intent path (AppClient.onInventoryItemAction forwards
        // the panel's {action_id, payload}; the catalog resolves the key).
        store.dispatchAction("inventory.use", { item_key: "healing_potion" });
      },
      expected: "use healing_potion",
    },
    {
      id: "backpack row: equipment toggle (both directions echo equip)",
      ids: ["inventory.toggle_equip"],
      prepare() {
        openExploration();
        store.dispatchAction("inventory.toggle_equip", { item_key: "item_leather_armor" });
      },
      expected: "equip item_leather_armor",
    },
    {
      id: "ballot menu: numbered accept row (payload-only)",
      ids: ["title.accept"],
      prepare() {
        openExploration();
        // The title_ballot menu intent (AppClient forwards {action_id,
        // payload}; the catalog resolves the numbered choice from the
        // payload alone).
        store.dispatchAction("title.accept", { index: 2 });
      },
      expected: "title accept 2",
    },
    {
      id: "character drawer: persona field edit row (payload-only)",
      ids: ["character.persona.update"],
      prepare() {
        openExploration();
        // The drawer persona edit intent (AppClient.onPersonaEdit forwards
        // {field, text}; the echo replays the typed Telnet family line).
        store.dispatchAction("character.persona.update", {
          field: "personality",
          text: "沉穩",
        });
      },
      expected: "設定個性 沉穩",
    },
    {
      id: "ballot menu: decline row (payload-only)",
      ids: ["title.decline"],
      prepare() {
        openExploration();
        store.dispatchAction("title.decline", {});
      },
      expected: "title decline",
    },
    {
      id: "codex window: fixed equip row (payload-only)",
      ids: ["title.equip"],
      prepare() {
        openExploration();
        // The codex window intent (AppClient forwards {action_id, payload}).
        store.dispatchAction("title.equip", {
          kind: "fixed",
          identifier: "g_f_rank",
        });
      },
      expected: "title equip fixed g_f_rank",
    },
    {
      id: "codex window: confirmed epithet removal row (payload-only)",
      ids: ["title.remove"],
      prepare() {
        openExploration();
        store.dispatchAction("title.remove", { display: "夜襲之人" });
      },
      expected: "title remove epithet 夜襲之人 confirm",
    },
    {
      id: "shop drawer buy row (central fill from the services panel)",
      ids: ["shop.buy"],
      prepare() {
        openExploration();
        store.dispatchAction("shop.buy", { item_key: "item_iron_sword", quantity: 2 });
      },
      expected: "buy 鐵劍 2",
    },
    {
      id: "shop drawer sell row (central fill from the services panel)",
      ids: ["shop.sell"],
      prepare() {
        openExploration();
        store.dispatchAction("shop.sell", { item_key: "item_herb_moon", quantity: 1 });
      },
      expected: "sell 月光草 1",
    },
    {
      id: "services guild row (payload-only accept)",
      ids: ["guild.quest_accept"],
      prepare() {
        openExploration();
        store.setActiveSubDock("services");
        const model = ServiceMenu.buildMenus(SERVICES_PANEL_SAMPLE);
        store.router.pushFrame({ source: "services.board", params: {} });
        const row = model.menus.board.items.find((i) => i.actionId === "guild.quest_accept");
        expect(store.focusItemByKey(row.key)).toBe(true);
        store.focusConfirm("pointer");
      },
      expected: "guild accept quest_mill_grain",
    },
    {
      id: "services quantity form Enter submit (captured itemLabel replayed)",
      ids: ["shop.buy"],
      prepare() {
        openExploration();
        store.setActiveSubDock("services");
        const model = ServiceMenu.buildMenus(SERVICES_PANEL_SAMPLE);
        store.router.pushFrame({ source: "services.stock", params: {} });
        const row = model.menus.stock.items.find((i) => i.itemKey === "item_iron_sword");
        expect(store.focusItemByKey(row.key)).toBe(true);
        store.focusConfirm("pointer"); // opens the bounded quantity form
        expect(store.quantityForm?.open).toBe(true);
        store.focusPress("2");
        store.focusPress("Enter");
      },
      expected: "buy 鐵劍 2",
    },
    {
      id: "combat: keyboard SINGLE-target cast (forwarded row descriptor)",
      ids: ["combat.cast"],
      prepare() {
        openExploration();
        enterCombat([SKILL_ATTACK]);
        store.focusPress("Enter"); // root 攻擊 opens the target frame
        store.focusConfirm("keyboard"); // keyboard confirm submits
      },
      expected: "cast 攻擊=灰袍盜賊",
    },
    {
      id: "combat: AREA cast with the approved shorthand",
      ids: ["combat.cast"],
      prepare() {
        openExploration();
        enterCombat([SKILL_FIRE]);
        store.focusItemByKey("skills");
        store.focusConfirm("pointer"); // the skills tab pushes the category frame
        expect(store.focusItemByKey("skill-cat-0")).toBe(true);
        store.focusConfirm("pointer"); // single-group category collapses to the group frame // single-group category collapses to the group frame
        expect(store.focusItemByKey("fire_ball")).toBe(true);
        store.focusConfirm("pointer"); // opens the AREA target frame
        expect(store.focusItemByKey("shorthand-all-enemies")).toBe(true);
        store.focusConfirm("pointer"); // client-local shorthand choice
        expect(store.focusItemByKey("area-confirm")).toBe(true);
        store.focusConfirm("keyboard");
      },
      expected: "cast 火球術=all-enemies",
    },
    {
      id: "combat: AREA cast on explicitly selected targets (D3b labels)",
      ids: ["combat.cast"],
      prepare() {
        openExploration();
        enterCombat([SKILL_FIRE]);
        store.focusItemByKey("skills");
        store.focusConfirm("pointer"); // the skills tab pushes the category frame
        expect(store.focusItemByKey("skill-cat-0")).toBe(true);
        store.focusConfirm("pointer"); // single-group category collapses to the group frame
        expect(store.focusItemByKey("fire_ball")).toBe(true);
        store.focusConfirm("pointer"); // opens the AREA target frame
        expect(store.focusItemByKey("area-7")).toBe(true);
        store.focusPress(" ");
        expect(store.focusItemByKey("area-8")).toBe(true);
        store.focusPress(" ");
        expect(store.focusItemByKey("area-confirm")).toBe(true);
        store.focusConfirm("keyboard");
      },
      expected: "cast 火球術=灰袍盜賊、同行劍士",
    },
    {
      id: "combat: cast with a non-default freeform magnitude",
      ids: ["combat.cast"],
      prepare() {
        openExploration();
        enterCombat([SKILL_WIND]);
        store.focusItemByKey("skills");
        store.focusConfirm("pointer"); // the skills tab pushes the category frame
        expect(store.focusItemByKey("skill-cat-0")).toBe(true);
        store.focusConfirm("pointer"); // single-group category collapses to the group frame
        expect(store.focusItemByKey("wind_blade")).toBe(true);
        store.focusConfirm("pointer"); // master skill stops at the 威力 step
        expect(store.focusItemByKey("scale-2")).toBe(true);
        store.focusConfirm("pointer"); // chosen scale applies, targets open
        store.focusConfirm("keyboard"); // first target, keyboard submit
      },
      expected: "cast 風刃術（威力×2）=灰袍盜賊",
    },
    {
      id: "combat: cast with the DEFAULT magnitude shows no 威力 suffix",
      ids: ["combat.cast"],
      prepare() {
        openExploration();
        enterCombat([SKILL_WIND]);
        store.focusItemByKey("skills");
        store.focusConfirm("pointer"); // the skills tab pushes the category frame
        expect(store.focusItemByKey("skill-cat-0")).toBe(true);
        store.focusConfirm("pointer"); // single-group category collapses to the group frame
        expect(store.focusItemByKey("wind_blade")).toBe(true);
        store.focusConfirm("pointer"); // master skill stops at the 威力 step
        expect(store.focusItemByKey("scale-1")).toBe(true);
        store.focusConfirm("pointer");
        store.focusConfirm("keyboard");
      },
      expected: "cast 風刃術=灰袍盜賊",
    },
    {
      id: "combat: flee row (button label forwarded, form (b))",
      ids: ["combat.flee"],
      prepare() {
        openExploration();
        enterCombat([SKILL_ATTACK]);
        expect(store.focusItemByKey("flee")).toBe(true);
        store.focusConfirm("keyboard");
      },
      expected: "逃跑",
    },
    {
      id: "combat: forfeit confirmation",
      ids: ["combat.forfeit"],
      prepare() {
        openExploration();
        enterCombat([SKILL_ATTACK]);
        expect(store.focusItemByKey("forfeit")).toBe(true);
        store.focusConfirm("pointer"); // pushes the confirm frame
        expect(store.focusItemByKey("confirm-forfeit")).toBe(true);
        store.focusConfirm("keyboard");
      },
      expected: "combat forfeit",
    },
    {
      id: "minimap move: unique edge label (AppClient-derived descriptor)",
      ids: ["explore.move"],
      prepare() {
        openExploration();
        // AppClient.onMapMove derives the label via LocalMap.exitLabelFor
        // (unique-edge rule pinned by the Node gate); the store echoes it.
        store.dispatchAction(
          "explore.move",
          { exit_ref: "east", current_node: "room:42" },
          { exitLabel: "東" },
        );
      },
      expected: "東",
    },
    {
      id: "EXPECTED SILENCE: minimap move with no committed label",
      ids: ["explore.move"],
      silence: true,
      prepare() {
        openExploration();
        store.dispatchAction("explore.move", { exit_ref: "east", current_node: "room:42" });
      },
    },
    {
      id: "exploration row: scripted talk (row descriptor forwarded)",
      ids: ["explore.talk_scripted"],
      prepare() {
        openExploration();
        store.dispatchAction(
          "explore.talk_scripted",
          { npc_id: 7, keyword_id: "guild" },
          { npcLabel: "店長", keywordLabel: "公會" },
        );
      },
      expected: "talk 店長 公會",
    },
    {
      id: "free-form speech intent (central fill from the exploration panel)",
      ids: ["explore.talk_freeform"],
      prepare() {
        openExploration();
        store.dispatchAction("explore.talk_freeform", { npc_id: 7, speech: "你好" });
      },
      expected: "talk 店長 你好",
    },
    {
      id: "engage intent (central fill: monster display name)",
      ids: ["explore.engage"],
      prepare() {
        openExploration();
        store.dispatchAction("explore.engage", { monster_id: 7 });
      },
      expected: "engage 店長",
    },
    {
      id: "look intent (central fill: target display name)",
      ids: ["explore.look"],
      prepare() {
        openExploration();
        store.dispatchAction("explore.look", { target_id: 7 });
      },
      expected: "look 店長",
    },
    {
      id: "party invite intent (central fill)",
      ids: ["explore.party_invite"],
      prepare() {
        openExploration();
        store.dispatchAction("explore.party_invite", { npc_id: 7 });
      },
      expected: "invite 店長",
    },
    {
      id: "party leave intent (central fill)",
      ids: ["explore.party_leave"],
      prepare() {
        openExploration();
        store.dispatchAction("explore.party_leave", { npc_id: 7 });
      },
      expected: "leave 店長",
    },
    {
      id: "exploration row: wait a daypart",
      ids: ["explore.wait"],
      prepare() {
        openExploration();
        store.dispatchAction("explore.wait", { daypart: "dusk" });
      },
      expected: "wait until dusk",
    },
    {
      id: "guild rows: register / abandon / turnin / track / exam (payload-only)",
      ids: ["guild.register", "guild.quest_abandon", "guild.quest_turnin", "guild.quest_track", "guild.exam_start"],
      prepare() {
        openExploration();
        store.dispatchAction("guild.register", {});
        store.receive(1, "ui_action_result", [fx.actionResult()], {});
        store.receive(1, "ui_update", [fx.update({ revision: 2 })], {});
        store.dispatchAction("guild.quest_abandon", { quest_id: "q_1042" });
        store.receive(1, "ui_action_result", [fx.actionResult({ request_id: "session:2" })], {});
        store.receive(1, "ui_update", [fx.update({ revision: 3 })], {});
        store.dispatchAction("guild.quest_turnin", { quest_id: "q_1042" });
        store.receive(1, "ui_action_result", [fx.actionResult({ request_id: "session:3" })], {});
        store.receive(1, "ui_update", [fx.update({ revision: 4 })], {});
        store.dispatchAction("guild.quest_track", { quest_id: "q_1042", tracked: true });
        store.receive(1, "ui_action_result", [fx.actionResult({ request_id: "session:4" })], {});
        store.receive(1, "ui_update", [fx.update({ revision: 5 })], {});
        store.dispatchAction("guild.exam_start", { target_rank: "B" });
      },
      expected: ["guild register", "guild abandon q_1042", "guild turnin q_1042", "guild track q_1042", "guild exam B"],
    },
    {
      id: "creation preset card (payload-only preset command)",
      ids: ["creation.preset"],
      prepare() {
        openExploration();
        enterCreation();
        expect(store.focusItemByKey("presets")).toBe(true);
        store.focusConfirm("pointer"); // opens the preset card frame
        expect(store.focusItemByKey("preset-0")).toBe(true);
        store.focusConfirm("pointer");
      },
      expected: "character preset preset_wandering_blade",
    },
    {
      id: "creation activate confirmation (dock confirm item descriptor)",
      ids: ["creation.activate"],
      prepare() {
        openExploration();
        enterCreation();
        expect(store.focusItemByKey("presets")).toBe(true);
        store.focusConfirm("pointer");
        expect(store.focusItemByKey("preset-0")).toBe(true);
        store.focusConfirm("pointer"); // saves the draft (pending save)
        store.receive(1, "ui_action_result", [fx.actionResult()], {});
        // The successful save opens the confirmation frame automatically.
        expect(store.focusItemByKey("confirm-creation.activate")).toBe(true);
        store.focusConfirm("keyboard");
      },
      // Two deliberate activations, one line each: the draft save and the
      // activation confirmation both re-run the preset path.
      expected: [
        "character preset preset_wandering_blade",
        "character preset preset_wandering_blade",
      ],
    },
    {
      id: "creation reset confirmation (RESET_DISPLAY client label)",
      ids: ["creation.reset"],
      prepare() {
        openExploration();
        enterCreation();
        expect(store.requestCreationReset()).toBe(true);
        expect(store.focusItemByKey("confirm-creation.reset")).toBe(true);
        store.focusConfirm("keyboard");
      },
      expected: "清除草稿",
    },
    {
      id: "creation overlay confirm intent (central fill from committed confirm items)",
      ids: ["creation.reset"],
      prepare() {
        openExploration();
        enterCreation();
        expect(store.requestCreationReset()).toBe(true);
        // CreationOverlay.confirmCurrent emits only {action_id, payload:{}}.
        store.dispatchAction("creation.reset", {});
      },
      expected: "清除草稿",
    },
    {
      id: "creation custom and concept controls",
      ids: ["creation.custom", "creation.concept"],
      prepare() {
        openExploration();
        enterCreation();
        store.dispatchAction("creation.custom", {});
        store.receive(1, "ui_action_result", [fx.actionResult()], {});
        store.dispatchAction("creation.concept", { concept: "流浪學者" });
      },
      expected: ["character create", "character concept 流浪學者"],
    },
    {
      id: "suggestion-card cast intent (central fill: skill + target labels)",
      ids: ["combat.cast"],
      prepare() {
        openExploration();
        enterCombat([SKILL_ATTACK]);
        // OptionCard intents carry only {action_id, payload}.
        store.dispatchAction("combat.cast", { skill_key: "basic_attack", target_ids: [7] });
      },
      expected: "cast 攻擊=灰袍盜賊",
    },
    {
      id: "EXPECTED SILENCE: options.dismiss presentation control",
      ids: ["options.dismiss"],
      silence: true,
      prepare() {
        openExploration();
        store.dispatchAction("options.dismiss", {});
      },
    },
    {
      // The name roll is a UI-only convenience: no typed-command equivalent,
      // declared silent, dispatched with its exact wire payload.
      id: "EXPECTED SILENCE: creation.roll_name dice control",
      ids: ["creation.roll_name"],
      silence: true,
      prepare() {
        openExploration();
        enterCreation();
        store.dispatchAction("creation.roll_name", {
          race: "human",
          subrace: null,
          sex: "other",
        });
      },
    },
    {
      id: "blocked duplicate dispatch (in flight) adds no second line",
      ids: ["explore.wait"],
      prepare() {
        openExploration();
        store.dispatchAction("explore.wait", { daypart: "dusk" });
        expect(store.dispatchAction("explore.wait", { sleep: true })).toBe(null);
      },
      expected: "wait until dusk",
    },
  ];

  for (const surface of SURFACES) {
    it(`${surface.id}`, () => {
      surface.prepare();
      const lines = echoLines();
      if (surface.silence) {
        expect(lines).toEqual([]);
        return;
      }
      const expected = Array.isArray(surface.expected)
        ? surface.expected
        : [surface.expected];
      expect(lines).toEqual(expected);
      // Literal-text rendering: echo lines are plain `in` lines.
      for (const line of store.narrative.filter((l) => l.kind === "in")) {
        expect(line.tokens).toBe(null);
      }
    });
  }

  it("no dispatch surface leaks descriptor data into the envelope", () => {
    openExploration();
    store.dispatchAction("shop.buy", { item_key: "item_iron_sword", quantity: 2 }); // filled
    store.dispatchAction("explore.talk_scripted", { npc_id: 7, keyword_id: "k" }, { npcLabel: "店長", keywordLabel: "公會" }); // forwarded
    for (const envelope of sender.sent.actions) {
      expect(Object.keys(envelope).sort()).toEqual(ENVELOPE_KEYS);
    }
    expect(sender.sent.actions[0].payload).toEqual({ item_key: "item_iron_sword", quantity: 2 });
  });

  it("the behavioral table exercises every registered mutation id", () => {
    const exercised = new Set(SURFACES.flatMap((surface) => surface.ids));
    for (const actionId of REGISTERED_MUTATION_IDS) {
      expect(
        exercised.has(actionId),
        `${actionId} must have a behavioral table row (silent controls included)`,
      ).toBe(true);
    }
    expect(SILENT_IDS).toEqual(["creation.roll_name", "options.dismiss"]);
  });

  it("a fill never overrides an explicitly provided descriptor field", () => {
    openExploration();
    // The explicit itemLabel wins over the services panel's row name.
    store.dispatchAction(
      "shop.buy",
      { item_key: "item_iron_sword", quantity: 1 },
      { itemLabel: "鐵劍(店藏)》" },
    );
    expect(echoLines()).toEqual(["buy 鐵劍(店藏)》 1"]);
  });

  it("an EMPTY descriptor array is declared absent and may be filled", () => {
    openExploration();
    // Declared semantics: `itemLabel: []` carries no label, so the committed
    // services row name fills it (pinned so the `has()` rule cannot drift).
    store.dispatchAction(
      "shop.buy",
      { item_key: "item_iron_sword", quantity: 2 },
      { itemLabel: [] },
    );
    expect(echoLines()).toEqual(["buy 鐵劍 2"]);
  });
});
