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
    expect(w.attributes("id")).toBe("command-line-bar");
    const input = w.get("textarea#inputfield");
    expect(input.element.closest(".inputfieldwrapper")).not.toBeNull();
    w.vm.focusField();
    expect(document.activeElement).toBe(input.element);
    expect(w.findAll("[aria-expanded]").length).toBe(0);
  });

  it("sends exactly one command on Enter, emits sent, and clears the field", async () => {
    const w = mountLine();
    const input = w.get("textarea#inputfield");
    input.element.value = "  look  ";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();
    expect(w.emitted("submit")).toHaveLength(1);
    expect(w.emitted("submit")[0]).toEqual(["  look  "]);
    expect(w.emitted("sent")).toHaveLength(1);
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

  it.each([
    ["offline", { connected: false, mutationsLocked: false, inFlight: false }],
    ["mutationsLocked", { connected: true, mutationsLocked: true, inFlight: false }],
    ["inFlight", { connected: true, mutationsLocked: false, inFlight: true }],
  ])("a rejected send (%s) preserves the typed speech and does not emit sent", async (_label, props) => {
    const w = mountLine(props);
    const input = w.get("textarea#inputfield");
    input.element.value = "talk 老周";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();
    expect(w.emitted("submit")).toHaveLength(1);
    expect(w.emitted("sent")).toBeUndefined();
    expect(input.element.value).toBe("talk 老周", "rejected send keeps the speech");
    w.unmount();
    wrapper = null;
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

  // webclient-align-02-quickbar-shortcuts: the truthful hint + Tab completion.
  it("the hint cluster states exactly the draft's history + completion affordance", () => {
    const w = mountLine();
    expect(w.get(".hint").text()).toBe("↑↓ 歷史 · Tab 補全");
  });

  function pressTab(w, opts = {}) {
    const input = w.get("textarea#inputfield");
    pressKey(input.element, "Tab", opts);
    return input;
  }

  function typeInto(w, text) {
    const input = w.get("textarea#inputfield");
    input.element.value = text;
    input.trigger("input");
    return input;
  }

  it("Tab completes a unique candidate with the caret at its end", async () => {
    const w = mountLine({ completionCandidates: ["西風酒館"] });
    const input = typeInto(w, "西風");
    input.element.focus();
    await w.vm.$nextTick();
    pressTab(w);
    await w.vm.$nextTick();
    expect(input.element.value).toBe("西風酒館");
    expect(document.activeElement).toBe(input.element, "focus never leaves the field");
  });

  it("Tab completes to the longest common prefix then cycles; Shift+Tab reverses", async () => {
    const w = mountLine({
      history: ["cast wind_blade", "cast wind_wall"],
      completionCandidates: ["西風酒館", "北岸大道"],
    });
    typeInto(w, "cast w");
    await w.vm.$nextTick();
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("cast wind_");
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("cast wind_blade");
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("cast wind_wall");
    // wraps back to the LCP rung
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("cast wind_");
    // Shift+Tab steps back onto the previous candidate
    pressKey(w.get("textarea#inputfield").element, "Tab", { shiftKey: true });
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("cast wind_wall");
  });

  it("Tab is stable across candidate kinds: panel candidate joins the set", async () => {
    const w = mountLine({ completionCandidates: ["south"] });
    typeInto(w, "sou");
    await w.vm.$nextTick();
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("south");
  });

  it("a manual edit resets the cycle and re-derives from the new draft", async () => {
    const w = mountLine({
      history: ["cast wind_blade", "cast wind_wall"],
    });
    typeInto(w, "cast w");
    await w.vm.$nextTick();
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("cast wind_");
    typeInto(w, "西");
    await w.vm.$nextTick();
    pressTab(w);
    await w.vm.$nextTick();
    // no candidate matches 西 — the field is untouched by the stale cycle
    expect(w.get("textarea#inputfield").element.value).toBe("西");
  });

  it("a candidate-source change drops the in-flight cycle", async () => {
    // The draft stays untouched, but the stale cycle must not keep offering
    // candidates the committed sources no longer contain.
    const w = mountLine({
      history: ["cast wind_blade", "cast wind_wall"],
      completionCandidates: ["西風酒館", "北岸大道"],
    });
    typeInto(w, "cast w");
    await w.vm.$nextTick();
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("cast wind_");
    // The room changes: the exit rows disappear and history is replaced.
    w.setProps({
      history: ["look"],
      completionCandidates: [],
    });
    await w.vm.$nextTick();
    // Re-deriving from the retained draft finds no candidate -> the field is
    // left alone (a surviving stale cycle would instead re-offer wind_wall).
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("cast wind_");
  });

  it("an unmatched draft leaves text and focus unchanged (Tab never escapes)", async () => {
    const w = mountLine({ completionCandidates: ["西風酒館"] });
    const input = typeInto(w, "zzz");
    input.element.focus();
    await w.vm.$nextTick();
    pressTab(w);
    await w.vm.$nextTick();
    expect(input.element.value).toBe("zzz");
    expect(document.activeElement).toBe(input.element, "Tab never moves focus out");
  });

  it("Tab completion matches the text before the caret", async () => {
    const w = mountLine({ completionCandidates: ["西風酒館"] });
    const input = typeInto(w, "西風酒館 殘尾");
    input.element.setSelectionRange(2, 2);
    pressTab(w);
    await w.vm.$nextTick();
    expect(w.get("textarea#inputfield").element.value).toBe("西風酒館");
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

  it("renders no utility-cluster or overlay/drawer opener controls in the bar", () => {
    const w = mountLine();
    expect(w.find(".cmdutil").exists()).toBe(false);
    expect(w.find('[data-testid="gallery-opener"]').exists()).toBe(false);
    expect(w.find('[data-testid="command-line-lineage"]').exists()).toBe(false);
    expect(w.find('[data-testid="command-line-lore"]').exists()).toBe(false);
    expect(w.find('[data-testid="command-line-codex"]').exists()).toBe(false);
    expect(w.find('[data-testid="command-line-settings"]').exists()).toBe(false);
    expect(w.find('[data-testid="command-line-help"]').exists()).toBe(false);
  });
});
