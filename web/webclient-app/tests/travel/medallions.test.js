// Party medallions (wilderness-travel-interface, design §8): each present
// member joins its own committed fatigue row; nothing is derived.

import { afterEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import PartyMedallions from "../../components/travel/PartyMedallions.vue";
import { companionFigures } from "../../components/companion-lineup.js";
import { portraitFor } from "../../components/party-helpers.js";
import { medallionLabel, medallionMembers } from "../../components/travel/travel-model.js";
import { WILD_SUBJECT, fx, liveTravel, panelsAt, tick } from "./support.js";

vi.setConfig({ testTimeout: 60000 });

let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
}, 60000);

const row = (identity, name, fields = {}) => ({
  identity, name, reserve_percent: 90, stage: "normal", label: "合成充沛",
  severity: "informational", restriction: null, asleep: false, ...fields,
});
const slot = (identity, name, portraitRef = null) => ({
  identity, display_name: name, portrait_ref: portraitRef, role: "companion",
});

// The owner "1", companions 7 and 8, and a remote companion 9 with no row.
function figures({ possessing = false } = {}) {
  return companionFigures({
    player: { identity: "1", artwork: null, panel: null, hasReference: true, displayName: "合成主角" },
    companions: [slot(7, "合成甲"), slot(8, "合成乙", "88"), slot(9, "合成丙")],
    actorIdentity: possessing ? "7" : "1",
    possessing,
    controlledName: "",
    artPanel: { available: true, portrait_catalog: {} },
    portraitFor,
  });
}

const status = (rows) => fx.statusPanel({ fatigue: rows });

describe("medallion membership", () => {
  it("shows the controlled body once, then the present members in party order", () => {
    const members = medallionMembers(
      figures(),
      status([row("1", "合成主角"), row("8", "合成乙", { reserve_percent: 35, stage: "moderate", label: "合成疲勞" }), row("7", "合成甲")]),
    );
    expect(members.map((m) => [m.key, m.controlled])).toEqual([["1", true], ["7", false], ["8", false]]);
    // The remote member has no row: it is not with the party.
    expect(members.some((m) => m.key === "9")).toBe(false);
    expect(members[2]).toMatchObject({ reserve: 35, stage: "moderate", label: "合成疲勞", asleep: false, available: true });
  });

  it("keeps each body's own facts under possession, never the owner's for the puppet", () => {
    const rows = [
      row("1", "合成主角", { reserve_percent: 80 }),
      row("7", "合成甲", { reserve_percent: 2, stage: "forced_sleep", label: "合成昏睡", restriction: "沉睡中，無法行動", asleep: true }),
      row("8", "合成乙", { reserve_percent: 50, stage: "sleeping", label: "合成睡眠", restriction: "沉睡中，無法行動", asleep: true }),
    ];
    const members = medallionMembers(figures({ possessing: true }), status(rows));
    // The puppet is the controlled front; the owner's body stands at its slot.
    expect(members.map((m) => m.key)).toEqual(["7", "1", "8"]);
    expect(members.filter((m) => m.controlled).map((m) => m.key)).toEqual(["7"]);
    expect(members.map((m) => [m.key, m.reserve, m.asleep])).toEqual([["7", 2, true], ["1", 80, false], ["8", 50, true]]);
  });

  it("reads unavailable, never full, when the controlled body's row is missing", () => {
    const [front, ...rest] = medallionMembers(figures(), status([row("7", "合成甲")]));
    expect(front).toMatchObject({ key: "1", controlled: true, available: false, reserve: null, stage: null });
    expect(medallionLabel(front)).toBe("合成主角：精力資料無法取得");
    expect(rest.map((m) => m.key)).toEqual(["7"]);
    const unavailable = medallionMembers(figures(), { schema_version: 5, available: false, reason: { code: "x", message: "y" } });
    expect(unavailable.map((m) => [m.key, m.available])).toEqual([["1", false]]);
  });

  it("names each member by its reserve and supplied stage label", () => {
    const [front] = medallionMembers(figures(), status([row("1", "合成主角", { reserve_percent: 64, stage: "light", label: "合成微倦" })]));
    expect(medallionLabel(front)).toBe("合成主角：精力 64%（合成微倦）");
  });
});

describe("the medallion strip", () => {
  it("draws the supplied reserve, the stage label, the ring and the crescent", () => {
    const members = medallionMembers(
      figures(),
      status([
        row("1", "合成主角", { reserve_percent: 73 }),
        row("7", "合成甲", { reserve_percent: 18, stage: "severe", label: "合成力竭" }),
        row("8", "合成乙", { reserve_percent: 50, stage: "sleeping", label: "合成睡眠", restriction: "沉睡中，無法行動", asleep: true }),
      ]),
    );
    const w = mount(PartyMedallions, { props: { members } });
    wrappers.push(w);
    const items = w.findAll('[data-testid="party-medallion"]');
    expect(items.map((item) => item.attributes("data-identity"))).toEqual(["1", "7", "8"]);
    expect(items.map((item) => item.attributes("data-controlled"))).toEqual(["true", "false", "false"]);
    expect(items[0].get(".party-medallion__fill").attributes("style")).toContain("width: 73%");
    // No stage label at the normal stage; the supplied one otherwise.
    expect(items[0].find(".party-medallion__stage").exists()).toBe(false);
    expect(items[1].get(".party-medallion__stage").text()).toBe("合成力竭");
    // Sleep is a shape, not a colour: only the sleeper wears the crescent.
    expect(items.map((item) => item.find('[data-testid="party-medallion__moon"]').exists())).toEqual([false, false, true]);
    expect(items[2].attributes("aria-label")).toBe("合成乙：精力 50%（合成睡眠）");
    // The 70 / 40 / 20 % notches.
    expect(items[0].findAll(".party-medallion__notch").map((n) => n.attributes("style"))).toEqual(
      ["left: 20%;", "left: 40%;", "left: 70%;"],
    );
  });

  it("draws an unavailable member with no fill at all", () => {
    const members = medallionMembers(figures(), status([row("7", "合成甲")]));
    const w = mount(PartyMedallions, { props: { members } });
    wrappers.push(w);
    const front = w.findAll('[data-testid="party-medallion"]')[0];
    expect(front.classes()).toContain("is-unavailable");
    expect(front.find(".party-medallion__fill").exists()).toBe(false);
  });

  it("stands under the vitals dock in the live travel shell", async () => {
    const h = liveTravel({
      wrappers,
      panels: panelsAt(WILD_SUBJECT, {
        status: fx.statusPanel({ fatigue: [row("42", "影行者", { reserve_percent: 40, stage: "moderate", label: "合成疲勞" })] }),
      }),
    });
    await tick();
    const vitals = h.w.get('[data-testid="anchor-vitals"]');
    const children = [...vitals.element.children].map((el) => el.getAttribute("data-testid"));
    expect(children.indexOf("status-panel")).toBeLessThan(children.indexOf("party-medallions"));
    // The dock does not repeat the fatigue rows the medallions show.
    expect(vitals.find('[data-testid="status-panel__fatigue"]').exists()).toBe(false);
    expect(vitals.findAll('[data-testid="party-medallion"]')).toHaveLength(1);
  });
});
