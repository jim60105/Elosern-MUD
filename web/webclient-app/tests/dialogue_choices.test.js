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
import { choiceRow, dialoguePanel as v3Panel, unavailableDialoguePanel } from "./support/dialogue_panel.js";

const PANEL = v3Panel({
  keywords: ["fare", "smell", "chest"],
  labels: ["「就五枚，走嗎？」", "含糊帶過氣味", "直接問箱櫃下落"],
});
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

  // authored-dialogue-locked-ui: a visibly locked topic is a selectable
  // refusal with a lock and the server's canonical hint; an operational
  // disabled state emits nothing.
  describe("locked topics", () => {
    const LONG_HINT = `需要（需要持有${"霧門通行證".repeat(12)}）且（需要好感階段至少為熟識）`;
    const GENERATED_ID = `g.${"q".repeat(40)}.${"z".repeat(2048 - 43)}`;
    const LOCKED_PANEL = v3Panel({
      choices: [
        choiceRow("fare", { topicId: "host.fare", label: "渡河的價錢" }),
        { ...choiceRow("gate", { topicId: "host.gate", label: "霧門的事" }), availability: "locked", requirement_hint: "需要持有霧門通行證" },
        { ...choiceRow("vault", { topicId: "host.vault", label: "密室" }), availability: "hidden" },
        { ...choiceRow("blank", { topicId: "host.blank", label: "沉默的事" }), availability: "locked", requirement_hint: "" },
        { ...choiceRow("dream", { topicId: GENERATED_ID, label: "夢裡的約定" }), availability: "locked", requirement_hint: LONG_HINT },
      ],
    });
    const LOCKED_PICKS = dialogueViewModel(LOCKED_PANEL).picks;
    const tip = (w) => w.find('[data-testid="choice-card-tip"]');
    const description = (row) =>
      (row.attributes("aria-describedby") || "")
        .split(" ")
        .filter(Boolean)
        .map((id) => document.getElementById(id)?.textContent)
        .join(" ");

    it("renders open and locked rows in payload order and never a hidden one", () => {
      const w = mountList({ picks: LOCKED_PICKS });
      expect(labels(w)).toEqual(["渡河的價錢", "霧門的事", "沉默的事", "夢裡的約定", "自由對話", "移動…", "結束對話"]);
      expect(w.text()).not.toContain("密室");
      expect(badges(w).slice(0, 4)).toEqual(["1", "2", "3", "4"]);
      expect(rows(w).map((row) => row.attributes("data-locked") ?? null).slice(0, 4)).toEqual([null, "true", "true", "true"]);
    });

    it("marks a locked row with a padlock and a text name, never aria-disabled", () => {
      const w = mountList({ picks: LOCKED_PICKS });
      const locked = rows(w)[1];
      expect(locked.find('[data-testid="choice-card-lock"]').exists()).toBe(true);
      expect(locked.get('[data-testid="choice-card-lock"]').attributes("aria-hidden")).toBe("true");
      expect(locked.text()).toContain("（尚未解鎖）");
      expect(locked.attributes("aria-disabled")).toBeUndefined();
      expect(rows(w)[0].find('[data-testid="choice-card-lock"]').exists()).toBe(false);
      expect(w.find('[aria-disabled="true"]').exists()).toBe(false);
    });

    it("describes a locked row with its canonical hint, outside the row's name", () => {
      const w = mountList({ picks: LOCKED_PICKS });
      const locked = rows(w)[1];
      expect(description(locked)).toBe("需要持有霧門通行證");
      expect(locked.text()).not.toContain("需要持有霧門通行證");
      // An open row and an empty hint carry no description and no copy.
      expect(rows(w)[0].attributes("aria-describedby")).toBeUndefined();
      expect(rows(w)[2].attributes("aria-describedby")).toBeUndefined();
      expect(w.findAll('[data-testid="choice-card-tip-text"]').map((el) => el.text())).toEqual(["需要持有霧門通行證", LONG_HINT]);
    });

    it("shows the hint for the active locked row while the list holds keyboard focus", async () => {
      const w = mountList({ picks: LOCKED_PICKS });
      expect(tip(w).exists()).toBe(false);
      await key(w, "ArrowDown");
      expect(tip(w).exists()).toBe(true);
      expect(tip(w).text()).toBe("需要持有霧門通行證");
      expect(tip(w).attributes("data-tip-source")).toBe("focus");
      expect(tip(w).attributes("aria-hidden")).toBe("true");
      expect(tip(w).attributes("tabindex")).toBeUndefined();
      expect(w.findAll("[tabindex]")).toHaveLength(1);
      // An empty hint produces no tooltip container at all.
      await key(w, "ArrowDown");
      expect(tip(w).exists()).toBe(false);
      // A long hint shows in full.
      await key(w, "ArrowDown");
      expect(tip(w).text()).toBe(LONG_HINT);
      // Leaving the list hides it.
      list(w).element.blur();
      await nextTick();
      expect(tip(w).exists()).toBe(false);
    });

    it("shows the hint on pointer hover, keyed to the hovered row, and keeps it on the tooltip", async () => {
      const outside = document.createElement("button");
      document.body.appendChild(outside);
      outside.focus();
      wrapper = mount(DialogueChoices, { attachTo: document.body, props: { picks: LOCKED_PICKS, exits: EXITS, localMap: LOCAL_MAP } });
      const w = wrapper;
      await rows(w)[3].trigger("mouseenter");
      expect(tip(w).text()).toBe(LONG_HINT);
      expect(tip(w).attributes("data-tip-source")).toBe("pointer");
      // Resting on the tooltip (a descendant of the card) keeps it.
      await tip(w).trigger("mouseenter");
      expect(tip(w).exists()).toBe(true);
      await rows(w)[0].trigger("mouseenter");
      expect(tip(w).exists()).toBe(false);
      await rows(w)[1].trigger("mouseenter");
      expect(tip(w).text()).toBe("需要持有霧門通行證");
      await list(w).trigger("mouseleave");
      expect(tip(w).exists()).toBe(false);
      expect(document.activeElement).toBe(outside);
    });

    it("drops a pointer hint whose row a refresh removes", async () => {
      const w = mountList({ picks: LOCKED_PICKS });
      list(w).element.blur();
      await rows(w)[1].trigger("mouseenter");
      expect(tip(w).exists()).toBe(true);
      await w.setProps({ picks: LOCKED_PICKS.filter((pick) => pick.topicId !== "host.gate") });
      expect(tip(w).exists()).toBe(false);
    });

    it("Escape dismisses a keyboard hint and stops there; a pointer hint lets Escape through", async () => {
      const w = mountList({ picks: LOCKED_PICKS });
      await key(w, "ArrowDown");
      expect(tip(w).exists()).toBe(true);
      await key(w, "Escape");
      expect(tip(w).exists()).toBe(false);
      expect(documentKeys).not.toContain("Escape");
      // The next target shows again.
      await key(w, "ArrowDown");
      await key(w, "ArrowDown");
      expect(tip(w).text()).toBe(LONG_HINT);
      await rows(w)[1].trigger("mouseenter");
      expect(tip(w).attributes("data-tip-source")).toBe("pointer");
      await key(w, "Escape");
      expect(tip(w).exists()).toBe(false);
      expect(documentKeys).toContain("Escape");
    });

    it("activates a locked row by Enter, digit, and pointer with its full committed payload", async () => {
      const before = vi.fn();
      const w = mountList({ picks: LOCKED_PICKS, beforeActivate: before });
      await key(w, "ArrowDown");
      await key(w, "Enter");
      await key(w, "4");
      await rows(w)[2].trigger("click");
      expect(before).toHaveBeenCalledTimes(3);
      const picked = w.emitted("pick").map(([pick]) => pick);
      expect(picked.map((pick) => pick.topicId)).toEqual(["host.gate", GENERATED_ID, "host.blank"]);
      expect(picked[1].payload).toEqual({ npc_id: 41, topic_id: GENERATED_ID, context_id: "ctx-1" });
      expect(picked[1].payload.topic_id).toHaveLength(2048);
    });

    it("the dispatch lock suppresses a locked row too", async () => {
      const w = mountList({ picks: LOCKED_PICKS, locked: true });
      await key(w, "2");
      await rows(w)[1].trigger("click");
      expect(w.emitted("pick")).toBeUndefined();
    });

    it("keeps all sixteen declared topics reachable by keyboard and scrolls each into view", async () => {
      const many = dialogueViewModel(
        v3Panel({
          choices: Array.from({ length: 16 }, (_, index) => ({
            ...choiceRow(`t${index}`, { topicId: `host.t${index}`, label: `話題${index + 1}` }),
            ...(index % 3 === 0 ? { availability: "locked", requirement_hint: `需要條件${index}` } : {}),
          })),
        }),
      ).picks;
      const scrolled = [];
      const original = Element.prototype.scrollIntoView;
      Element.prototype.scrollIntoView = function scrollIntoView() {
        scrolled.push(this.id);
      };
      try {
        const w = mountList({ picks: many });
        expect(rows(w)).toHaveLength(19);
        for (let index = 1; index < 16; index += 1) {
          await key(w, "ArrowDown");
          await nextTick();
        }
        expect(activeRow(w)).toBe(rows(w)[15].element);
        expect(tip(w).text()).toBe("需要條件15");
        expect(scrolled).toContain(rows(w)[15].element.id);
        await key(w, "Home");
        await nextTick();
        expect(activeRow(w)).toBe(rows(w)[0].element);
      } finally {
        Element.prototype.scrollIntoView = original;
      }
    });
  });
  // authored-dialogue-unread-notices: the server's unread marker is a pip in
  // the padlock's slot plus text; the lock always wins.
  describe("unread topics", () => {
    const UNREAD_PANEL = v3Panel({
      choices: [
        { ...choiceRow("fare", { topicId: "host.fare", label: "渡河的價錢" }), unread: true },
        choiceRow("smell", { topicId: "host.smell", label: "河邊的氣味" }),
        { ...choiceRow("gate", { topicId: "host.gate", label: "霧門的事" }), availability: "locked", requirement_hint: "需要信物", unread: true },
      ],
    });
    const UNREAD_PICKS = dialogueViewModel(UNREAD_PANEL).picks;

    it("draws a pip and the text name on an unread open row only", () => {
      const w = mountList({ picks: UNREAD_PICKS });
      const [fare, smell, gate] = rows(w);
      expect(fare.attributes("data-unread")).toBe("true");
      expect(fare.get('[data-testid="choice-card-unread"]').attributes("aria-hidden")).toBe("true");
      expect(fare.text()).toContain("（未讀）");
      expect(smell.attributes("data-unread")).toBeUndefined();
      expect(smell.find('[data-testid="choice-card-unread"]').exists()).toBe(false);
      expect(smell.text()).not.toContain("（未讀）");
      // The lock marker wins: a locked row shows only its padlock.
      expect(gate.attributes("data-unread")).toBeUndefined();
      expect(gate.find('[data-testid="choice-card-unread"]').exists()).toBe(false);
      expect(gate.find('[data-testid="choice-card-lock"]').exists()).toBe(true);
      expect(gate.text()).not.toContain("（未讀）");
    });

    it("keeps the active row and focus when a refresh marks a topic read", async () => {
      const w = mountList({ picks: UNREAD_PICKS });
      await key(w, "ArrowDown");
      const before = activeRow(w).getAttribute("data-row-key");
      const read = v3Panel({
        choices: UNREAD_PANEL.choices.map((choice) => ({ ...choice, unread: false })),
      });
      await w.setProps({ picks: dialogueViewModel(read).picks });
      expect(activeRow(w).getAttribute("data-row-key")).toBe(before);
      expect(document.activeElement).toBe(list(w).element);
      expect(w.find('[data-testid="choice-card-unread"]').exists()).toBe(false);
    });
  });
});
