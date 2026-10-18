// skillbook-authoritative-casting D6/D7: the SkillBook → dock hand-over in the
// composed store. The book's 施放 sends only the read-only preview; the dock
// takes the single router once the matching preview revision commits; local
// AREA selection, the scale re-preview, the opening confirmation, Escape back
// to the book, the combat hand-off, a refused preview, and lifecycle retirement
// all run through the one store and the one keyboard router.
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";

const KEY = "t_soft_mend";

function skillUsePanel(spec, overrides = {}) {
  const panel = {
    schema_version: 2,
    available: true,
    kind: "skill_use",
    actor_id: 42,
    scale: 1,
    skill: {
      key: KEY,
      label: "合成癒合",
      description: "合成用的治療技能。",
      target_spec: spec,
      usable_out_of_combat: true,
      cost: { mp: 11 },
      enabled: true,
      disabled_reason: null,
      targets: [],
      openings: [],
    },
  };
  if (spec === "self") {
    panel.skill.targets = [{ identity: 42, label: "影行者（自己）", enabled: true, disabled_reason: null }];
  }
  if (spec === "single" || spec === "area") {
    panel.skill.targets = [
      { identity: 42, label: "影行者（自己）", enabled: true, disabled_reason: null },
      { identity: 51, label: "村民（1）", enabled: true, disabled_reason: null },
      { identity: 52, label: "村民（2）", enabled: true, disabled_reason: null },
    ];
    panel.skill.openings = [
      { identity: 9, label: "合成狼（開戰）", target_ids: [9], enabled: true, disabled_reason: null },
    ];
  }
  Object.assign(panel, overrides.panel || {});
  Object.assign(panel.skill, overrides.skill || {});
  return panel;
}

