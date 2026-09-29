// webclient-dialogue-choices-overlay D5: the dialogue choice list. The rows
// and their badges, the single-tab-stop menu composite (active descendant),
// the keys it consumes (arrows with wrap, Home / End, Enter / Space, the
// digits, Escape in the exits) and the ones it lets through (`/`, Tab),
// the held-repeat guard, pointer parity, the `↦ 移動…` exits with a disabled
// exit and the way back, `locked`, and `beforeActivate` before every emit.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import DialogueChoices from "../components/DialogueChoices.vue";
import { dialogueViewModel } from "../stores/dialogue-view.js";
import { overviewExits } from "../composables/use-dialogue-choices.js";

const PANEL = {
  schema_version: 2,
  available: true,
  kind: "dialogue",
  host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
  bond_stage: "親睦",
  line: "「渡河要五枚銅板。」",
  choices: [
    { keyword_id: "fare", label: "「就五枚，走嗎？」" },
    { keyword_id: "smell", label: "含糊帶過氣味" },
    { keyword_id: "chest", label: "直接問箱櫃下落" },
  ],
};
const PICKS = dialogueViewModel(PANEL).picks;

const EXITS = [
  {
    key: "move-east",
    label: "東",
    direction: "east",
    destination: "room:43",
    enabled: true,
    actionId: "explore.move",
    payload: { exit_ref: "east", current_node: "room:42" },
    commandDisplay: { exitLabel: "東" },
  },
  {
    key: "move-north",
    label: "北",
    direction: "north",
    destination: "room:44",
    enabled: false,
    disabled_reason: { code: "blocked", message: "門被鎖住了" },
    actionId: "explore.move",
    payload: { exit_ref: "north", current_node: "room:42" },
    commandDisplay: { exitLabel: "北" },
  },
];
const LOCAL_MAP = { nodes: [{ id: "room:43", label: "西風酒館" }, { id: "room:44", label: "北岸大道" }] };

