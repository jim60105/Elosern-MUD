import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import CommandDrawer from "../components/CommandDrawer.vue";

function pressKey(target, key, options = {}) {
  target.dispatchEvent(
    new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...options }),
  );
}

describe("CommandDrawer (B1 core family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountDrawer(props = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(CommandDrawer, { attachTo: host, props });
    return wrapper;
  }

  it("defaults closed: only the entry button renders", () => {
    const w = mountDrawer({ open: false });
    expect(w.get('[data-testid="command-drawer"]').attributes("data-open")).toBe("false");
    expect(w.get('[data-testid="command-drawer-entry"]').attributes("aria-expanded")).toBe("false");
    expect(w.find("textarea#inputfield").exists()).toBe(false);
  });

  it("renders the preserved input contract when open", () => {
    const w = mountDrawer({
      open: true,
      prompt: "<span class=\"color-111\">></span> ",
    });
    const input = w.get("textarea#inputfield");
    expect(input.element.closest(".inputfieldwrapper")).not.toBeNull();
    expect(input.attributes("aria-label")).toBe("指令輸入");
    expect(w.get('[data-testid="command-drawer-send"]').text()).toBe(">");
    const prompt = w.get('[data-testid="command-drawer-prompt"]');
    expect(prompt.find("span").classes()).toContain("color-111");
  });

  it("sends exactly one non-empty command on Enter and clears the field", async () => {
    const w = mountDrawer({ open: true });
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
    const w = mountDrawer({ open: true });
    const input = w.get("textarea#inputfield");
    input.element.value = "   ";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter");
    await w.vm.$nextTick();
    expect(w.emitted("submit")).toBeUndefined();
  });

  it("keeps Shift+Enter as a newline (no submit)", async () => {
    const w = mountDrawer({ open: true });
    const input = w.get("textarea#inputfield");
    input.element.value = "line one";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    pressKey(input.element, "Enter", { shiftKey: true });
    await w.vm.$nextTick();
    expect(w.emitted("submit")).toBeUndefined();
    expect(input.element.value).toBe("line one");
  });

  it("walks the command history with ArrowUp/ArrowDown and restores the draft", async () => {
    const w = mountDrawer({ open: true, history: ["look", "北", "talk 老周"] });
    const input = w.get("textarea#inputfield");
    input.element.value = "draft";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));

    pressKey(input.element, "ArrowUp");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("talk 老周");
    pressKey(input.element, "ArrowUp");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("北");
    pressKey(input.element, "ArrowDown");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("talk 老周");
    pressKey(input.element, "ArrowDown");
    await w.vm.$nextTick();
    expect(input.element.value).toBe("draft");
  });

  it("emits focus-parent on Escape (the drawer release path)", async () => {
    const w = mountDrawer({ open: true });
    pressKey(w.get("textarea#inputfield").element, "Escape");
    await w.vm.$nextTick();
    expect(w.emitted("focus-parent")).toHaveLength(1);
  });

  it("exposes focusField so the shell can focus the field after a `/` open", () => {
    const w = mountDrawer({ open: true });
    w.vm.focusField();
    expect(document.activeElement).toBe(w.get("textarea#inputfield").element);
  });
});
