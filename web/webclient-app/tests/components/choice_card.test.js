// exploration-presence-rail (task 1.1): ChoiceCard, the one centred card
// shell. Rows as data, one tab stop with an active descendant, the keys it
// consumes (arrows with wrap, Home / End, digits, Enter / Space, Escape), the
// held-repeat guard, the trailing back row, the focus trap, and the entrance
// that a reconnect's frame (`entrance` false) shows at rest.
import { readFileSync } from "node:fs";
import { join } from "node:path";
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

  // exploration-room-actions (design D4): a row's second `hint` line, the
  // muted notes above the rows, the trash-can badge, and the active row kept
  // by key across a committed update.
  it("renders a row hint, muted notes that are not rows, and a trash-can badge", () => {
    wrapper = mount(ChoiceCard, {
      attachTo: document.body,
      props: {
        rows: [
          { key: "a", label: "看看木箱", hint: "可能藏著什麼", badge: "1", kind: "verb", enabled: true },
          { key: "dismiss", label: "清除建議", icon: "trash", badge: "", kind: "dismiss", enabled: true },
          ROWS[4],
        ],
        notes: ["AI 建議目前不可用"],
      },
    });
    const rows = wrapper.findAll('[role="menuitem"]');
    expect(rows).toHaveLength(3);
    expect(rows[0].get('[data-testid="choice-card-hint"]').text()).toBe("可能藏著什麼");
    expect(wrapper.get('[data-testid="choice-card-note"]').text()).toBe("AI 建議目前不可用");
    expect(wrapper.get('[data-testid="choice-card-note"]').attributes("role")).toBeUndefined();
    expect(rows[1].find('svg[data-icon="trash"]').exists()).toBe(true);
    expect(rows[1].text()).toBe("清除建議");
    // The digits address the rows only.
    wrapper.element.focus();
    wrapper.element.dispatchEvent(new KeyboardEvent("keydown", { key: "1", bubbles: true, cancelable: true }));
    expect(wrapper.emitted("pick")[0]).toEqual(["a"]);
  });

  it("keeps the active row by key when the rows update, else keeps it in range", async () => {
    const first = [
      { key: "a", label: "A", badge: "1", kind: "verb", enabled: true },
      { key: "b", label: "B", badge: "2", kind: "verb", enabled: true },
      { key: "c", label: "C", badge: "3", kind: "verb", enabled: true },
    ];
    wrapper = mount(ChoiceCard, { attachTo: document.body, props: { rows: first } });
    wrapper.vm.setActive(1);
    await nextTick();
    await wrapper.setProps({ rows: [first[2], first[0], first[1]] });
    expect(wrapper.get('[data-active="true"]').attributes("data-row-key")).toBe("b");
    await wrapper.setProps({ rows: [first[2]] });
    expect(wrapper.get('[data-active="true"]').attributes("data-row-key")).toBe("c");
  });

  // slice U: the interaction card's real labelled groups, the digit badges
  // that stop at position 9, and a service flow's return to its originating
  // entry.
  it("renders real labelled groups whose headings are not rows", async () => {
    const grouped = [
      { key: "talk-open", label: "交談", badge: "1", kind: "verb", enabled: false, reason: "對方無法交談。", group: "common", groupLabel: "一般" },
      { key: "look-target", label: "查看", badge: "2", kind: "verb", enabled: true, group: "common", groupLabel: "一般" },
      { key: "service-shop", label: "交易", badge: "3", kind: "verb", enabled: true, group: "services", groupLabel: "服務" },
      { key: "back", label: "返回", badge: "✕", icon: "close", kind: "back", enabled: true, back: true },
    ];
    const w = mountCard({ rows: grouped, trailingIndex: 3 });
    const groups = w.findAll('[role="group"]');
    expect(groups.map((group) => group.attributes("data-group"))).toEqual(["common", "services"]);
    const headings = w.findAll('[data-testid="choice-card-group-heading"]');
    expect(headings.map((heading) => heading.text())).toEqual(["一般", "服務"]);
    // The group's accessible name is the heading it references, and the
    // heading is not selectable, not a row, and adds no tab stop.
    expect(groups[0].attributes("aria-labelledby")).toBe(headings[0].attributes("id"));
    expect(groups[1].attributes("aria-labelledby")).toBe(headings[1].attributes("id"));
    expect(headings[0].attributes("role")).toBe("heading");
    expect(headings[0].attributes("tabindex")).toBeUndefined();
    expect(rows(w)).toHaveLength(4);
    expect(w.findAll("[tabindex]")).toHaveLength(1);
    // The card opens on the first enabled row (the disabled 交談 is skipped);
    // arrows then cross a group boundary without ever landing on a heading,
    // because the index counts rows only.
    expect(activeRow(w)).toBe(rows(w)[1].element);
    await key(w, "ArrowDown");
    await nextTick();
    expect(activeRow(w)).toBe(rows(w)[2].element);
    await key(w, "ArrowDown");
    await nextTick();
    expect(activeRow(w)).toBe(rows(w)[3].element);
    // The disabled common row keeps its inline described reason.
    expect(rows(w)[0].attributes("aria-disabled")).toBe("true");
    const described = rows(w)[0].attributes("aria-describedby");
    expect(document.getElementById(described).textContent).toBe("對方無法交談。");
    // End selects the trailing return, Home the first row.
    await key(w, "Home");
    await nextTick();
    expect(activeRow(w)).toBe(rows(w)[0].element);
    await key(w, "End");
    await nextTick();
    expect(activeRow(w)).toBe(rows(w)[3].element);
  });

  it("badges and digits stop at position 9 and later rows stay reachable", async () => {
    const many = Array.from({ length: 12 }, (_, index) => ({
      key: `row-${index + 1}`,
      label: `列 ${index + 1}`,
      badge: index < 9 ? String(index + 1) : null,
      kind: "verb",
      enabled: true,
      group: "services",
      groupLabel: "服務",
    }));
    const w = mountCard({ rows: [...many, ROWS[4]], trailingIndex: 12 });
    const all = rows(w);
    expect(all).toHaveLength(13);
    // No digit badge past the ninth row, and no alternate numbering scheme.
    expect(all.slice(9, 12).map((row) => row.find(".choice-card__badge").exists())).toEqual([
      false,
      false,
      false,
    ]);
    expect(all[12].text()).toBe("返回");
    await key(w, "9");
    expect(w.emitted("pick").at(-1)).toEqual(["row-9"]);
    // Digits never address a later row.
    await key(w, "1");
    expect(w.emitted("pick")).toHaveLength(2);
    // Arrows reach every row after the ninth and Enter activates it.
    await key(w, "Home");
    for (let step = 0; step < 10; step += 1) {
      await key(w, "ArrowDown");
    }
    await nextTick();
    expect(activeRow(w)).toBe(all[10].element);
    await key(w, "Enter");
    expect(w.emitted("pick").at(-1)).toEqual(["row-11"]);
  });

  it("focusRow returns focus to a surviving entry, else to the first valid row", async () => {
    const grouped = [
      { key: "talk-open", label: "交談", badge: "1", kind: "verb", enabled: false, reason: "不可。", group: "common" },
      { key: "look-target", label: "查看", badge: "2", kind: "verb", enabled: true, group: "common" },
      { key: "service-shop", label: "交易", badge: "3", kind: "verb", enabled: true, group: "services" },
      ROWS[4],
    ];
    const w = mountCard({ rows: grouped, trailingIndex: 3 });
    document.body.focus?.();
    w.vm.focusRow("service-shop");
    await nextTick();
    expect(document.activeElement).toBe(card(w).element);
    expect(activeRow(w)).toBe(rows(w)[2].element);
    // An entry that disappeared falls back to the first enabled row.
    w.vm.focusRow("service-gone");
    await nextTick();
    expect(activeRow(w)).toBe(rows(w)[1].element);
  });

  // authored-dialogue-locked-ui (web/webclient-app/AGENTS.md styling
  // pitfall): the card's own style block is the one source of its rules.
  // app-shell.css carries no `.elosern-root` duplicate or override of a
  // choice-card or dialogue-choices selector that the live client would
  // apply over the component (and Storybook would not show).
  it("has no app-shell.css duplicate of its selectors", () => {
    const shell = readFileSync(join(process.cwd(), "web/webclient-app/styles/app-shell.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
    const selectors = [...shell.matchAll(/([^{}]+)\{/g)].map((match) => match[1].trim());
    expect(selectors.filter((selector) => /\.(choice-card|dialogue-choices)(?![\w-])|\.(choice-card|dialogue-choices)__/.test(selector))).toEqual([]);
  });
});

