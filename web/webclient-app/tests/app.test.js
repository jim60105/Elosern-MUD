import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
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
    expect(root.attributes("data-elosern-stage")).toBe("showcase-core");
    expect(root.attributes("data-elosern-mode")).toBe("explore");
    expect(w.get('[data-testid="topbar"]')).toBeTruthy();
    expect(w.get('[data-testid="connection-state"]').text()).toBe("○ 未連線");
    expect(w.get('[data-testid="narrative-feed"]')).toBeTruthy();
    const drawer = w.get('[data-testid="command-drawer"]');
    expect(drawer.attributes("data-open")).toBe("false");
    expect(w.get('[data-testid="command-drawer-entry"]').attributes("aria-expanded")).toBe("false");
    expect(w.get('[data-testid="connect-overlay"]').attributes("data-status")).toBe("connecting");
    expect(w.get("#elosern-action-live").attributes("aria-live")).toBe("polite");
    expect(w.get("#elosern-offline-overlay").attributes("data-visible")).toBe("false");
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
    // B1 has no B2-B4 panel read models yet: the empty side panels render
    // nothing (no children, no text), so no surface invents data.
    const w = mountShell();
    for (const selector of [".app-shell__panel-left", ".app-shell__panel-right"]) {
      const panel = w.get(selector);
      expect(panel.element.children.length).toBe(0);
      expect(panel.text().trim()).toBe("");
    }
    expect(w.get("#elosern-action-live").text().trim()).toBe("");
  });

  it("toggles the drawer with `/` and focuses the field; Escape returns focus to the feed; slash stays literal in the field", async () => {
    const w = mountShell();
    pressKey(window, "/");
    await w.vm.$nextTick();
    expect(w.get('[data-testid="command-drawer"]').attributes("data-open")).toBe("true");
    let input = w.get("textarea#inputfield");
    expect(document.activeElement).toBe(input.element);

    pressKey(input.element, "Escape");
    await w.vm.$nextTick();
    expect(w.get('[data-testid="command-drawer"]').attributes("data-open")).toBe("false");
    expect(document.activeElement).toBe(w.get('[data-testid="narrative-feed"]').element);

    // Slash stays literal text inside the focused field (the shell does not
    // claim it there). jsdom performs no default text insertion, so the
    // keystroke lands the way a browser would: value plus input event. The
    // drawer must stay open — the shell must not toggle — and focus must
    // stay in the field. Re-fetch the field: the row remounts on re-open.
    pressKey(window, "/");
    await w.vm.$nextTick();
    input = w.get("textarea#inputfield");
    input.element.value = "/";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    await w.vm.$nextTick();
    expect(input.element.value).toBe("/");
    expect(w.get('[data-testid="command-drawer"]').attributes("data-open")).toBe("true");
    expect(document.activeElement).toBe(input.element);
  });

  it("emits exactly one submit-command per deliberate send", async () => {
    const w = mountShell();
    w.get('[data-testid="command-drawer-entry"]').trigger("click");
    await w.vm.$nextTick();
    const input = w.get("textarea#inputfield");
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