describe("DialogueChoices", () => {
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

  function mountList(props = {}) {
    wrapper = mount(DialogueChoices, {
      attachTo: document.body,
      props: { picks: PICKS, exits: EXITS, localMap: LOCAL_MAP, ...props },
    });
    wrapper.vm.focus();
    return wrapper;
  }

  const list = (w) => w.get('[data-testid="dialogue-choices"]');
  const rows = (w) => w.findAll('[role="menuitem"]');
  const labels = (w) => rows(w).map((row) => row.get(".dialogue-choices__label").text());
  const badges = (w) => rows(w).map((row) => row.get(".dialogue-choices__badge").attributes("data-badge"));
  const activeRow = (w) => document.getElementById(list(w).attributes("aria-activedescendant"));

  async function key(w, name, init = {}) {
    list(w).element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true, ...init }));
    await nextTick();
  }

  it("renders the picks with digit badges, then the free, move, and leave rows, and nothing else", () => {
    const w = mountList();
    expect(labels(w)).toEqual(["「就五枚，走嗎？」", "含糊帶過氣味", "直接問箱櫃下落", "自由對話", "移動…", "結束對話"]);
    expect(badges(w)).toEqual(["1", "2", "3", "⌨", "↦", "✕"]);
    expect(rows(w).map((row) => row.attributes("data-testid"))).toEqual([
      "dialogue-pick",
      "dialogue-pick",
      "dialogue-pick",
      "dialogue-freeform",
      "dialogue-move",
      "dialogue-exit",
    ]);
    expect(rows(w)[1].attributes("data-keyword-id")).toBe("smell");
    expect(w.find('[aria-disabled="true"]').exists()).toBe(false);
  });

  it("with no picks renders only the three trailing rows", () => {
    const w = mountList({ picks: [] });
    expect(labels(w)).toEqual(["自由對話", "移動…", "結束對話"]);
  });

  it("is one tab stop: a menu that names its active row", () => {
    const w = mountList();
    const el = list(w);
    expect(el.attributes("role")).toBe("menu");
    expect(el.attributes("aria-label")).toBe("對話選項");
    expect(el.attributes("tabindex")).toBe("0");
    expect(document.activeElement).toBe(el.element);
    expect(w.findAll("[tabindex]")).toHaveLength(1);
    expect(activeRow(w)).toBe(rows(w)[0].element);
  });

  it("moves with the arrows, wrapping, and jumps with Home and End; the keys never reach the document", async () => {
    const w = mountList();
    await key(w, "ArrowUp");
    expect(activeRow(w)).toBe(rows(w)[5].element);
    await key(w, "ArrowDown");
    expect(activeRow(w)).toBe(rows(w)[0].element);
    await key(w, "ArrowDown");
    await key(w, "ArrowDown");
    expect(activeRow(w)).toBe(rows(w)[2].element);
    await key(w, "End");
    expect(activeRow(w)).toBe(rows(w)[5].element);
    await key(w, "Home");
    expect(activeRow(w)).toBe(rows(w)[0].element);
    expect(documentKeys).toEqual([]);
  });

  it("activates the active row on Enter and on Space, once each, and consumes both", async () => {
    const before = vi.fn();
    const w = mountList({ beforeActivate: before });
    await key(w, "ArrowDown");
    await key(w, "Enter");
    expect(w.emitted("pick")).toEqual([[PICKS[1]]]);
    await key(w, "End");
    await key(w, " ");
    expect(w.emitted("leave")).toHaveLength(1);
    expect(before).toHaveBeenCalledTimes(2);
    expect(documentKeys).toEqual([]);
  });

  it("lets Shift+Enter and Shift+Space through without activating", async () => {
    const w = mountList();
    await key(w, "Enter", { shiftKey: true });
    await key(w, " ", { shiftKey: true });
    expect(w.emitted("pick")).toBeUndefined();
    expect(documentKeys).toEqual(["Enter", " "]);
  });

  it("ignores a held Enter's repeat, which is still consumed", async () => {
    const w = mountList();
    await key(w, "Enter", { repeat: true });
    expect(w.emitted("pick")).toBeUndefined();
    expect(documentKeys).toEqual([]);
  });

  it("digit N activates pick N directly; a digit past the picks passes through", async () => {
    const w = mountList();
    await key(w, "2");
    expect(w.emitted("pick")).toEqual([[PICKS[1]]]);
    expect(activeRow(w)).toBe(rows(w)[1].element);
    await key(w, "4");
    expect(w.emitted("pick")).toHaveLength(1);
    expect(documentKeys).toEqual(["4"]);
    await key(w, "3", { repeat: true });
    expect(w.emitted("pick")).toHaveLength(1);
  });

  it("lets `/`, Tab, Escape (in the choices), and modified keys through untouched", async () => {
    const w = mountList();
    await key(w, "/");
    await key(w, "Tab");
    await key(w, "Escape");
    await key(w, "1", { ctrlKey: true });
    expect(documentKeys).toEqual(["/", "Tab", "Escape", "1"]);
    expect(w.emitted("pick")).toBeUndefined();
  });

  it("emits freeform and leave from their rows, each after beforeActivate", async () => {
    const order = [];
    const w = mountList({ beforeActivate: () => order.push("before"), onFreeform: () => order.push("freeform") });
    await rows(w)[3].trigger("click");
    expect(w.emitted("freeform")).toHaveLength(1);
    await rows(w)[5].trigger("click");
    expect(w.emitted("leave")).toHaveLength(1);
    expect(order.slice(0, 2)).toEqual(["before", "freeform"]);
    expect(order.filter((entry) => entry === "before")).toHaveLength(2);
  });

  it("a pointer activation focuses the list, marks the row active, and runs the same path as Enter", async () => {
    const w = mountList();
    document.body.focus();
    await rows(w)[2].trigger("click");
    expect(document.activeElement).toBe(list(w).element);
    expect(activeRow(w)).toBe(rows(w)[2].element);
    expect(w.emitted("pick")).toEqual([[PICKS[2]]]);
  });

  it("`↦ 移動…` swaps in the exits and the back row, dispatching nothing", async () => {
    const before = vi.fn();
    const w = mountList({ beforeActivate: before });
    await key(w, "End");
    await key(w, "ArrowUp");
    await key(w, "Enter");
    expect(before).not.toHaveBeenCalled();
    expect(Object.keys(w.emitted()).filter((name) => ["pick", "freeform", "move", "leave"].includes(name))).toEqual([]);
    expect(list(w).attributes("data-view")).toBe("exits");
    expect(labels(w)).toEqual(["西風酒館", "北", "返回對話"]);
    expect(badges(w)).toEqual(["→", "↑", "↩"]);
    expect(rows(w).map((row) => row.attributes("data-testid"))).toEqual([
      "dialogue-exit-row",
      "dialogue-exit-row",
      "dialogue-exits-back",
    ]);
    expect(activeRow(w)).toBe(rows(w)[0].element);
  });

  it("an enabled exit emits move with the overview item; a disabled one keeps its reason and emits nothing", async () => {
    const w = mountList();
    await rows(w)[4].trigger("click");
    const locked = rows(w)[1];
    expect(locked.attributes("aria-disabled")).toBe("true");
    const reason = locked.get('[data-testid="dialogue-exit-reason"]');
    expect(reason.text()).toBe("門被鎖住了");
    expect(locked.attributes("aria-describedby")).toBe(reason.attributes("id"));
    await key(w, "ArrowDown");
    await key(w, "Enter");
    expect(w.emitted("move")).toBeUndefined();
    await key(w, "Home");
    await key(w, "Enter");
    expect(w.emitted("move")).toEqual([[EXITS[0]]]);
  });

  it("Escape and the back row return to the choices with `↦ 移動…` active; digits do nothing in the exits", async () => {
    const w = mountList();
    await rows(w)[4].trigger("click");
    await key(w, "1");
    expect(w.emitted("pick")).toBeUndefined();
    await key(w, "Escape");
    expect(list(w).attributes("data-view")).toBe("choices");
    expect(activeRow(w).getAttribute("data-testid")).toBe("dialogue-move");
    expect(documentKeys).toEqual(["1"]);
    await rows(w)[4].trigger("click");
    await rows(w)[2].trigger("click");
    expect(list(w).attributes("data-view")).toBe("choices");
    expect(activeRow(w).getAttribute("data-testid")).toBe("dialogue-move");
  });

  // webclient-message-typesetting: the initial highlight.
  it("opens the exits on the first enabled exit when the first is disabled", async () => {
    const w = mountList({ exits: [EXITS[1], EXITS[0]] });
    await rows(w)[4].trigger("click");
    expect(rows(w)[0].attributes("aria-disabled")).toBe("true");
    expect(activeRow(w)).toBe(rows(w)[1].element);
    expect(w.emitted("move")).toBeUndefined();
  });

  it("with every exit disabled keeps the first exit active with its explanation, not the back row", async () => {
    const w = mountList({ exits: [EXITS[1]] });
    await rows(w)[4].trigger("click");
    const first = rows(w)[0];
    expect(activeRow(w)).toBe(first.element);
    expect(first.attributes("aria-describedby")).toBe(first.get('[data-testid="dialogue-exit-reason"]').attributes("id"));
    await key(w, "Enter");
    expect(w.emitted("move")).toBeUndefined();
  });

  it("an unfocused list shows its first row as active without taking focus or activating it", async () => {
    const outside = document.createElement("button");
    document.body.appendChild(outside);
    outside.focus();
    wrapper = mount(DialogueChoices, {
      attachTo: document.body,
      props: { picks: PICKS, exits: EXITS, localMap: LOCAL_MAP },
    });
    const w = wrapper;
    await nextTick();
    expect(document.activeElement).toBe(outside);
    expect(activeRow(w)).toBe(rows(w)[0].element);
    expect(rows(w)[0].classes()).toContain("dialogue-choices__row--active");
    expect(rows(w)[0].attributes("data-active")).toBe("true");
    expect(Object.keys(w.emitted()).filter((name) => ["pick", "freeform", "move", "leave"].includes(name))).toEqual([]);
    // Taking focus later (Tab) continues from that row; only a deliberate
    // activation dispatches.
    w.vm.focus();
    await key(w, "ArrowDown");
    expect(w.emitted("pick")).toBeUndefined();
    await key(w, "Enter");
    expect(w.emitted("pick")).toEqual([[PICKS[1]]]);
  });

  it("a room with no exits shows the back row alone", async () => {
    const w = mountList({ exits: [] });
    await rows(w)[4].trigger("click");
    expect(labels(w)).toEqual(["返回對話"]);
  });

  it("`locked` suppresses every activation", async () => {
    const before = vi.fn();
    const w = mountList({ locked: true, beforeActivate: before });
    await key(w, "Enter");
    await key(w, "1");
    await rows(w)[5].trigger("click");
    expect(before).not.toHaveBeenCalled();
    expect(w.emitted("pick")).toBeUndefined();
    expect(w.emitted("leave")).toBeUndefined();
  });
});

describe("overviewExits", () => {
  it("slices the overview's items by its `exits` section, in reading order", () => {
    const menu = {
      items: [{ key: "a" }, { key: "b" }, { key: "p" }, { key: "f" }],
      sections: [
        { key: "exits", count: 2 },
        { key: "people", count: 1 },
        { key: "footer", count: 1 },
      ],
    };
    expect(overviewExits(menu).map((item) => item.key)).toEqual(["a", "b"]);
    expect(overviewExits({ items: menu.items, sections: [{ key: "people", count: 1 }, { key: "exits", count: 2 }] }).map((i) => i.key)).toEqual(["b", "p"]);
    expect(overviewExits(null)).toEqual([]);
    expect(overviewExits({ items: menu.items, sections: [] })).toEqual([]);
  });
});
