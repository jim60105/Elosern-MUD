import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import CommandLine from "../components/CommandLine.vue";

function pressKey(target, key, options = {}) {
  target.dispatchEvent(
    new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...options }),
  );
}

describe("CommandLine (H5, webclient-hud-05-overlays-and-command-line)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountLine(props = {}) {
    const host = document.createElement("div");
    host.className = "elosern-stage";
    host.setAttribute("data-elosern-mode", props.mode || "exploration");
    document.body.appendChild(host);
    wrapper = mount(CommandLine, { attachTo: host, props });
    return wrapper;
  }

  it("the field is present and focusable with no opening action (task 2.6)", () => {
    const w = mountLine();
    const input = w.get("textarea#inputfield");
    expect(input.element.closest(".inputfieldwrapper")).not.toBeNull();
    w.vm.focusField();
    expect(document.activeElement).toBe(input.element);
    // No entry control, no aria-expanded anywhere in the bar (task 2.6).
    expect(w.findAll("[aria-expanded]").length).toBe(0);
  });

  it("sends exactly one command on Enter and clears the field", async () => {
    const w = mountLine();
    const input = w.get("textarea#inputfield");
    input.element.value = "  look  ";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();
    expect(w.emitted("submit")).toHaveLength(1);
    expect(w.emitted("submit")[0]).toEqual(["  look  "]);
    expect(input.element.value).toBe("");
  });

  it("never submits an empty or whitespace-only entry", async () => {
    const w = mountLine();
    const input = w.get("textarea#inputfield");
    input.element.value = "   ";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();
    expect(w.emitted("submit")).toBeUndefined();
  });

  it("keeps Shift+Enter as a newline (no submit)", async () => {
    const w = mountLine();
    const input = w.get("textarea#inputfield");
    input.element.value = "line one";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter", { shiftKey: true });
    await w.vm.$nextTick();
    expect(w.emitted("submit")).toBeUndefined();
    expect(input.element.value).toBe("line one");
  });

  it("a rejected send preserves the typed speech (offline or locked)", async () => {
    const w = mountLine({ connected: false, mutationsLocked: true });
    const input = w.get("textarea#inputfield");
    input.element.value = "talk 老周";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();
    expect(w.emitted("submit")).toHaveLength(1);
    expect(input.element.value).toBe("talk 老周", "rejected send keeps the speech");
  });

  it("walks the command history with keys and buttons, preserving the draft (task 2.6)", async () => {
    const history = ["look", "北", "talk 老周"];
    const w = mountLine({ history });
    const input = w.get("textarea#inputfield");
    input.element.value = "draft";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));

    pressKey(input.element, "ArrowUp");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("talk 老周");
    pressKey(input.element, "ArrowUp");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("北");
    // The pointer path: the 下一筆 button drives the same walk state.
    w.get('[data-testid="command-line-history-down"]').trigger("click");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("talk 老周");
    w.get('[data-testid="command-line-history-down"]').trigger("click");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("draft", "the unsent draft is restored past the most recent entry");
    // Neither path submits.
    expect(w.emitted("submit")).toBeUndefined();
  });

  it("emits focus-parent on Escape (the field's own release path)", async () => {
    const w = mountLine();
    pressKey(w.get("textarea#inputfield").element, "Escape");
    await w.vm.$nextTick();
    expect(w.emitted("focus-parent")).toHaveLength(1);
  });

  it("a slash typed in the field is ordinary text (never claimed)", async () => {
    const w = mountLine();
    const input = w.get("textarea#inputfield");
    pressKey(input.element, "/");
    await w.vm.$nextTick();
    // The component's keydown handler ignores "/": it is literal text input.
    expect(w.emitted("submit")).toBeUndefined();
    expect(w.emitted("focus-parent")).toBeUndefined();
  });

  it("the quick-word chips prepare without submitting (task 4.5)", async () => {
    const w = mountLine({ mode: "exploration" });
    const input = w.get("textarea#inputfield");
    const chip = w.get('[data-testid="quick-word-chip-看"]');
    expect(chip.exists()).toBe(true);
    chip.trigger("click");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("看 ", "the chip's label plus a trailing space");
    expect(document.activeElement).toBe(input.element, "focus moves to the field");
    expect(w.emitted("submit")).toBeUndefined();
  });

  it("chip sets follow the mode (task 4.5): combat chips are absent in exploration", async () => {
    const w = mountLine({ mode: "exploration" });
    // jsdom cannot resolve the compound mode-gate selector
    // (`.elosern-stage[data-elosern-mode="exploration"] .qwc-combat`), so
    // assert the mechanism: the driver attribute, the in-DOM (gated) group,
    // and the loaded CSSOM rule that hides it.
    const host = document.querySelector(".elosern-stage");
    expect(host.getAttribute("data-elosern-mode")).toBe("exploration");
    const combatGroup = w.get('[data-testid="quick-word-chips-combat"]');
    expect(combatGroup.exists()).toBe(true, "the inactive group is gated, not removed");
    const ruleLoaded = Array.from(document.styleSheets).some((sheet) => {
      try {
        return Array.from(sheet.cssRules || []).some(
          (rule) =>
            rule.selectorText &&
            rule.selectorText.includes('data-elosern-mode="exploration"] .qwc-combat'),
        );
      } catch {
        return false;
      }
    });
    expect(ruleLoaded).toBe(true, "the mode-gate CSS rule is loaded and hides the group");
  });

  it("the prompt line honors the text-to-HTML preference (task 7.7)", () => {
    const prompt = '<span class="color-111">></span> ';
    const w = mountLine({ prompt, textToHtml: true });
    const html = w.get('[data-testid="command-line-prompt"]');
    expect(html.find(".color-111").exists()).toBe(true);

    const w2 = mount(CommandLine, {
      props: { prompt, textToHtml: false },
    });
    const literal = w2.get('[data-testid="command-line-prompt"]');
    expect(literal.find(".color-111").exists()).toBe(false, "off: literal text, no pipeline");
    w2.unmount();
  });
});
