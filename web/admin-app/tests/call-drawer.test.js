import { afterEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import GmCallDrawer from "../components/GmCallDrawer.vue";
import { GmApiError } from "../lib/api.js";
import { CALL_DETAIL } from "../stories/fixtures.js";

const CALL = "0c".repeat(16);

function mountDrawer(get, callId = CALL) {
  const api = { get: vi.fn(get), post: vi.fn() };
  const wrapper = mount(GmCallDrawer, { attachTo: document.body, props: { callId, api } });
  return { wrapper, api };
}

describe("LLM call payload drawer", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("shows the outcome and one tab per attempt with role groups, response and errors", async () => {
    const { wrapper, api } = mountDrawer(async () => CALL_DETAIL);
    await flushPromises();
    expect(api.get).toHaveBeenCalledWith(`/llm/calls/${CALL}`);
    expect(wrapper.attributes("open")).toBeDefined();
    expect(wrapper.attributes("aria-labelledby")).toBe("gm-call-drawer-title");
    expect(document.activeElement?.id).toBe("gm-call-drawer-title");
    const outcome = wrapper.get("[data-testid='gm-call-outcome']");
    expect(outcome.text()).toContain("invalid_output");
    expect(outcome.get(".status-marker").text()).toBe("降級");

    const tabs = wrapper.findAll("[role='tab']");
    expect(tabs.map((tab) => tab.text())).toEqual(["第 1 次 · 失敗", "第 2 次 · 失敗"]);
    expect(tabs[0].attributes("aria-selected")).toBe("true");
    const first = wrapper.get("[data-testid='gm-call-attempt-0']");
    const summaries = first.findAll("details > summary").map((summary) => summary.text());
    expect(summaries[0]).toContain("系統");
    expect(summaries[1]).toContain("使用者");
    expect(first.text()).toContain("旅人：請問北方的森林最近安全嗎？");
    // The structured response rides the shared JSON tree: keys and values are
    // separate nodes, no longer one verbatim JSON string.
    expect(first.text()).toContain("prompt_tokens");
    expect(first.text()).toContain("812");
    expect(first.findAll(".gm-json-tree__key").map((node) => node.text())).toContain("prompt_tokens");
    expect(first.text()).toContain("'reply' is a required property");
    expect(first.text()).toContain("HTTP 200");

    await tabs[0].trigger("keydown", { key: "ArrowRight" });
    expect(tabs[1].attributes("aria-selected")).toBe("true");
    const second = wrapper.get("[data-testid='gm-call-attempt-1']");
    expect(second.isVisible()).toBe(true);
    expect(second.text()).toContain("請求失敗");
    expect(second.text()).toContain("timeout：request timed out after 60s");
    expect(second.text()).toContain("沒有回應內容");
    expect(second.text()).toContain("此次嘗試沒有驗證錯誤");
    await tabs[1].trigger("keydown", { key: "Home" });
    expect(tabs[0].attributes("aria-selected")).toBe("true");
  });

  it("explains outcome-only calls without inventing attempts", async () => {
    const { wrapper } = mountDrawer(async () => ({
      outcome: { ...CALL_DETAIL.outcome, reason: "profile_disabled", attempts: [] },
      exchanges: [],
    }));
    await flushPromises();
    expect(wrapper.findAll("[role='tab']")).toHaveLength(0);
    expect(wrapper.get("[data-testid='gm-call-outcome-only']").text()).toContain("只有結果紀錄");
  });

  it("renders a raw-text response verbatim and an exchange without an outcome", async () => {
    const exchange = { ...CALL_DETAIL.exchanges[0], response: "<html>not json</html>" };
    const { wrapper } = mountDrawer(async () => ({ outcome: null, exchanges: [exchange] }));
    await flushPromises();
    expect(wrapper.get("[data-testid='gm-call-no-outcome']").text()).toContain("沒有結果紀錄");
    expect(wrapper.get("[data-testid='gm-call-attempt-0']").text()).toContain("<html>not json</html>");
    expect(wrapper.find("[data-testid='gm-call-attempt-0'] html").exists()).toBe(false);
  });

  it("shows explicit expired and disabled states", async () => {
    const cases = [
      ["transcript_not_found", 404, "紀錄已過期"],
      ["transcript_disabled", 409, "未啟用 transcript"],
    ];
    for (const [code, status, title] of cases) {
      const { wrapper } = mountDrawer(async () => {
        throw new GmApiError(code, { status, message: "x" });
      });
      await flushPromises();
      expect(wrapper.text()).toContain(title);
      expect(wrapper.text()).toContain(code);
      wrapper.unmount();
    }
  });

  it("never lets a slower earlier selection overwrite a later one", async () => {
    let releaseFirst;
    const first = new Promise((resolve) => (releaseFirst = resolve));
    const later = "0d".repeat(16);
    const { wrapper } = mountDrawer((path) =>
      path.endsWith(CALL) ? first : Promise.resolve({ ...CALL_DETAIL, outcome: { ...CALL_DETAIL.outcome, layer: "narrator" } }),
    );
    await wrapper.setProps({ callId: later });
    await flushPromises();
    releaseFirst(CALL_DETAIL);
    await flushPromises();
    expect(wrapper.get("[data-testid='gm-call-outcome']").text()).toContain("narrator");
  });

  it("closes on Escape and the close button", async () => {
    const { wrapper } = mountDrawer(async () => CALL_DETAIL);
    await flushPromises();
    await wrapper.trigger("keydown", { key: "Escape" });
    await wrapper.get("button[aria-label='關閉明細']").trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(2);
    await wrapper.setProps({ callId: null });
    expect(wrapper.attributes("open")).toBeUndefined();
  });

  it("falls back gracefully when the clipboard is unavailable", async () => {
    const original = navigator.clipboard;
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: undefined });
    const { wrapper } = mountDrawer(async () => CALL_DETAIL);
    await flushPromises();
    const copyAll = wrapper.findAll("button").find((button) => button.text() === "複製全部 JSON");
    await copyAll.trigger("click");
    await flushPromises();
    expect(copyAll.text()).toBe("複製失敗，請手動選取");
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: original });
  });

  it("restores focus to the opener, or the fallback heading when the opener is gone", async () => {
    const opener = document.createElement("button");
    const heading = document.createElement("h2");
    heading.id = "fallback-heading";
    document.body.append(opener, heading);
    opener.focus();
    const api = { get: vi.fn(async () => CALL_DETAIL), post: vi.fn() };
    const wrapper = mount(GmCallDrawer, {
      attachTo: document.body,
      props: { callId: CALL, api, fallbackFocus: "#fallback-heading" },
    });
    await flushPromises();
    expect(document.documentElement.classList.contains("gm-scroll-locked")).toBe(true);
    await wrapper.setProps({ callId: null });
    expect(document.activeElement).toBe(opener);
    expect(document.documentElement.classList.contains("gm-scroll-locked")).toBe(false);

    opener.focus();
    await wrapper.setProps({ callId: CALL });
    await flushPromises();
    opener.remove();
    await wrapper.setProps({ callId: null });
    expect(document.activeElement).toBe(heading);
    expect(heading.getAttribute("tabindex")).toBe("-1");
    wrapper.unmount();
  });

  it("does not move focus when it never opened, and unlocks scrolling on unmount", async () => {
    const outside = document.createElement("button");
    document.body.append(outside);
    outside.focus();
    const api = { get: vi.fn(), post: vi.fn() };
    const idle = mount(GmCallDrawer, { attachTo: document.body, props: { callId: null, api, fallbackFocus: "body" } });
    idle.unmount();
    expect(document.activeElement).toBe(outside);
    const { wrapper } = mountDrawer(async () => CALL_DETAIL);
    await flushPromises();
    wrapper.unmount();
    expect(document.documentElement.classList.contains("gm-scroll-locked")).toBe(false);
  });

  it("closes on a backdrop click only when the press started on the backdrop", async () => {
    const { wrapper } = mountDrawer(async () => CALL_DETAIL);
    await flushPromises();
    const sheet = wrapper.get(".gm-call-drawer__sheet");
    await sheet.trigger("pointerdown");
    await wrapper.trigger("click");
    expect(wrapper.emitted("close")).toBeUndefined();
    await wrapper.trigger("pointerdown");
    await wrapper.trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);
  });
});
