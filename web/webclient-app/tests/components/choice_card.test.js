// exploration-presence-rail (task 1.1): ChoiceCard, the one centred card
// shell. Rows as data, one tab stop with an active descendant, the keys it
// consumes (arrows with wrap, Home / End, digits, Enter / Space, Escape), the
// held-repeat guard, the trailing back row, the focus trap, and the entrance
// that a reconnect's frame (`entrance` false) shows at rest.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import ChoiceCard from "../../components/ChoiceCard.vue";

const ROWS = [
  { key: "talk-open", label: "交談", badge: "1", kind: "verb", enabled: true },
  { key: "service-shop", label: "交易", badge: "2", kind: "verb", enabled: true },
  {
    key: "engage",
    label: "戰鬥",
    badge: "3",
    kind: "verb",
    enabled: false,
    reason: "這裡不能動手。",
  },
  { key: "look-target", label: "查看", badge: "4", kind: "verb", enabled: true },
  { key: "back", label: "返回", badge: "✕", icon: "close", kind: "back", enabled: true, back: true },
];

describe("ChoiceCard", () => {
  let wrapper;
  let documentKeys;
  const onDocumentKey = (event) => documentKeys.push(event.key);

  beforeEach(() => {
    documentKeys = [];
    document.addEventListener("keydown", onDocumentKey);
  });

  afterEach(() => {
    document.removeEventListener("keydown", onDocumentKey);
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountCard(props = {}) {
    wrapper = mount(ChoiceCard, {
      attachTo: document.body,
      props: { rows: ROWS, trailingIndex: 4, autofocus: true, ...props },
    });
    return wrapper;
  }

  const card = (w) => w.get('[data-testid="choice-card"]');
  const rows = (w) => w.findAll('[role="menuitem"]');
  const activeRow = (w) => document.getElementById(card(w).attributes("aria-activedescendant"));

  async function key(w, name, init = {}) {
    card(w).element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
    await nextTick();
  }

  it("renders the rows with their badges, one tab stop, and the rule before the trailing row", () => {
    const w = mountCard();
    expect(rows(w).map((row) => row.text())).toEqual(["1交談", "2交易", "3戰鬥這裡不能動手。", "4查看", "返回"]);
    expect(card(w).attributes("role")).toBe("menu");
    expect(w.findAll("[tabindex]")).toHaveLength(1);
    expect(document.activeElement).toBe(card(w).element);
    expect(rows(w)[4].classes()).toContain("choice-card__row--trailing");
    expect(rows(w)[2].attributes("aria-disabled")).toBe("true");
    expect(rows(w)[2].attributes("aria-describedby")).toBeTruthy();
    // The first enabled row starts active.
    expect(activeRow(w)).toBe(rows(w)[0].element);
  });

  it("arrows wrap, Home / End jump, and Enter picks the active row", async () => {
    const w = mountCard();
    await key(w, "ArrowUp");
    expect(activeRow(w)).toBe(rows(w)[4].element);
    await key(w, "ArrowDown");
    expect(activeRow(w)).toBe(rows(w)[0].element);
    await key(w, "End");
    expect(activeRow(w)).toBe(rows(w)[4].element);
    await key(w, "Home");
    await key(w, "ArrowDown");
    await key(w, "Enter");
    expect(w.emitted("pick")).toEqual([["service-shop"]]);
    expect(documentKeys).toEqual([]);
  });

  it("digits pick the Nth row and a digit beyond the rows is claimed and does nothing", async () => {
    const w = mountCard();
    await key(w, "4");
    expect(w.emitted("pick")).toEqual([["look-target"]]);
    await key(w, "7");
    expect(w.emitted("pick")).toHaveLength(1);
    expect(documentKeys).toEqual([]);
  });

  it("keys, digits, and Enter in order: 3 then ArrowDown then Enter", async () => {
    const enabledRows = ROWS.map((row) => ({ ...row, enabled: true, reason: null }));
    const w = mountCard({ rows: enabledRows });
    await key(w, "3");
    await key(w, "ArrowDown");
    await key(w, "Enter");
    expect(w.emitted("pick")).toEqual([["engage"], ["look-target"]]);
  });

  it("a held repeat never activates", async () => {
    const w = mountCard();
    await key(w, "Enter", { repeat: true });
    await key(w, "2", { repeat: true });
    expect(w.emitted("pick")).toBeUndefined();
  });

  it("a disabled row explains itself and emits nothing", async () => {
    const w = mountCard();
    await key(w, "3");
    expect(activeRow(w)).toBe(rows(w)[2].element);
    await key(w, "Enter");
    expect(w.emitted("pick")).toBeUndefined();
  });

  it("the trailing back row and Escape emit back, never pick", async () => {
    const w = mountCard();
    await rows(w)[4].trigger("click");
    await key(w, "Escape");
    expect(w.emitted("back")).toHaveLength(2);
    expect(w.emitted("pick")).toBeUndefined();
  });

  it("traps Tab while trapFocus is set and lets it through otherwise", async () => {
    const w = mountCard({ trapFocus: true });
    await key(w, "Tab");
    expect(documentKeys).toEqual([]);
    w.unmount();
    wrapper = null;
    const open = mountCard();
    await key(open, "Tab");
    expect(documentKeys).toEqual(["Tab"]);
  });

  it("the dialogue switches let Escape and out-of-range digits pass through", async () => {
    const w = mountCard({ escapeBack: false, digitRows: 2, claimDigits: false });
    await key(w, "Escape");
    await key(w, "3");
    expect(documentKeys).toEqual(["Escape", "3"]);
    expect(w.emitted("back")).toBeUndefined();
  });

  it("renders a parallel block's classes beside the generic ones", () => {
    const w = mountCard({ block: "dialogue-choices" });
    expect(card(w).classes()).toEqual(expect.arrayContaining(["choice-card", "dialogue-choices"]));
    expect(rows(w)[0].classes()).toEqual(
      expect.arrayContaining(["choice-card__row--active", "dialogue-choices__row--active"]),
    );
  });

  it("animates in by default and shows at rest when the entrance is off", () => {
    const animated = mountCard();
    expect(card(animated).classes()).not.toContain("choice-card--still");
    animated.unmount();
    wrapper = null;
    const still = mountCard({ entrance: false });
    expect(card(still).classes()).toContain("choice-card--still");
    expect(card(still).classes()).toContain("choice-card--rows-still");
  });

  it("a new view key re-staggers the rows", async () => {
    const w = mountCard({ entrance: false, viewKey: "a" });
    await w.setProps({ viewKey: "b" });
    expect(card(w).classes()).not.toContain("choice-card--rows-still");
    expect(card(w).classes()).toContain("choice-card--still");
  });
});
