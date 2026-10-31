// The travel band log (wilderness-travel-log-ui, task 3.1): the real composed
// store behind a fake sender and the mounted AppClient. Every travel_log body
// passes the real wire validator; entries are synthetic.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import TravelLog from "../../components/travel/TravelLog.vue";
import { MAX_TRAVEL_LOG_ENTRIES } from "../../stores/elosern/travel_log.js";
import { travelEntry, travelLogPanel } from "../../stories/fixtures/travel_log.js";
import { TOWN_SUBJECT, WILD_SUBJECT, fx, liveTravel, panelsAt, tick, walkArea, walkPanels } from "./support.js";

const wrappers = [];
afterEach(() => {
  while (wrappers.length) wrappers.pop().unmount();
  document.body.innerHTML = "";
  vi.useRealTimers();
});

const dusk = (id, extra = {}) => travelEntry("dusk", {}, { id, text: `暮色降臨 ${id}。`, ...extra });
const ID = (n) => `${"a".repeat(32)}:tok${String(n).padStart(5, "0")}.0`;

function sysLines(store) {
  return store.narrative.filter((line) => line.kind === "sys").map((line) => line.text);
}

describe("travel_log adoption", () => {
  it("appends each notice once and a replayed batch adds no entry or full-log line", () => {
    const h = liveTravel({ mounted: false });
    h.publish({ travel_log: travelLogPanel([dusk(ID(1)), dusk(ID(2))]) });
    expect(h.store.view.travel.entries.map((e) => e.id)).toEqual([ID(1), ID(2)]);
    expect(sysLines(h.store)).toEqual([`暮色降臨 ${ID(1)}。`, `暮色降臨 ${ID(2)}。`]);
    // The coordinator's replay: the same batch on a later snapshot.
    h.accept("ui_snapshot", fx.snapshot({ revision: h.next(), panels: panelsAt(WILD_SUBJECT, { travel_log: travelLogPanel([dusk(ID(2))]) }) }));
    h.publish({ status: fx.statusPanel() });
    expect(h.store.view.travel.entries.map((e) => e.id)).toEqual([ID(1), ID(2)]);
    expect(sysLines(h.store)).toHaveLength(2);
  });

  it("keeps chronological order across batches and bounds the retained history", () => {
    const h = liveTravel({ mounted: false });
    let n = 0;
    for (let batch = 0; batch < 3; batch += 1) {
      const entries = [];
      for (let i = 0; i < 50; i += 1) entries.push(dusk(ID((n += 1))));
      h.publish({ travel_log: travelLogPanel(entries) });
    }
    const ids = h.store.view.travel.entries.map((e) => e.id);
    expect(ids).toHaveLength(MAX_TRAVEL_LOG_ENTRIES);
    expect(ids[0]).toBe(ID(150 - MAX_TRAVEL_LOG_ENTRIES + 1));
    expect(ids.at(-1)).toBe(ID(150));
    expect(sysLines(h.store)).toHaveLength(150);
  });

  it("never adopts a malformed batch", () => {
    const h = liveTravel({ mounted: false });
    const bad = travelLogPanel([{ ...dusk(ID(1)), text: "   " }]);
    const outcome = h.store.receive(h.store.view.generation, "ui_update", [fx.update({ revision: h.next(), panels: { travel_log: bad } })], {});
    expect(outcome.accepted).toBe(false);
    expect(h.store.view.travel.entries).toEqual([]);
    expect(sysLines(h.store)).toEqual([]);
  });

  it("retires the history with the epoch and never re-appends a replayed notice", () => {
    const h = liveTravel({ mounted: false });
    h.publish({ travel_log: travelLogPanel([dusk(ID(1))]) });
    h.store.beginTransport(2);
    h.store.setConnected(true);
    h.accept("ui_snapshot", fx.snapshot({ presentation_epoch: fx.EPOCH_B, revision: 1, panels: panelsAt(WILD_SUBJECT) }));
    expect(h.store.view.travel.entries).toEqual([]);
    h.publish({ travel_log: travelLogPanel([dusk(ID(1)), dusk(ID(2))]) }, { presentation_epoch: fx.EPOCH_B });
    expect(h.store.view.travel.entries.map((e) => e.id)).toEqual([ID(1), ID(2)]);
    expect(sysLines(h.store)).toEqual([`暮色降臨 ${ID(1)}。`, `暮色降臨 ${ID(2)}。`]);
  });
});

