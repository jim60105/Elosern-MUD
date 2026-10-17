// webclient-party-items-tactics: the store side of the commanded actor's own
// item use and basic actions — companion-only stock, the committed disabled
// reason, the SELF/SINGLE item command shapes inside the guarded envelope, the
// actor-bound cross-side warning for a hostile item on an ally, the 防禦 /
// 閃避 / 挑釁 declarations, the in-combat bag routing that can never dispatch
// the actorless `inventory.use`, and the revalidation that pops a stale item
// frame (or drops the held warning) after a committed panel change.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("../../lib/motion_tokens.js", () => ({ readMotionMs: vi.fn(() => 400) }));

import { useElosernStore } from "../../stores/elosern.js";
import { useIntentHandlers } from "../../composables/intents.js";
import * as fx from "./protocol_fixtures.js";

const PLAYER = 42;
const ALLY = 8;
const FOE = 11;

function participant(identity, token, name, team) {
  return {
    identity,
    token,
    display_name: name,
    team,
    state: "active",
    hp_current: 50,
    hp_maximum: 60,
    portrait_ref: String(identity),
    conditions: [],
  };
}

const ROSTER = [
  participant(PLAYER, "a1", "影行者", "party"),
  participant(ALLY, "a2", "同行劍士", "party"),
  participant(FOE, "e1", "灰袍盜賊", "foes"),
];

function item(overrides = {}) {
  return {
    item_key: "t_tonic",
    label: "合成藥水",
    summary: "恢復少量體力。",
    quantity: 2,
    enabled: true,
    reason: null,
    target_spec: "self",
    targets: [],
    hostile: false,
    beneficial: true,
    ...overrides,
  };
}

function tactic(overrides = {}) {
  return { key: "defend", label: "防禦", enabled: true, reason: null, targets: [], ...overrides };
}