describe("SkillBook use hand-over", () => {
  let store;
  let sender;
  let revision;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    revision = 1;
  });

  // The book's caster is the committed character panel's viewed member.
  function characterPanel(memberId = 42) {
    return {
      schema_version: 8,
      available: true,
      kind: "character",
      member_id: memberId,
      traits: [],
      conditions: [],
      actives: [],
      passives: [],
      equipment: [],
      disguise: { active: false, description: "", displayed: [] },
      guild: { rank: null, merit: 0 },
      wallet: 0,
    };
  }

  function openExploration(
    mode = "exploration",
    contextActions = fx.explorationActions(),
    status = undefined,
    character = characterPanel(),
  ) {
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(1, "ui_snapshot", [
      fx.snapshot({
        mode,
        panels: {
          status: fx.statusPanel(status),
          character,
          exploration: fx.explorationPanel(),
          context_actions: contextActions,
          local_map: fx.localMapPanel(),
        },
      }),
    ], {});
  }

  function lastAction() {
    return sender.sent.actions[sender.sent.actions.length - 1];
  }

  function resolve(panels, result = {}) {
    const envelope = lastAction();
    revision += 1;
    store.receive(1, "ui_update", [fx.update({ revision, panels })], {});
    store.receive(1, "ui_action_result", [
      fx.actionResult({ request_id: envelope.request_id, presentation_revision: revision, ...result }),
    ], {});
  }

  function beginPreview(spec, overrides, status) {
    openExploration("exploration", fx.explorationActions(), status);
    store.openHudDrawer("skill");
    const outcome = store.beginSkillUse(KEY);
    expect(outcome.route).toBe("preview");
    expect(lastAction().action_id).toBe("explore.skill_preview");
    expect(lastAction().payload).toEqual({ actor_id: 42, skill_key: KEY });
    resolve({ skill_use: skillUsePanel(spec, overrides) });
  }

  const source = () => store.router.currentDescriptor().source;
  const items = () => store.view.combatMenu.items;

  it("hands casting to the dock only after the matching preview commits", () => {
    openExploration();
    store.openHudDrawer("skill");
    store.beginSkillUse(KEY);
    // Pending: the book is still open, nothing but the preview was sent.
    expect(store.view.hudDrawer).toBe("skill");
    expect(store.view.skillUsePendingKey).toBe(KEY);
    expect(sender.sent.actions.map((a) => a.action_id)).toEqual(["explore.skill_preview"]);
    const focusBefore = store.view.dockFocusRequest;
    resolve({ skill_use: skillUsePanel("single") });
    expect(store.view.hudDrawer).toBe(null);
    expect(source()).toBe("skilluse.root");
    expect(store.view.dockFocusRequest).toBe(focusBefore + 1);
    expect(store.view.skillUse.label).toBe("合成癒合");
    expect(items().map((item) => item.key)).toEqual(["target-42", "target-51", "target-52", "opening-9"]);
    // Still no cast: opening the flow sends nothing.
    expect(sender.sent.actions.map((a) => a.action_id)).toEqual(["explore.skill_preview"]);
  });

  it("confirms an ordinary SINGLE target with exactly one explore.cast", () => {
    beginPreview("single");
    store.focusItemByKey("target-52");
    store.focusConfirm("keyboard");
    expect(lastAction().action_id).toBe("explore.cast");
    expect(lastAction().payload).toEqual({
      actor_id: 42,
      skill_key: KEY,
      target_ids: [52],
    });
  });

  it("requires an explicit confirmation for NONE and carries no target field", () => {
    beginPreview("none");
    expect(items()[0].key).toBe("cast-none");
    store.focusConfirm("keyboard");
    expect(lastAction().payload).toEqual({ actor_id: 42, skill_key: KEY });
  });

  it("toggles ordinary AREA candidates with Space and submits presenter order", () => {
    beginPreview("area");
    store.focusItemByKey("area-52");
    store.focusPress(" ");
    store.focusItemByKey("area-42");
    store.focusPress(" ");
    const confirm = items().find((item) => item.key === "area-confirm");
    expect(confirm.label).toBe("確認施展（已選 2）");
    store.focusItemByKey("area-confirm");
    store.focusConfirm("keyboard");
    expect(lastAction().payload).toEqual({
      actor_id: 42,
      skill_key: KEY,
      target_ids: [42, 52],
    });
  });

  it("confirms a monster opening through its own frame with the anchor only", () => {
    beginPreview("area", {
      skill: {
        openings: [
          { identity: 9, label: "合成狼等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null },
          { identity: 12, label: "灰狼等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null },
        ],
      },
    });
    store.focusItemByKey("opening-12");
    store.focusConfirm("keyboard");
    expect(source()).toBe("skilluse.opening");
    const sentBefore = sender.sent.actions.length;
    expect(items().map((item) => item.key)).toEqual(["confirm-opening", "cancel-opening"]);
    // 返回 pops back without casting.
    store.focusItemByKey("cancel-opening");
    store.focusConfirm("keyboard");
    expect(source()).toBe("skilluse.root");
    expect(sender.sent.actions.length).toBe(sentBefore);
    store.focusItemByKey("opening-12");
    store.focusConfirm("keyboard");
    store.focusItemByKey("confirm-opening");
    store.focusConfirm("keyboard");
    expect(lastAction().payload).toEqual({
      actor_id: 42,
      skill_key: KEY,
      opening_target_id: 12,
    });
  });

  it("re-previews a chosen scale and casts at the committed scale", () => {
    const rungs = [
      { scale: 0.25, label: "1/4", mp_cost: 3 },
      { scale: 0.5, label: "1/2", mp_cost: 6 },
      { scale: 1, label: "1", mp_cost: 11 },
    ];
    beginPreview("none", { skill: { freeform_scales: rungs } });
    expect(items()[0].key).toBe("scale-open");
    store.focusItemByKey("scale-open");
    store.focusConfirm("keyboard");
    expect(source()).toBe("skilluse.scale");
    store.focusItemByKey("scale-1/2");
    store.focusConfirm("keyboard");
    expect(lastAction().action_id).toBe("explore.skill_preview");
    expect(lastAction().payload).toEqual({
      actor_id: 42,
      skill_key: KEY,
      scale: 0.5,
    });
    expect(source()).toBe("skilluse.root");
    // The pending preview locks confirmation: Enter sends nothing new.
    const pending = sender.sent.actions.length;
    store.focusItemByKey("cast-none");
    store.focusConfirm("keyboard");
    expect(sender.sent.actions.length).toBe(pending);
    resolve({ skill_use: skillUsePanel("none", { panel: { scale: 0.5 }, skill: { freeform_scales: rungs, cost: { mp: 6 } } }) });
    store.focusItemByKey("cast-none");
    store.focusConfirm("keyboard");
    expect(lastAction().payload).toEqual({
      actor_id: 42,
      skill_key: KEY,
      scale: 0.5,
    });
  });

  it("Escape from the flow root returns to the book focused on the skill", () => {
    beginPreview("single");
    store.focusEscape();
    expect(store.view.hudDrawer).toBe("skill");
    expect(store.view.bookReturn.skillKey).toBe(KEY);
    expect(source()).toBe("exploration.root");
    expect(sender.sent.actions.map((a) => a.action_id)).toEqual(["explore.skill_preview"]);
  });

  it("a committed cast retires the flow without reopening the book", () => {
    beginPreview("none");
    store.focusConfirm("keyboard");
    resolve({ skill_use: { schema_version: 2, available: false, reason: { code: "skill_use_unavailable", message: "技能施放預覽目前無法顯示" } } });
    expect(source()).toBe("exploration.root");
    expect(store.view.hudDrawer).toBe(null);
    expect(store.view.skillUsePhase).toBe(null);
  });

  it("a refused preview keeps the book open with the server message", () => {
    openExploration();
    store.openHudDrawer("skill");
    store.beginSkillUse(KEY);
    resolve({}, { outcome: "rejected", code: "unknown_skill", message: "你沒有可施放的這項技能。" });
    expect(store.view.hudDrawer).toBe("skill");
    expect(store.view.skillUseNotice).toEqual({ skillKey: KEY, message: "你沒有可施放的這項技能。" });
    expect(source()).toBe("exploration.root");
  });

  it("closing the book while the preview is pending never takes over the dock", () => {
    openExploration();
    store.openHudDrawer("skill");
    store.beginSkillUse(KEY);
    store.closeHudDrawer();
    resolve({ skill_use: skillUsePanel("single") });
    expect(source()).toBe("exploration.root");
    expect(store.view.skillUsePhase).toBe(null);
  });

  it("in combat the book hands focus to the combat Skills entry without sending anything", () => {
    openExploration("combat", fx.combatActions());
    store.openHudDrawer("skill");
    const outcome = store.beginSkillUse(KEY);
    expect(outcome.route).toBe("combat");
    expect(store.view.hudDrawer).toBe(null);
    expect(store.router.currentItem().key).toBe("skills");
    expect(sender.sent.actions).toEqual([]);
  });

  it("a newer panel drops a vanished AREA selection", () => {
    beginPreview("area");
    store.focusItemByKey("area-51");
    store.focusPress(" ");
    const replaced = skillUsePanel("area");
    replaced.skill.targets = replaced.skill.targets.filter((row) => row.identity !== 51);
    revision += 1;
    store.receive(1, "ui_update", [fx.update({ revision, panels: { skill_use: replaced } })], {});
    const confirm = items().find((item) => item.key === "area-confirm");
    expect(confirm.enabled).toBe(false);
  });

  it("a new epoch retires a pending flow without resubmitting", () => {
    openExploration();
    store.openHudDrawer("skill");
    store.beginSkillUse(KEY);
    store.beginTransport(2);
    store.setConnected(true);
    store.receive(2, "ui_snapshot", [
      fx.snapshot({ presentation_epoch: fx.EPOCH_B, panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), context_actions: fx.explorationActions() } }),
    ], {});
    expect(store.view.skillUsePhase).toBe(null);
    expect(sender.sent.actions.filter((a) => a.action_id === "explore.cast")).toEqual([]);
  });

  it("refuses locally when the character panel publishes no member", () => {
    store.beginTransport(1);
    store.setConnected(true);
    const snap = fx.snapshot({
      mode: "exploration",
      panels: {
        exploration: fx.explorationPanel(),
        context_actions: fx.explorationActions(),
        local_map: fx.localMapPanel(),
      },
    });
    delete snap.panels.character;
    store.receive(1, "ui_snapshot", [snap], {});
    store.openHudDrawer("skill");
    const outcome = store.beginSkillUse(KEY);
    expect(outcome.route).toBe("refused");
    expect(sender.sent.actions).toEqual([]);
  });

  it("a preview naming another caster never enters the dock", () => {
    openExploration();
    store.openHudDrawer("skill");
    store.beginSkillUse(KEY);
    resolve({ skill_use: skillUsePanel("single", { panel: { actor_id: 77 } }) });
    expect(source()).toBe("exploration.root");
    expect(store.view.skillUsePhase).toBe(null);
    expect(sender.sent.actions.map((a) => a.action_id)).toEqual(["explore.skill_preview"]);
  });

  it("binds the opening confirmation to the previewed companion", () => {
    openExploration(
      "exploration",
      fx.explorationActions(),
      { actor: { identity: "42" } },
      characterPanel(77),
    );
    store.openHudDrawer("skill");
    store.beginSkillUse(KEY);
    expect(lastAction().payload).toEqual({ actor_id: 77, skill_key: KEY });
    resolve({ skill_use: skillUsePanel("single", { panel: { actor_id: 77 } }) });
    expect(source()).toBe("skilluse.root");
    store.focusItemByKey("opening-9");
    store.focusConfirm("keyboard");
    expect(source()).toBe("skilluse.opening");
    // Opening the confirmation sends nothing; cancelling still sends nothing.
    expect(sender.sent.actions.filter((a) => a.action_id === "explore.cast")).toEqual([]);
    store.focusItemByKey("cancel-opening");
    store.focusConfirm("keyboard");
    expect(source()).toBe("skilluse.root");
    expect(sender.sent.actions.filter((a) => a.action_id === "explore.cast")).toEqual([]);
    // Confirming sends exactly one cast naming that caster and the anchor.
    store.focusItemByKey("opening-9");
    store.focusConfirm("keyboard");
    store.focusItemByKey("confirm-opening");
    store.focusConfirm("keyboard");
    const casts = sender.sent.actions.filter((a) => a.action_id === "explore.cast");
    expect(casts).toHaveLength(1);
    expect(casts[0].payload).toEqual({
      actor_id: 77,
      skill_key: KEY,
      opening_target_id: 9,
    });
  });

  it("names the character member, not the controlled figure, as the caster", () => {
    // A conflicting status identity (the controlled figure) never selects the
    // caster: the book lists the viewed member's skills, so the preview and
    // every later booking name that member.
    openExploration(
      "exploration",
      fx.explorationActions(),
      { actor: { identity: "77" } },
      characterPanel(42),
    );
    store.openHudDrawer("skill");
    const outcome = store.beginSkillUse(KEY);
    expect(outcome.route).toBe("preview");
    expect(lastAction().payload).toEqual({ actor_id: 42, skill_key: KEY });
  });

  it("a replacement preview for another caster retires the open confirmation", () => {
    beginPreview("single");
    store.focusItemByKey("opening-9");
    store.focusConfirm("keyboard");
    expect(source()).toBe("skilluse.opening");
    const replacement = skillUsePanel("single", { panel: { actor_id: 77 } });
    revision += 1;
    store.receive(1, "ui_update", [
      fx.update({ revision, panels: { skill_use: replacement } }),
    ], {});
    expect(store.view.skillUsePhase).toBe(null);
    expect(source()).toBe("exploration.root");
    expect(sender.sent.actions.filter((a) => a.action_id === "explore.cast")).toEqual([]);
  });
});