describe("the TravelLog component", () => {
  it("groups by day under headings with a time, glyph and spoken kind per line", () => {
    const entries = [
      travelEntry("region_entered", { name: "甲原" }, { day: 3, time: "06:00", text: "進入甲原。" }),
      travelEntry("hostile_sighted", { name: "狼", count: 2, threat: null }, { day: 3, time: "09:10", text: "發現狼 ×2。" }),
      travelEntry("nightfall", {}, { day: 4, time: "19:30", text: "入夜了。" }),
    ];
    const w = mount(TravelLog, { props: { entries } });
    wrappers.push(w);
    expect(w.findAll("h3").map((n) => n.text())).toEqual(["第 3 日", "第 4 日"]);
    const lines = w.findAll('[data-testid="travel-log__entry"]');
    expect(lines.map((l) => l.find("time").text())).toEqual(["06:00", "09:10", "19:30"]);
    expect(lines.map((l) => l.find(".travel-log__glyph").text())).toEqual(["·", "▲", "☾"]);
    expect(lines[1].find(".visually-hidden").text()).toBe("敵蹤：");
    expect(lines[2].classes()).toContain("is-newest");
    const region = w.get('[role="log"]');
    expect(region.attributes("aria-live")).toBe("polite");
  });

  it("keeps a look to one line and opens its prose without executing markup", async () => {
    const prose = "第一行。\n<img src=x onerror=alert(1)>第二行";
    const entries = [travelEntry("look", { prose }, { text: "環顧四周：第一行。" })];
    const w = mount(TravelLog, { props: { entries } });
    wrappers.push(w);
    expect(w.findAll('[data-testid="travel-log__entry"]')).toHaveLength(1);
    expect(w.find('[data-testid="travel-log__prose"]').exists()).toBe(false);
    const more = w.get('[data-testid="travel-log__more"]');
    expect(more.attributes("aria-expanded")).toBe("false");
    await more.trigger("click");
    const body = w.get('[data-testid="travel-log__prose"]');
    expect(more.attributes("aria-expanded")).toBe("true");
    expect(more.attributes("aria-controls")).toBe(body.attributes("id"));
    expect(body.find("img").exists()).toBe(false);
    expect(body.text()).toContain("<img src=x onerror=alert(1)>第二行");
    expect(w.findAll('[data-testid="travel-log__entry"]')).toHaveLength(1);
  });
});

describe("the travel band replaces paging only in travel", () => {
  it("mounts the log in travel and the message window outside it", async () => {
    const h = liveTravel({ wrappers });
    await tick();
    expect(h.w.find('[data-testid="travel-log"]').exists()).toBe(true);
    expect(h.w.find('[data-testid="message-page"]').exists()).toBe(false);
    expect(h.w.find('[data-testid="message-log-open"]').exists()).toBe(true);
    h.publish({ art: panelsAt(TOWN_SUBJECT).art });
    await tick();
    expect(h.w.find('[data-testid="travel-log"]').exists()).toBe(false);
    expect(h.w.find('[data-testid="message-page"]').exists()).toBe(true);
  });
});

// The refusal hook: the walking harness's synthetic wilderness cells.
const CX = 60;
const CY = 80;
function walkHarness() {
  const h = liveTravel({ mounted: false, panels: walkPanels(CX, CY) });
  h.store.setTravelMap({ status: "ready", area: walkArea(CX, CY) });
  const moves = () => h.sender.sent.actions.filter((a) => a.action_id === "explore.move");
  const refuse = (request, extra = {}) =>
    h.accept("ui_action_result", fx.actionResult({
      request_id: request.request_id, presentation_revision: h.store.view.revision,
      outcome: "rejected", code: "blocked", message: "前方的河水太深，無法涉過。", ...extra,
    }));
  const errLines = () => h.store.narrative.filter((l) => l.kind === "err").map((l) => l.text);
  const refusals = () => h.store.view.travel.entries.filter((e) => e.kind === "refusal");
  return { ...h, moves, refuse, errLines, refusals };
}

describe("a refused travel step", () => {
  beforeEach(() => vi.useFakeTimers());

  it("adds one travel entry for a discrete step and keeps the single full-log line", () => {
    const h = walkHarness();
    h.store.stepTravel("east");
    const [request] = h.moves();
    h.refuse(request);
    h.refuse(request);
    expect(h.refusals().map((e) => e.text)).toEqual(["前方的河水太深，無法涉過。"]);
    expect(h.errLines()).toEqual(["前方的河水太深，無法涉過。"]);
    expect(sysLines(h.store)).toEqual([]);
    expect(h.store.view.travel.notice).toMatchObject({ kind: "refused" });
  });

  it("adds one entry when a held walk's step is refused, and the queue appends nothing", () => {
    const h = walkHarness();
    h.store.holdTravel("east");
    vi.advanceTimersByTime(400);
    const [request] = h.moves();
    h.refuse(request);
    expect(h.store.view.travel.walking).toBeNull();
    expect(h.refusals()).toHaveLength(1);
    expect(h.errLines()).toHaveLength(1);
  });

  it("ignores a foreign result and a refusal outside travel", () => {
    const h = walkHarness();
    h.store.stepTravel("east");
    const [request] = h.moves();
    h.refuse({ request_id: "session:99" });
    expect(h.refusals()).toEqual([]);
    expect(h.errLines()).toEqual([]);
    // The matching result still adds exactly one entry afterwards.
    h.refuse(request);
    expect(h.refusals()).toHaveLength(1);

    const town = liveTravel({ mounted: false, subject: TOWN_SUBJECT });
    const sent = town.store.dispatchAction("explore.move", { exit_ref: "e1", current_node: "grid:t_synth_map:2,0" });
    town.accept("ui_action_result", fx.actionResult({ request_id: sent, presentation_revision: 1, outcome: "rejected", code: "blocked", message: "不通。" }));
    expect(town.store.view.travel.entries).toEqual([]);
    expect(town.store.narrative.filter((l) => l.kind === "err")).toHaveLength(1);
  });

  it("joins the newest notice's day and uses the committed clock", () => {
    const h = walkHarness();
    h.publish({ travel_log: travelLogPanel([dusk(ID(1), { day: 7 })]) });
    h.store.stepTravel("east");
    h.refuse(h.moves()[0]);
    const refusal = h.refusals()[0];
    const t = h.store.view.serverTime;
    expect(refusal.day).toBe(7);
    expect(refusal.time).toBe(`${String(t.hour).padStart(2, "0")}:${String(t.minute).padStart(2, "0")}`);
  });
});
