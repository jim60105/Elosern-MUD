// landmark-rite-surfaces (design D7): the rite model, the rite arrival card,
// the rite panel and the rite backdrop, each mounted alone over synthetic
// panels. Assertions read structure, state attributes, test ids and emitted
// events; where two states differ, the rendered texts are compared rather
// than the interface wording.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import RitePanels from "../../../static/webclient/js/elosern/protocol/panels/rite.js";
import RiteBackdrop from "../../components/rite/RiteBackdrop.vue";
import RitePanel from "../../components/rite/RitePanel.vue";
import RiteArrivalCard from "../../components/rite/RiteArrivalCard.vue";
import { SOLO_ONLY_REASON, UNSEEN_LABEL, riteRows, ritePerformers } from "../../components/rite/rite-model.js";
import { RITE_ART_PANEL, RITE_PARTY, ritePanel, ritePanelWithArt } from "../../stories/fixtures/rite.js";

// Every mounted wrapper is unmounted, then the body cleared, in one hook, so
// a failed assertion never leaves a live app or listener behind.
const mounted = [];
function track(wrapper) {
  mounted.push(wrapper);
  return wrapper;
}

afterEach(() => {
  while (mounted.length) mounted.pop().unmount();
  document.body.innerHTML = "";
});

describe("rite fixtures", () => {
  it("are valid committed rite panels", () => {
    expect(() => RitePanels.validateRitePanel(ritePanel())).not.toThrow();
    expect(() => RitePanels.validateRitePanel(ritePanelWithArt({ performers: RITE_PARTY, seen: ["drink"] }))).not.toThrow();
  });
});

describe("rite model", () => {
  it("names the performers: the first row is self, the rest by member id", () => {
    const performers = ritePerformers(ritePanel({ performers: RITE_PARTY }));
    expect(performers).toEqual([
      { id: "self", memberId: null, name: "合成旅人", self: true },
      { id: "7", memberId: 7, name: "合成同伴", self: false },
      { id: "8", memberId: 8, name: "合成學徒", self: false },
    ]);
  });

  it("a possessed companion in the first row is not self", () => {
    const [first] = ritePerformers(
      ritePanel({ performers: [{ member_id: null, name: "合成附身者", owner: false }, { member_id: 3, name: "合成主人", owner: true }] }),
    );
    expect(first).toEqual({ id: "self", memberId: null, name: "合成附身者", self: false });
  });

  it("the controlled character may pick every option; only unseen ones are unread", () => {
    const rite = ritePanel({ seen: ["bathe"] });
    const rows = riteRows(rite, ritePerformers(rite)[0]);
    expect(rows.map((row) => row.key)).toEqual(["drink", "bathe", "leave"]);
    expect(rows.slice(0, 2)).toEqual([
      { key: "drink", badge: "1", label: "俯身飲下", enabled: true, reason: null, unread: true },
      { key: "bathe", badge: "2", label: "浸入池中", enabled: true, reason: null, unread: false },
    ]);
    expect(rows[2]).toMatchObject({ key: "leave", back: true, kind: "leave", icon: "close" });
  });

  it("a companion cannot pick a solo-only option, which is not marked unread", () => {
    const rite = ritePanel({ performers: RITE_PARTY });
    const rows = riteRows(rite, ritePerformers(rite)[1]);
    expect(rows[0]).toMatchObject({ key: "drink", enabled: true, reason: null, unread: true });
    expect(rows[1]).toMatchObject({ key: "bathe", enabled: false, reason: SOLO_ONLY_REASON, unread: false });
  });
});

