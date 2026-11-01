// The camp card (OpenSpec change wilderness-camping; design §5): the real
// composed store behind a fake sender and the mounted AppClient. The card
// shows only the server preview, resets the dream opt-in on every opening,
// confirms exactly once, and drops stale or foreign results. Synthetic data.
import { afterEach, describe, expect, it } from "vitest";
import { liveTravel, tick, walkArea, walkCapacity, walkPanels } from "./support.js";

const CX = 60;
const CY = 80;

const wrappers = [];
afterEach(() => {
  while (wrappers.length) wrappers.pop().unmount();
  document.body.innerHTML = "";
});

const member = (id, current, predicted, wake = 900) => ({
  member_id: String(id),
  name: `成員${id}`,
  current_reserve: current * 3600,
  predicted_reserve: predicted * 3600,
  reserve_max: 360000,
  current_percent: current,
  predicted_percent: predicted,
  wake_tick: wake,
  wake_time: "第 2 日 06:00",
});

function previewData({ recoveredAvailable = true, dawnDream = true, recoveredDream = false, available = true } = {}) {
  const refusal = { code: "party_unavailable", message: "在場成員都已入睡或已完全恢復" };
  if (!available) {
    const off = (mode) => ({ mode, available: false, refusal, dream_offerable: false, wake_tick: null, wake_time: null, members: [] });
    return {
      available: false, refusal: { code: "hostile_present", message: "附近有活著的怪物，這裡不安全。" },
      dream_offerable: false, default_mode: "until-dawn", current_tick: 100, current_time: "第 1 日 20:00",
      modes: [off("until-dawn"), off("until-recovered")],
    };
  }
  return {
    available: true,
    refusal: null,
    dream_offerable: dawnDream,
    default_mode: "until-dawn",
    current_tick: 100,
    current_time: "第 1 日 20:00",
    modes: [
      { mode: "until-dawn", available: true, refusal: null, dream_offerable: dawnDream, wake_tick: 900, wake_time: "第 2 日 06:00", members: [member(42, 50, 100), member(2, 20, 100)] },
      recoveredAvailable
        ? { mode: "until-recovered", available: true, refusal: null, dream_offerable: recoveredDream, wake_tick: 700, wake_time: "第 1 日 23:00", members: [member(42, 50, 96, 100), member(2, 20, 100, 700)] }
        : { mode: "until-recovered", available: false, refusal, dream_offerable: false, wake_tick: null, wake_time: null, members: [] },
    ],
  };
}

async function harness() {
  const h = liveTravel({ wrappers, panels: walkPanels(CX, CY, { capacity: walkCapacity() }) });
  await tick();
  // The stage's own area read completes first (the single-flight gate).
  await h.answerMap(walkArea(CX, CY));
  h.publish({ status: walkPanels(CX, CY, { capacity: walkCapacity() }).status });
  await tick();
  const sent = (id) => h.sender.sent.actions.filter((a) => a.action_id === id);
  const card = () => h.w.find('[data-testid="camp-card"]');
  const key = async (k, extra = {}) => {
    await card().trigger("keydown", { key: k, ...extra });
    await tick();
  };
  const answer = async (request, data, overrides = {}) => {
    h.accept("ui_action_result", {
      protocol_version: 1,
      presentation_epoch: request.presentation_epoch,
      request_id: request.request_id,
      outcome: "success",
      code: request.action_id,
      message: "完成",
      presentation_revision: h.store.view.revision,
      data,
      ...overrides,
    });
    await tick();
  };
  const open = async (data = previewData()) => {
    expect(h.store.openTravelCamp("leg")).toBe(true);
    await tick();
    const request = sent("explore.camp_preview").at(-1);
    if (data) await answer(request, data);
    return request;
  };
  return { ...h, sent, card, key, answer, open };
}