describe("party items and tactics (store)", () => {
  let store;
  let sender;
  let gen = 0;
  let revision = 1;

  beforeEach(() => {
    window.localStorage.clear();
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    gen = 0;
    revision = 1;
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // One committed v7 combat panel for the requested actor: its own local item
  // stock and basic-action capability.
  function panel({ actorId = PLAYER, draftVersion = 0, items = [], tactics = [], needs = [PLAYER, ALLY] } = {}) {
    return fx.combatActions({
      participants: ROSTER,
      actors: [
        { identity: PLAYER, commandable: true, reason: null },
        { identity: ALLY, commandable: true, reason: null },
      ],
      choices: { actor_id: actorId, skills: [], items, tactics },
      draft: {
        round_revision: 0,
        draft_version: draftVersion,
        required_actor_ids: [PLAYER, ALLY],
        entries: [],
        needs_selection_ids: needs,
        reselection_reasons: [],
      },
      session: { session_id: "s-1", mode: "hostile", round: 1, round_revision: 0, state: "ready", reason: null },
    });
  }

  function enterCombat(options = {}) {
    if (gen > 0) {
      setActivePinia(createPinia());
      store = useElosernStore();
      sender = fx.createFakeSender();
      store.setSender(sender);
      revision = 1;
    }
    gen += 1;
    store.beginTransport(gen);
    store.setConnected(true);
    store.setLoggedIn(true);
    const result = store.receive(
      gen,
      "ui_snapshot",
      [fx.snapshot({ mode: "combat", revision, panels: { status: fx.statusPanel(), context_actions: panel(options) } })],
      {},
    );
    expect(result.accepted, JSON.stringify(result)).toBe(true);
  }

  function commit(options, { mode = "combat" } = {}) {
    revision += 1;
    const body =
      mode === "combat"
        ? { context_actions: panel(options) }
        : { context_actions: fx.explorationActions() };
    const result = store.receive(gen, "ui_update", [fx.update({ revision, mode, panels: body })], {});
    expect(result.accepted, JSON.stringify(result)).toBe(true);
    return revision;
  }

  function sent(actionId) {
    return sender.sent.actions.filter((action) => action.action_id === actionId);
  }

  function rootRow(key) {
    return store.view.combatMenu.items.find((row) => row.key === key);
  }

  function openRoot(key) {
    store.focusItemByKey(key);
    return store.focusPress("Enter");
  }

  function openItems() {
    expect(openRoot("items")).toBe(true);
    expect(store.router.currentDescriptor().source).toBe("combat.items");
  }

  function openItemRow(key) {
    store.focusItemByKey(`item-${key}`);
    expect(store.focusPress("Enter")).toBe(true);
    expect(store.router.currentDescriptor()).toEqual({
      source: "combat.item",
      params: { itemKey: key },
    });
  }

  it("feeds 道具 from the commanded actor's own stock, never the commander's", () => {
    enterCombat({ items: [] });
    expect(rootRow("items").enabled).toBe(false);
    expect(rootRow("items").disabledReason.code).toBe("no_usable_item");

    // The companion's own canonical choices commit: 道具 opens that stock only.
    commit({ actorId: ALLY, items: [item({ item_key: "t_ember_spray", label: "餘燼噴霧" })] });
    expect(rootRow("items").enabled).toBe(true);
    openItems();
    expect(store.view.combatMenu.items.map((row) => row.key)).toEqual(["item-t_ember_spray"]);
    expect(store.view.combatMenu.items[0].label).toBe("餘燼噴霧 ×2");
  });

  it("a no-effect item carries its committed reason and never submits", () => {
    enterCombat({
      items: [item({ enabled: false, reason: { code: "hp_full", message: "體力已滿。" } })],
    });
    openItems();
    const row = store.view.combatMenu.items[0];
    expect(row.key).toBe("item-t_tonic");
    expect(row.enabled).toBe(false);
    expect(row.description).toBe("恢復少量體力。");
    // The disabled row stays focusable for its explanation and sends nothing.
    store.focusItemByKey("item-t_tonic");
    expect(store.focusPress("Enter")).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.resolveFrame({ source: "combat.item", params: { itemKey: "t_tonic" } }).items[0].disabledReason).toEqual({
      code: "hp_full",
      message: "體力已滿。",
    });
  });

  it("a SELF item submits one guarded item command with no target field", () => {
    enterCombat({ items: [item()] });
    openItems();
    openItemRow("t_tonic");
    store.focusItemByKey("self-confirm");
    expect(store.focusPress("Enter")).toBe(true);

    expect(sender.sent.actions).toHaveLength(1);
    const command = sender.sent.actions[0];
    expect(command.action_id).toBe("combat.command");
    expect(command.payload).toEqual({
      session_id: "s-1",
      round_revision: 0,
      draft_version: 0,
      actor_id: PLAYER,
      command: { kind: "item", payload: { item_key: "t_tonic" } },
    });
    // No actorless inventory.use, no optimistic consumption: the committed
    // stock is untouched until the round resolves.
    expect(sent("inventory.use")).toHaveLength(0);
    expect(store.resolveFrame({ source: "combat.items", params: {} }).items[0].label).toBe("合成藥水 ×2");
  });

  it("a SINGLE item reuses the stage step and submits one scalar target_id", () => {
    enterCombat({
      items: [item({ item_key: "t_bomb", label: "合成炸彈", target_spec: "single", targets: [FOE], beneficial: false })],
    });
    openItems();
    openItemRow("t_bomb");
    expect(store.view.stageTarget.positions.map((p) => p.key)).toEqual([`target-${FOE}`]);
    expect(store.stageTargetPointer(`target-${FOE}`, "activate")).toBe(true);

    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].payload.command).toEqual({
      kind: "item",
      payload: { item_key: "t_bomb", target_id: FOE },
    });
    expect(sent("inventory.use")).toHaveLength(0);
  });

  it("a hostile item on an ally asks once, and 否 sends nothing while 是 sends the held command", () => {
    enterCombat({
      items: [item({ item_key: "t_bomb", label: "合成炸彈", target_spec: "single", targets: [ALLY], hostile: true, beneficial: false })],
    });
    openItems();
    openItemRow("t_bomb");
    expect(store.focusPress("Enter")).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.view.crossSideConfirm).toMatchObject({ kind: "item", key: "t_bomb", sides: "ally" });
    expect(store.view.crossSideConfirm.question).toBe("確定要對友方使用〈合成炸彈〉？");
    // The step stays exactly as it was.
    expect(store.view.stageTarget.focusKey).toBe(`target-${ALLY}`);

    // 否 / Escape: back to the step, nothing sent.
    expect(store.cancelCrossSide()).toBe(true);
    expect(store.view.crossSideConfirm).toBeNull();
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.focusPress("Enter")).toBe(true);
    // 是 sends exactly one envelope, bound to the item the question named.
    expect(store.confirmCrossSide()).toBeTruthy();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].payload.command).toEqual({
      kind: "item",
      payload: { item_key: "t_bomb", target_id: ALLY },
    });
  });

  it("a beneficial item on an enemy asks with the enemy wording", () => {
    enterCombat({
      items: [item({ item_key: "t_salve", label: "合成藥膏", target_spec: "single", targets: [FOE], beneficial: true })],
    });
    openItems();
    openItemRow("t_salve");
    expect(store.focusPress("Enter")).toBe(true);
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.view.crossSideConfirm.question).toBe("確定要對敵方使用〈合成藥膏〉？");
  });

  it("Defend and Dodge confirm their round choice as one inert tactic command", () => {
    enterCombat({
      tactics: [tactic(), tactic({ key: "dodge", label: "閃避" })],
    });
    expect(rootRow("defend").enabled).toBe(true);
    expect(rootRow("dodge").enabled).toBe(true);

    expect(openRoot("defend")).toBe(true);
    expect(store.router.currentDescriptor()).toEqual({ source: "combat.tactic", params: { key: "defend" } });
    store.focusItemByKey("tactic-confirm");
    expect(store.focusPress("Enter")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    // The wire kind is `tactic` (the panel echoes it back as its own
    // `tactical` draft spelling); nothing was charged or applied here.
    expect(sender.sent.actions[0].payload.command).toEqual({ kind: "tactic", payload: { key: "defend" } });
    expect(sent("combat.command")).toHaveLength(1);
  });

  it("Taunt reuses the stage single-enemy step and submits that enemy", () => {
    enterCombat({ tactics: [tactic({ key: "taunt", label: "挑釁", targets: [FOE] })] });
    expect(openRoot("taunt")).toBe(true);
    expect(store.view.stageTarget.positions.map((p) => p.key)).toEqual([`target-${FOE}`]);
    expect(store.stageTargetPointer(`target-${FOE}`, "activate")).toBe(true);
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].payload.command).toEqual({
      kind: "tactic",
      payload: { key: "taunt", target_id: FOE },
    });
  });

  it("an unavailable basic action shows its committed reason and sends nothing", () => {
    enterCombat({
      tactics: [tactic({ key: "dodge", enabled: false, reason: { code: "dodge_disabled", message: "無法閃避。" } })],
    });
    expect(rootRow("dodge").enabled).toBe(false);
    expect(rootRow("dodge").disabledReason).toEqual({ code: "dodge_disabled", message: "無法閃避。" });
    expect(rootRow("defend").enabled).toBe(false);
    expect(rootRow("defend").disabledReason.code).toBe("unavailable");
    store.focusItemByKey("dodge");
    expect(store.focusPress("Enter")).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("the in-combat bag routes a use into the actor flow and never dispatches inventory.use", () => {
    enterCombat({
      items: [item({ item_key: "t_bomb", label: "合成炸彈", target_spec: "single", targets: [FOE], beneficial: false })],
    });
    const handlers = useIntentHandlers(store, (actionId, payload) => store.dispatchAction(actionId, payload));
    store.openHudDrawer("inventory");
    expect(store.view.hudDrawer).toBe("inventory");

    handlers.onInventoryItemAction({ action_id: "inventory.use", payload: { item_key: "t_bomb" } });
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.view.hudDrawer).toBeNull();
    expect(store.router.currentDescriptor()).toEqual({
      source: "combat.item",
      params: { itemKey: "t_bomb" },
    });
    // The same target/review/confirm flow the 道具 row opens.
    expect(store.view.stageTarget.positions.map((p) => p.key)).toEqual([`target-${FOE}`]);
    expect(store.stageTargetPointer(`target-${FOE}`, "activate")).toBe(true);
    expect(sent("inventory.use")).toHaveLength(0);
    expect(sent("combat.command")).toHaveLength(1);

    // The single-writer lock releases on the result; inspection and the
    // commander's own equipment toggle then stay free and unchanged.
    store.receive(
      gen,
      "ui_action_result",
      [
        fx.actionResult({
          request_id: sent("combat.command")[0].request_id,
          code: "already_committed",
          presentation_revision: revision,
        }),
      ],
      {},
    );
    store.openHudDrawer("inventory");
    handlers.onInventoryItemAction({
      action_id: "inventory.toggle_equip",
      payload: { item_key: "plain_sword" },
    });
    expect(sent("inventory.toggle_equip")).toHaveLength(1);
    expect(sent("inventory.toggle_equip")[0].payload).toEqual({ item_key: "plain_sword" });
  });

  it("useCombatItem refuses an item outside the committed stock and pushes nothing", () => {
    enterCombat({ items: [item()] });
    expect(store.useCombatItem("t_absent")).toBe(false);
    expect(store.router.currentDescriptor().source).toBe("combat.root");
    expect(sender.sent.actions).toHaveLength(0);
    expect(store.useCombatItem("t_tonic")).toBe(true);
    expect(store.router.currentDescriptor().params).toEqual({ itemKey: "t_tonic" });
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a committed equipment change that drops the item pops its frame", () => {
    enterCombat({ items: [item()] });
    openItems();
    openItemRow("t_tonic");
    expect(store.router.currentDescriptor().source).toBe("combat.item");

    // The revalidated choices no longer carry the item: the frame degrades to
    // the shared marker and pops one level, exactly like a lost skill key.
    commit({ items: [] });
    expect(store.router.currentDescriptor().source).toBe("combat.items");
    expect(store.view.combatMenu.items).toEqual([]);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("a committed equipment change drops the held item warning unsent", () => {
    enterCombat({
      items: [item({ item_key: "t_bomb", label: "合成炸彈", target_spec: "single", targets: [ALLY], hostile: true, beneficial: false })],
    });
    openItems();
    openItemRow("t_bomb");
    store.focusItemByKey(`target-${ALLY}`);
    expect(store.focusPress("Enter")).toBe(true);
    expect(store.view.crossSideConfirm).not.toBeNull();

    // The item's availability changes under the held question: it closes
    // without sending anything.
    commit({ items: [item({ item_key: "t_bomb", label: "合成炸彈", target_spec: "single", targets: [ALLY], hostile: true, beneficial: false, enabled: false, reason: { code: "hp_full", message: "體力已滿。" } })] });
    expect(store.view.crossSideConfirm).toBeNull();
    expect(sender.sent.actions).toHaveLength(0);
  });

});