describe("RiteArrivalCard", () => {
  let documentKeys = [];
  const onDocumentKey = (event) => documentKeys.push(event.key);

  beforeEach(() => {
    documentKeys = [];
    document.addEventListener("keydown", onDocumentKey);
  });

  afterEach(() => {
    document.removeEventListener("keydown", onDocumentKey);
  });

  function mountCard(rite = ritePanel(), props = {}) {
    return track(mount(RiteArrivalCard, { attachTo: document.body, props: { rite, artPanel: RITE_ART_PANEL, ...props } }));
  }

  const byId = (w, id) => w.get(`[data-testid="${id}"]`);

  async function key(target, name, init = {}) {
    target.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
    await nextTick();
  }

  it("shows the unlit and the lit district line, the guardian and the experienced count", () => {
    const unlit = mountCard(ritePanel({ seen: ["drink"] }));
    const unlitLine = byId(unlit, "rite-arrival-district");
    expect(unlitLine.attributes("data-lit")).toBe("false");
    expect(unlitLine.text()).toContain("合成高地");
    expect(byId(unlit, "rite-arrival-landmark").text()).toBe("合成石龕");
    expect(byId(unlit, "rite-arrival-guardian").text()).toContain("合成泉聲");
    expect(byId(unlit, "rite-arrival-guardian").text()).toContain("水面映出的聲音");
    const seen = byId(unlit, "rite-arrival-seen");
    expect([seen.attributes("data-seen"), seen.attributes("data-total")]).toEqual(["1", "2"]);
    expect(seen.text()).toMatch(/1\D+2/);
    const unlitText = unlitLine.text();

    const litCard = mountCard(ritePanel({ district: { ...ritePanel().district, lit: true } }));
    const litLine = byId(litCard, "rite-arrival-district");
    expect(litLine.attributes("data-lit")).toBe("true");
    expect(litLine.text()).toContain("合成高地");
    expect(litLine.text()).not.toBe(unlitText);
  });

  it("reads differently as a revisit than as an arrival", () => {
    const arrival = mountCard();
    const kicker = byId(arrival, "rite-arrival-kicker");
    expect(kicker.attributes("data-revisit")).toBe("false");
    const arrivalText = kicker.text();
    const revisit = mountCard(ritePanel(), { revisit: true });
    expect(byId(revisit, "rite-arrival-kicker").attributes("data-revisit")).toBe("true");
    expect(byId(revisit, "rite-arrival-kicker").text()).not.toBe(arrivalText);
  });

  it("focuses approach on mount; Enter approaches once and a held repeat does nothing", async () => {
    const w = mountCard();
    expect(document.activeElement).toBe(byId(w, "rite-arrival-approach").element);
    const root = byId(w, "rite-arrival-card").element;
    await key(document.activeElement, "Enter");
    await key(document.activeElement, "Enter", { repeat: true });
    expect(w.emitted("approach")).toHaveLength(1);
    expect(w.emitted("leave")).toBeUndefined();
    await key(root, "Escape");
    expect(w.emitted("leave")).toHaveLength(1);
    await key(root, "Escape", { repeat: true });
    expect(w.emitted("leave")).toHaveLength(1);
    await key(root, "x");
    expect(documentKeys).toEqual([]);
  });

  it("Enter on the dialog itself approaches", async () => {
    const w = mountCard();
    await key(byId(w, "rite-arrival-card").element, "Enter");
    expect(w.emitted("approach")).toHaveLength(1);
    expect(w.emitted("leave")).toBeUndefined();
  });

  it("an IME composition's Enter and Escape do nothing", async () => {
    const w = mountCard();
    await key(document.activeElement, "Enter", { isComposing: true });
    await key(document.activeElement, "Escape", { isComposing: true });
    expect(w.emitted("approach")).toBeUndefined();
    expect(w.emitted("leave")).toBeUndefined();
  });

  it("Tab moves only between the two buttons, and Enter on the leave button leaves", async () => {
    const w = mountCard();
    const leave = byId(w, "rite-arrival-leave").element;
    const approach = byId(w, "rite-arrival-approach").element;
    await key(document.activeElement, "Tab");
    expect(document.activeElement).toBe(leave);
    await key(document.activeElement, "Tab", { shiftKey: true });
    expect(document.activeElement).toBe(approach);
    await key(document.activeElement, "Tab");
    expect(document.activeElement).toBe(leave);
    expect(documentKeys).toEqual([]);
    await key(leave, "Enter");
    expect(w.emitted("leave")).toHaveLength(1);
    expect(w.emitted("approach")).toBeUndefined();
  });

  it("each button's click emits its own event", async () => {
    const w = mountCard();
    await byId(w, "rite-arrival-leave").trigger("click");
    await byId(w, "rite-arrival-approach").trigger("click");
    expect(w.emitted("leave")).toHaveLength(1);
    expect(w.emitted("approach")).toHaveLength(1);
  });

  it("collapses the art band without a descriptor and shows the artwork with one", () => {
    const plain = mountCard();
    expect(plain.find('[data-testid="artwork-preview"]').exists()).toBe(false);
    expect(plain.find("img").exists()).toBe(false);
    expect(byId(plain, "rite-arrival-art").classes()).toContain("is-empty");
    const art = mountCard(ritePanelWithArt());
    expect(art.find('[data-testid="artwork-preview"]').exists()).toBe(true);
    expect(byId(art, "rite-arrival-art").classes()).not.toContain("is-empty");
  });

  it("renders no line of the panel's delivery", () => {
    const delivery = {
      kind: "formal",
      delivery_id: "rite:synthetic_highlands:drink:1",
      scene_id: "rite.synthetic.drink.self",
      scene_revision: "r1",
      actor_name: "合成旅人",
      guardian_name: "合成泉聲",
      lines: [
        { kind: "narration", text: "合成敘述之一。" },
        { kind: "speech", speaker: "host", text: "合成台詞之二。" },
      ],
    };
    const rite = ritePanel({ delivery });
    expect(() => RitePanels.validateRitePanel(rite)).not.toThrow();
    const w = mountCard(rite);
    const text = w.text();
    for (const line of delivery.lines) expect(text).not.toContain(line.text);
  });

  it("shows at rest when the entrance is off", () => {
    const w = mountCard(ritePanel(), { entrance: false });
    expect(byId(w, "rite-arrival-card").classes()).toContain("choice-card--still");
  });
});

