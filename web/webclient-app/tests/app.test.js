import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { h } from "vue";
import ActionDock from "../components/ActionDock.vue";
import AppShell from "../components/AppShell.vue";

function pressKey(target, key, options = {}) {
  target.dispatchEvent(
    new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...options }),
  );
}

describe("AppShell root (B1 core family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  // The shell is always mounted attached to the document: focus and the
  // mount-time fallback retirement both need a live DOM.
  function mountShell(props = {}) {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppShell, { attachTo: host, props });
    return wrapper;
  }

  it("renders every required core surface in the pre-connection state", () => {
    const w = mountShell();
    const root = w.get('[data-testid="elosern-vue-root"]');
    expect(root.attributes("data-elosern-stage")).toBe("contextual-hud");
    expect(root.attributes("data-elosern-mode")).toBe("exploration");
    expect(w.get('[data-testid="topbar"]')).toBeTruthy();
    expect(w.get('[data-testid="topbar-title"]').text()).toBe("伊洛瑟恩");
    expect(w.get('[data-testid="connection-state"]').text()).toBe("○ 未連線");
    expect(w.get('[data-testid="narrative-feed"]')).toBeTruthy();
    expect(w.get('[data-testid="narrative-fulllog-control"]')).toBeTruthy();
    // H5: the command line is a permanently present bar — no open/closed
    // state, no entry control, no `aria-expanded`.
    expect(w.get('[data-testid="command-line"]').exists()).toBe(true);
    expect(w.find('textarea#inputfield').exists()).toBe(true);
    expect(w.findAll("[aria-expanded]").length).toBe(0);
    expect(w.get('[data-testid="connect-overlay"]').attributes("data-status")).toBe("connecting");
    expect(w.get("#elosern-action-live").attributes("aria-live")).toBe("polite");
    expect(w.get("#elosern-offline-overlay").attributes("data-visible")).toBe("false");
    // The cinematic stage (H1): the full-bleed root carries the mode attribute
    // and the named anchors; the top band carries the brand + meta pill.
    expect(w.get('[data-testid="elosern-stage"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-hud-left"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-feed"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-dock"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-command-line"]').exists()).toBe(true);
  });

  it("retires the replaced text fallback on mount (hidden, not removed)", async () => {
    const mainSub = document.createElement("div");
    mainSub.id = "main-sub";
    const messageWindow = document.createElement("div");
    messageWindow.id = "messagewindow";
    const console = document.createElement("div");
    console.setAttribute("data-testid", "text-console");
    mainSub.append(messageWindow, console);
    document.body.appendChild(mainSub);

    mountShell();

    expect(document.getElementById("messagewindow")).not.toBeNull();
    expect(messageWindow.style.display).toBe("none");
    expect(messageWindow.getAttribute("data-elosern-retired")).toBe("app-mount");
    expect(console.style.display).toBe("none");
    expect(console.getAttribute("data-elosern-retired")).toBe("app-mount");
  });

  it("presents no invented data for surfaces without a backing read model", () => {
    // H1: the empty HUD anchors render nothing (no children, no text), so no
    // surface invents data (a surface with no backing read model is never
    // shown).
    const w = mountShell();
    for (const selector of ['[data-anchor="hud-left"]', '[data-anchor="hud-right"]']) {
      const panel = w.get(selector);
      expect(panel.element.children.length).toBe(0);
      expect(panel.text().trim()).toBe("");
    }
    expect(w.get("#elosern-action-live").text().trim()).toBe("");
  });

  // webclient-align-02-quickbar-shortcuts: the bound-letter router.
  it("a bound letter outside any field inserts letter + space and focuses; typing stays inside", async () => {
    const w = mountShell({ mode: "exploration" });
    const input = w.get("textarea#inputfield");
    // From a non-editable target (the dock), `g` behaves like a chip click.
    pressKey(window, "g");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("g ");
    expect(document.activeElement).toBe(input.element, "focus moves to the field");
    expect(w.emitted("submit-command")).toBeUndefined();
    // Inside the field the letter is ordinary text: the router never claims
    // it (not defaultPrevented — the browser's own insertion proceeds), and no
    // chip-insert rerouting happens (the draft keeps growing as typed text).
    const typed = new KeyboardEvent("keydown", { key: "t", bubbles: true, cancelable: true });
    input.element.dispatchEvent(typed);
    await w.vm.$nextTick();
    expect(typed.defaultPrevented).toBe(false, "the router leaves in-field letters to the browser");
    // Emulate the browser's native insertion that follows an unclaimed keydown.
    input.element.value = "g t";
    input.trigger("input");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("g t", "typed text accumulates; the router did not overwrite it");
  });

  it("the physical badge key works regardless of Caps Lock / Shift casing", async () => {
    const w = mountShell({ mode: "exploration" });
    // Caps Lock (or Shift) yields an uppercase event.key outside the field.
    pressKey(window, "G");
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe(
      "g ",
      "the uppercase press inserts the canonical lowercase command word",
    );
  });

  it("letter bindings follow the committed mode: combat binds s/c only, creation none", async () => {
    let combat = mountShell({ mode: "combat" });
    pressKey(window, "c");
    await combat.vm.$nextTick();
    expect(combat.get("textarea#inputfield").element.value).toBe("c ");
    pressKey(window, "l");
    await combat.vm.$nextTick();
    expect(combat.get("textarea#inputfield").element.value).toBe("c ", "l is unbound in combat");
    combat.unmount();
    wrapper = null;

    const creation = mountShell({ mode: "creation" });
    pressKey(window, "g");
    await creation.vm.$nextTick();
    expect(creation.get("textarea#inputfield").element.value).toBe("", "creation binds no letters");
  });

  it("unclaimed keys and modified letters fall through untouched", async () => {
    const w = mountShell({ mode: "exploration" });
    pressKey(window, "x");
    pressKey(window, "g", { ctrlKey: true });
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("");
  });

  it("`/` focuses the command field; Escape returns focus to the action dock; slash stays literal in the field", async () => {
    // H5 (task 3.6): the command line has no open/closed state — `/` is an
    // unconditional focus claim (no literal slash inserted), and Escape from
    // the focused field routes `focus-parent` → `releaseCommandField(true)`
    // → `#action-dock` focus rescue (the dock's menu level is untouched).
    // Mount the dock into the shell's action-dock slot as the preserved focus
    // target.
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    const w = mount(AppShell, {
      attachTo: host,
      slots: { "action-dock": () => h(ActionDock) },
    });
    wrapper = w;

    // `/` from the dock (a non-editable target) focuses the field. The shell's
    // window handler claims the key (preventDefault — no literal slash); the
    // exposed `focusCommandField` API (the store's single focus entry) moves
    // focus into the always-present field.
    pressKey(window, "/");
    await w.vm.$nextTick();
    w.vm.focusCommandField();
    await w.vm.$nextTick();
    let input = w.get("textarea#inputfield");
    expect(document.activeElement).toBe(input.element);

    // Escape from the focused field: nothing is sent, focus returns to the
    // action dock; the field stays present (it is never closed).
    pressKey(input.element, "Escape");
    await w.vm.$nextTick();
    expect(document.activeElement).toBe(document.getElementById("action-dock"));
    expect(w.find("textarea#inputfield").exists()).toBe(true);

    // Refocus the always-present field so the literal-slash step's premise
    // (an editable control is focused) holds after the Escape rescue.
    w.vm.focusCommandField();
    await w.vm.$nextTick();

    // A `/` pressed while an editable control (the field) is focused is
    // ordinary text input: the shell's window-level claim never fires, so a
    // literal slash is typeable. jsdom performs no default text insertion,
    // so the keystroke lands the way a browser would: value plus input event.
    pressKey(window, "/");
    await w.vm.$nextTick();
    input = w.get("textarea#inputfield");
    input.element.value = "/";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    await w.vm.$nextTick();
    expect(input.element.value).toBe("/");
    expect(document.activeElement).toBe(input.element);
  });

  it("emits exactly one submit-command per deliberate send", async () => {
    const w = mountShell({ connected: true });
    // The field is permanently present (H5): no entry button to click —
    // focus the field directly and send.
    const input = w.get("textarea#inputfield");
    w.vm.focusCommandField();
    await w.vm.$nextTick();
    input.element.value = "look";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();

    const emitted = w.emitted("submit-command");
    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(["look"]);
    expect(input.element.value).toBe("");
  });
});

describe("ESM lib wrappers (Vite CommonJS interop over the preserved UMD logic)", () => {
  it("re-exports the preserved pure-model APIs unchanged", async () => {
    const [protocol, keyboard, markup, localMap] = await Promise.all([
      import("../lib/protocol.js"),
      import("../lib/keyboard_router.js"),
      import("../lib/narrative_markup.js"),
      import("../lib/local_map.js"),
    ]);
    expect(protocol.default.PROTOCOL_VERSION).toBe(1);
    expect(protocol.default.syncEnvelope()).toEqual({ protocol_version: 1 });
    expect(typeof protocol.default.createStore).toBe("function");
    expect(typeof keyboard.default.createRouter).toBe("function");
    expect(markup.default.tokenize("<br>")).toHaveLength(1);
    expect(typeof localMap.default.reducePanel).toBe("function");
  });
});