describe("the camp card", () => {
  it("is pending until the preview arrives, then selects the server default", async () => {
    const s = await harness();
    await s.open(null);
    expect(s.card().attributes("data-phase")).toBe("previewPending");
    expect(s.card().find('[data-testid="camp-card-confirm"]').exists()).toBe(false);
    await s.answer(s.sent("explore.camp_preview").at(-1), previewData());
    expect(s.card().attributes("data-phase")).toBe("choosing");
    const tiles = s.card().findAll('[data-testid="camp-mode"]');
    expect(tiles.map((t) => t.attributes("data-mode"))).toEqual(["until-dawn", "until-recovered"]);
    expect(tiles[0].attributes("aria-checked")).toBe("true");
    // The selected mode's server rows, nothing derived.
    const rows = s.card().findAll('[data-testid="camp-card-member"]');
    expect(rows.map((r) => r.attributes("data-member"))).toEqual(["42", "2"]);
    expect(s.sent("explore.camp")).toHaveLength(0);
  });

  it("keys 1/2 pick tiles, D toggles only an offered checkbox and a switch clears it", async () => {
    const s = await harness();
    await s.open();
    await s.key("d");
    expect(s.store.view.camp.dream).toBe(true);
    await s.key("2");
    // The recovered mode cannot offer the dream: hidden and cleared.
    expect(s.store.view.camp.selected).toBe("until-recovered");
    expect(s.store.view.camp.dream).toBe(false);
    expect(s.card().find('[data-testid="camp-card-dream"]').exists()).toBe(false);
    await s.key("d");
    expect(s.store.view.camp.dream).toBe(false);
    await s.key("1");
    expect(s.store.view.camp.selected).toBe("until-dawn");
    expect(s.store.view.camp.dream).toBe(false);
  });

  it("Enter confirms exactly once with the selected mode and opt-in", async () => {
    const s = await harness();
    await s.open();
    await s.key("d");
    await s.key("Enter");
    await s.key("Enter");
    await s.key("Enter", { repeat: true });
    const camps = s.sent("explore.camp");
    expect(camps).toHaveLength(1);
    expect(camps[0].payload).toEqual({ mode: "until-dawn", dream: true });
    expect(s.card().attributes("data-phase")).toBe("submitting");
  });

  it("an unavailable selected mode shows its reason and disables confirmation", async () => {
    const s = await harness();
    await s.open(previewData({ recoveredAvailable: false }));
    await s.key("2");
    expect(s.store.view.camp.selected).toBe("until-recovered");
    expect(s.card().find('[data-testid="camp-mode-refusal"]').text()).toContain("完全恢復");
    expect(s.card().get('[data-testid="camp-card-confirm"]').attributes("disabled")).toBeDefined();
    await s.key("Enter");
    expect(s.sent("explore.camp")).toHaveLength(0);
    // The other tile stays reachable.
    await s.key("1");
    await s.key("Enter");
    expect(s.sent("explore.camp")).toHaveLength(1);
  });

  it("a refused preview shows only the reason and cancel, and Esc sends nothing", async () => {
    const s = await harness();
    await s.open(previewData({ available: false }));
    expect(s.card().attributes("data-phase")).toBe("refused");
    expect(s.card().get('[data-testid="camp-card-refusal"]').text()).toContain("怪物");
    expect(s.card().find('[data-testid="camp-mode"]').exists()).toBe(false);
    expect(s.card().find('[data-testid="camp-card-confirm"]').exists()).toBe(false);
    await s.key("Enter");
    await s.key("Escape");
    expect(s.card().exists()).toBe(false);
    expect(s.sent("explore.camp")).toHaveLength(0);
  });

  it("every reopening resets the dream opt-in unchecked", async () => {
    const s = await harness();
    await s.open();
    await s.key("d");
    expect(s.store.view.camp.dream).toBe(true);
    await s.key("Escape");
    await s.open();
    expect(s.store.view.camp.dream).toBe(false);
    expect(s.card().get('[data-testid="camp-card-dream-input"]').element.checked).toBe(false);
  });

  it("keeps Tab inside the card and consumes its keys", async () => {
    const s = await harness();
    await s.open();
    const seen = [];
    const listener = (event) => seen.push(event.key);
    document.addEventListener("keydown", listener);
    await s.key("1");
    await s.key("ArrowRight");
    await s.key("d");
    document.removeEventListener("keydown", listener);
    expect(seen).toEqual([]);
    const focusables = s.card().findAll("button, input");
    focusables.at(-1).element.focus();
    await s.card().trigger("keydown", { key: "Tab" });
    expect(s.card().element.contains(document.activeElement)).toBe(true);
  });

  it("drops a foreign or stale result and discards the card on disconnect", async () => {
    const s = await harness();
    const request = await s.open(null);
    // A result for another request id is not this preview's.
    await s.answer({ ...request, request_id: "session:999" }, previewData());
    expect(s.store.view.camp.phase).toBe("previewPending");
    await s.answer(request, previewData());
    await s.key("Enter");
    const camp = s.sent("explore.camp").at(-1);
    s.store.setConnected(false);
    await tick();
    expect(s.store.view.camp.phase).toBe("closed");
    expect(s.card().exists()).toBe(false);
    s.store.setConnected(true);
    await tick();
    expect(s.sent("explore.camp")).toHaveLength(1);
    expect(camp.payload.mode).toBe("until-dawn");
  });

  it("a settled camp becomes the beat; a dream entry hands over to the dream stage", async () => {
    const s = await harness();
    await s.open();
    await s.key("Enter");
    const camp = s.sent("explore.camp").at(-1);
    const result = {
      camp_id: "a".repeat(64), phase: "complete",
      timing: { elapsed_seconds: 800, result_tick: 900, result_time: "第 2 日 06:00", wake_tick: 900, wake_time: "第 2 日 06:00" },
      members: [{ member_id: "42", name: "成員42", reserve_before: 180000, reserve_after: 360000, reserve_max: 360000, before_percent: 50, after_percent: 100, sleeping: false, wake_tick: 900 }],
      events: [], interrupted: false, interruption_reason: null,
    };
    await s.answer(camp, result, { message: "夜裡無事。" });
    expect(s.store.view.camp.phase).toBe("beat");
    expect(s.w.find('[data-testid="campfire-card"]').exists()).toBe(true);

    s.store.continueCampTravel();
    await tick();
    await s.open();
    await s.key("d");
    await s.key("Enter");
    const dream = s.sent("explore.camp").at(-1);
    await s.answer(dream, { ...result, phase: "dream", timing: { ...result.timing, elapsed_seconds: 0, wake_tick: null, wake_time: null } });
    expect(s.store.view.camp.phase).toBe("closed");
    expect(s.w.find('[data-testid="campfire-card"]').exists()).toBe(false);
  });

  it("a refused camp returns the server reason with only cancel", async () => {
    const s = await harness();
    await s.open();
    await s.key("Enter");
    const camp = s.sent("explore.camp").at(-1);
    s.accept("ui_action_result", {
      protocol_version: 1, presentation_epoch: camp.presentation_epoch, request_id: camp.request_id,
      outcome: "rejected", code: "hostile_present", message: "附近有活著的怪物，這裡不安全。",
      presentation_revision: s.store.view.revision,
    });
    await tick();
    expect(s.store.view.camp.phase).toBe("refused");
    expect(s.card().get('[data-testid="camp-card-refusal"]').text()).toContain("怪物");
  });

  it("the forced-walking-sleep handoff prepends 全員紮營 and keeps its rows", async () => {
    const s = await harness();
    const handoff = {
      schema_version: 1, available: true, owner_id: 42, controlled_body_id: 42, transition_id: "42:f:1",
      selection: { available: true, rows: [{ kind: "possess", identity: 2, name: "同伴", reserve_percent: 100, stage: "normal", label: "接手 同伴（精力 100%）", enabled: true, reason: null }] },
      party: { label: "全員一起睡眠", enabled: false, reason: "在場成員都已入睡或已完全恢復" },
      controlled_sleep: { sleep_id: "forced:42:1", revision: 0 },
      owner_sleep: { sleep_id: "forced:42:1", revision: 0, generation: 1, dream_pending: true, continuation: "none", continuation_available: true, continuation_reason: null },
    };
    // A walk is held when the collapse publication arrives.
    expect(s.store.holdTravel("east")).toBe(true);
    s.publish({ sleep_handoff: handoff });
    await tick();
    s.store.releaseTravel();
    await tick();
    const rows = () => s.w.findAll('[data-testid="sleep-handoff-card"] [data-testid^="sleep-handoff"]').map((r) => r.attributes("data-testid"));
    expect(rows()[0]).toBe("sleep-handoff-camp");
    expect(rows().slice(1)).toEqual(["sleep-handoff-row", "sleep-handoff-party"].concat(rows().slice(3)));
    await s.w.get('[data-testid="sleep-handoff-camp"]').trigger("click");
    await tick();
    expect(s.card().exists()).toBe(true);
    expect(s.sent("explore.camp_preview")).toHaveLength(1);
    // Cancel restores the handoff it covered.
    await s.key("Escape");
    expect(s.w.find('[data-testid="sleep-handoff-card"]').exists()).toBe(true);

    // An ordinary (not walking) sleep view gets no shortcut.
    s.publish({ sleep_handoff: { ...handoff, transition_id: "42:v:2" } });
    await tick();
    expect(s.w.find('[data-testid="sleep-handoff-camp"]').exists()).toBe(false);
  });
});