describe("RitePanel", () => {
  let documentKeys = [];
  const onDocumentKey = (event) => documentKeys.push(event.key);

  beforeEach(() => {
    documentKeys = [];
    document.addEventListener("keydown", onDocumentKey);
  });

  afterEach(() => {
    document.removeEventListener("keydown", onDocumentKey);
  });

  function mountPanel(rite = ritePanel(), performerIndex = 0, props = {}) {
    return track(
      mount(RitePanel, {
        attachTo: document.body,
        props: { rite, performer: ritePerformers(rite)[performerIndex], ...props },
      }),
    );
  }

  const card = (w) => w.get('[data-testid="rite-panel"]');
  const rows = (w) => w.findAll('[role="menuitem"]');
  const row = (w, rowKey) => w.get(`[data-row-key="${rowKey}"]`);

  async function key(w, name, init = {}) {
    card(w).element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
    await nextTick();
  }

  it("renders one row per option in order and then the leave row", () => {
    const w = mountPanel(ritePanel({ options: [...ritePanel().options, { key: "listen", label: "合成第三式", companion: true }] }));
    expect(rows(w).map((r) => r.attributes("data-row-key"))).toEqual(["drink", "bathe", "listen", "leave"]);
    expect(rows(w)[0].text()).toContain("俯身飲下");
    expect(rows(w)[3].classes()).toContain("choice-card__row--trailing");
    expect(document.activeElement).toBe(card(w).element);
  });

  it("a digit performs its option, Enter performs the active row, Escape and the leave row leave", async () => {
    const w = mountPanel();
    await key(w, "1");
    expect(w.emitted("perform")).toEqual([["drink"]]);
    await key(w, "ArrowDown");
    await key(w, "Enter");
    expect(w.emitted("perform")).toEqual([["drink"], ["bathe"]]);
    await key(w, "Escape");
    await row(w, "leave").trigger("click");
    expect(w.emitted("leave")).toHaveLength(2);
    await key(w, "Tab");
    expect(documentKeys).toEqual([]);
  });

  it("names the performer in the header inside the card frame, before the rows", () => {
    const rite = ritePanel({ performers: RITE_PARTY });
    const w = mountPanel(rite, 1);
    const header = card(w).get(".choice-card__header");
    expect(header.get('[data-testid="rite-panel-performer"]').text()).toContain("合成同伴");
    const rowsBox = card(w).get(".choice-card__rows").element;
    expect(header.element.compareDocumentPosition(rowsBox) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(card(w).attributes("data-view")).toBe("rite-7");
  });

  it("only the unseen row carries the not-yet-experienced mark and text", () => {
    const w = mountPanel(ritePanel({ seen: ["bathe"] }));
    const unseen = row(w, "drink");
    const seen = row(w, "bathe");
    expect(unseen.attributes("data-unread")).toBe("true");
    expect(unseen.find('[data-testid="choice-card-unread"]').exists()).toBe(true);
    expect(unseen.text()).toContain(UNSEEN_LABEL);
    expect(seen.attributes("data-unread")).toBeUndefined();
    expect(seen.find('[data-testid="choice-card-unread"]').exists()).toBe(false);
    expect(seen.text()).not.toContain(UNSEEN_LABEL);
  });

  it("a companion's solo-only row is disabled with its reason and emits nothing", async () => {
    const w = mountPanel(ritePanel({ performers: RITE_PARTY }), 1);
    const solo = row(w, "bathe");
    expect(solo.attributes("aria-disabled")).toBe("true");
    expect(solo.get('[data-testid="choice-card-reason"]').text()).toBe(SOLO_ONLY_REASON);
    await key(w, "2");
    await key(w, "Enter");
    await solo.trigger("click");
    expect(w.emitted("perform")).toBeUndefined();
    await key(w, "1");
    expect(w.emitted("perform")).toEqual([["drink"]]);
  });
});

describe("RitePanel performer switching", () => {
  let documentKeys = [];
  const onDocumentKey = (event) => documentKeys.push(event.key);

  beforeEach(() => {
    documentKeys = [];
    document.addEventListener("keydown", onDocumentKey);
  });

  afterEach(() => {
    document.removeEventListener("keydown", onDocumentKey);
  });

  function mountPanel(canSwitch) {
    const rite = ritePanel({ performers: RITE_PARTY });
    return track(
      mount(RitePanel, {
        attachTo: document.body,
        props: { rite, performer: ritePerformers(rite)[0], canSwitch },
      }),
    );
  }

  const card = (w) => w.get('[data-testid="rite-panel"]');
  const activeRow = (w) => w.get('[data-active="true"]').attributes("data-row-key");
  async function key(w, name, init = {}) {
    card(w).element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
    await nextTick();
  }

  it("shows the hint and steps the performer with the arrows without moving the active row", async () => {
    const w = mountPanel(true);
    expect(w.find('[data-testid="rite-panel-performer-hint"]').exists()).toBe(true);
    await key(w, "ArrowDown");
    expect(activeRow(w)).toBe("bathe");
    await key(w, "ArrowLeft");
    await key(w, "ArrowRight");
    expect(w.emitted("step-performer")).toEqual([[-1], [1]]);
    expect(activeRow(w)).toBe("bathe");
    expect(documentKeys).toEqual([]);
    // A modifier or an IME composition passes the key through.
    await key(w, "ArrowRight", { altKey: true });
    await key(w, "ArrowRight", { isComposing: true });
    expect(w.emitted("step-performer")).toHaveLength(2);
  });

  it("without picking there is no hint and the arrows emit nothing", async () => {
    const w = mountPanel(false);
    expect(w.find('[data-testid="rite-panel-performer-hint"]').exists()).toBe(false);
    await key(w, "ArrowLeft");
    await key(w, "ArrowRight");
    expect(w.emitted("step-performer")).toBeUndefined();
    expect(documentKeys).toEqual(["ArrowLeft", "ArrowRight"]);
  });
});

describe("RiteBackdrop", () => {
  it("names the landmark and the guardian over the artwork", () => {
    const w = track(mount(RiteBackdrop, { props: { rite: ritePanelWithArt(), artPanel: RITE_ART_PANEL } }));
    const plate = w.get('[data-testid="rite-backdrop-plate"]').text();
    expect(plate).toContain("合成石龕");
    expect(plate).toContain("合成泉聲");
    expect(w.find('[data-testid="artwork-preview"]').exists()).toBe(true);
    expect(w.get('[data-testid="rite-backdrop"]').classes()).not.toContain("is-empty");
  });

  it("shows quiet ink with the same plate and no image without artwork", () => {
    const w = track(mount(RiteBackdrop, { props: { rite: ritePanel(), artPanel: RITE_ART_PANEL } }));
    const plate = w.get('[data-testid="rite-backdrop-plate"]').text();
    expect(plate).toContain("合成石龕");
    expect(plate).toContain("合成泉聲");
    expect(w.find('[data-testid="artwork-preview"]').exists()).toBe(false);
    expect(w.find("img").exists()).toBe(false);
    expect(w.get('[data-testid="rite-backdrop"]').classes()).toContain("is-empty");
  });
});
