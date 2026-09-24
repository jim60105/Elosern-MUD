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
    expect(w.get('[data-testid="connection-state"]').text()).toBe("○ 未連線");
    expect(w.get('[data-testid="narrative-feed"]')).toBeTruthy();
    expect(w.get('[data-testid="narrative-fulllog-control"]')).toBeTruthy();
    // webclient-collapsible-command-line: the command line starts collapsed
    // (`data-expanded="false"`), its ⌨ toggle is in `#band-message` with
    // `aria-expanded="false"`, and `#inputfield` stays in the DOM.
    expect(w.get('[data-testid="command-line"]').exists()).toBe(true);
    expect(w.find('textarea#inputfield').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-command-line"]').attributes("data-expanded")).toBe("false");
    const toggle = w.get('[data-testid="anchor-band-message"] [data-testid="command-line-toggle"]');
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(toggle.attributes("aria-controls")).toBe("command-line-bar");
    expect(w.get('[data-testid="connect-overlay"]').attributes("data-status")).toBe("connecting");
    expect(w.get("#elosern-action-live").attributes("aria-live")).toBe("polite");
    expect(w.get("#elosern-offline-overlay").attributes("data-visible")).toBe("false");
    // The cinematic stage (H1): the full-bleed root carries the mode attribute
    // and the named anchors; the top band carries the brand + meta pill.
    expect(w.get('[data-testid="elosern-stage"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-place"] [data-testid="place-card"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-vitals"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-map"]').exists()).toBe(true);
    expect(w.find('[data-testid="anchor-hud-left"]').exists()).toBe(false);
    expect(w.find('[data-testid="anchor-hud-right"]').exists()).toBe(false);
    expect(w.get('[data-testid="stage-band"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-band-message"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-band-command"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-actor-left"]').exists()).toBe(true);
    expect(w.get('[data-testid="anchor-actor-right"]').exists()).toBe(true);
    expect(w.find('[data-testid="anchor-feed"]').exists()).toBe(false);
    expect(w.find('[data-testid="anchor-dock"]').exists()).toBe(false);
    // The narrative caption lives in the band's message region.
    expect(w.get('[data-testid="anchor-band-message"] [data-testid="narrative-feed"]').exists()).toBe(true);
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
    for (const selector of ['[data-anchor="vitals"]', '[data-anchor="map"]']) {
      const panel = w.get(selector);
      expect(panel.element.children.length).toBe(0);
      expect(panel.text().trim()).toBe("");
    }
    expect(w.get("#elosern-action-live").text().trim()).toBe("");
  });

  // webclient-retire-redundant-hud: bound letters retired, unclaimed keys do not insert or focus
  it("in exploration mode, a keydown of g on a non-editable target leaves #inputfield empty and does not move focus", async () => {
    const w = mountShell({ mode: "exploration" });
    const input = w.get("textarea#inputfield");
    const target = w.get('[data-testid="narrative-fulllog-control"]');
    target.element.focus();
    expect(document.activeElement).toBe(target.element);

    pressKey(window, "g");
    await w.vm.$nextTick();

    expect(input.element.value).toBe("");
    expect(document.activeElement).toBe(target.element, "focus remains on the target");
    expect(w.emitted("submit-command")).toBeUndefined();
  });

  it("unclaimed keys and modified letters fall through untouched", async () => {
    const w = mountShell({ mode: "exploration" });
    pressKey(window, "x");
    pressKey(window, "g", { ctrlKey: true });
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("");
  });

  it("`/` focuses the command field; Escape returns focus to the action dock; slash stays literal in the field", async () => {
    // webclient-collapsible-command-line (design D2): `focusCommandField`
    // expands the row (`data-expanded="true"`) and after `nextTick` focuses
    // `#inputfield`; Escape from the focused field routes `focus-parent` →
    // `releaseCommandField(true)` → `#action-dock` focus rescue and collapses.
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    const w = mount(AppShell, {
      attachTo: host,
      slots: { "action-dock": () => h(ActionDock) },
    });
    wrapper = w;

    const anchor = w.get('[data-testid="anchor-command-line"]');
    expect(anchor.attributes("data-expanded")).toBe("false");

    // `/` from the dock (a non-editable target) prevents a literal slash; the
    // exposed `focusCommandField` API expands the row and focuses the field.
    pressKey(window, "/");
    await w.vm.$nextTick();
    await w.vm.focusCommandField();
    await w.vm.$nextTick();
    expect(anchor.attributes("data-expanded")).toBe("true");
    expect(w.get('[data-testid="command-line-toggle"]').attributes("aria-expanded")).toBe("true");
    let input = w.get("textarea#inputfield");
    expect(document.activeElement).toBe(input.element);

    // Escape from the focused field: nothing is sent, focus returns to the
    // action dock, and the command line collapses while the field stays in DOM.
    pressKey(input.element, "Escape");
    await w.vm.$nextTick();
    expect(document.activeElement).toBe(document.getElementById("action-dock"));
    expect(anchor.attributes("data-expanded")).toBe("false");
    expect(w.find("textarea#inputfield").exists()).toBe(true);

    // Re-expand and focus the field so the literal-slash step's premise
    // (an editable control is focused) holds after the Escape rescue.
    await w.vm.focusCommandField();
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

  it("emits submit-command, collapses, and focuses the dock on an accepted send; stays expanded with text when locked", async () => {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    const w = mount(AppShell, {
      attachTo: host,
      props: { connected: true, mutationsLocked: false },
      slots: { "action-dock": () => h(ActionDock) },
    });
    wrapper = w;
    const anchor = w.get('[data-testid="anchor-command-line"]');
    const input = w.get("textarea#inputfield");
    await w.vm.focusCommandField();
    await w.vm.$nextTick();
    expect(anchor.attributes("data-expanded")).toBe("true");
    input.element.value = "look";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();

    const emitted = w.emitted("submit-command");
    expect(emitted).toHaveLength(1);
    expect(emitted[0]).toEqual(["look"]);
    expect(input.element.value).toBe("");
    expect(anchor.attributes("data-expanded")).toBe("false");
    expect(document.activeElement).toBe(document.getElementById("action-dock"));

    // A locked Enter keeps the line expanded, keeps focus, and keeps the draft.
    await w.setProps({ mutationsLocked: true });
    await w.vm.focusCommandField();
    await w.vm.$nextTick();
    input.element.value = "talk 老周";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();
    expect(anchor.attributes("data-expanded")).toBe("true");
    expect(input.element.value).toBe("talk 老周");
    expect(document.activeElement).toBe(input.element);
  });

  it("the ⌨ toggle expands and focuses the field, then collapses while leaving focus on the toggle", async () => {
    const w = mountShell({ connected: true });
    const anchor = w.get('[data-testid="anchor-command-line"]');
    const toggle = w.get('[data-testid="command-line-toggle"]');
    const input = w.get("textarea#inputfield");
    expect(anchor.attributes("data-expanded")).toBe("false");

    toggle.element.focus();
    await toggle.trigger("click");
    await w.vm.$nextTick();
    expect(anchor.attributes("data-expanded")).toBe("true");
    expect(toggle.attributes("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(input.element);

    toggle.element.focus();
    await toggle.trigger("click");
    await w.vm.$nextTick();
    expect(anchor.attributes("data-expanded")).toBe("false");
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(toggle.element);
  });

  it("entering creation collapses an expanded command line and rescues focus to the dock", async () => {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    const w = mount(AppShell, {
      attachTo: host,
      props: { mode: "exploration" },
      slots: { "action-dock": () => h(ActionDock) },
    });
    wrapper = w;
    const anchor = w.get('[data-testid="anchor-command-line"]');
    await w.vm.focusCommandField();
    await w.vm.$nextTick();
    expect(anchor.attributes("data-expanded")).toBe("true");
    expect(document.activeElement).toBe(w.get("textarea#inputfield").element);

    await w.setProps({ mode: "creation" });
    await w.vm.$nextTick();
    expect(anchor.attributes("data-expanded")).toBe("false");
    expect(document.activeElement).toBe(document.getElementById("action-dock"));

    // A focusCommandField request while in creation is ignored so returning to
    // exploration starts collapsed.
    await w.vm.focusCommandField();
    await w.setProps({ mode: "exploration" });
    await w.vm.$nextTick();
    expect(anchor.attributes("data-expanded")).toBe("false");
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
