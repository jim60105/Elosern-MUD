import { describe, it, expect, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { reactive } from "vue";
import DreamPanel from "../components/DreamPanel.vue";
import Protocol from "../../static/webclient/js/elosern/protocol.js";
import CommandEcho from "../../static/webclient/js/elosern/command_echo.js";

function state(overrides = {}) {
  return { session_id: "synthetic-dream", revision: 2, completed: 0, remaining: 6,
    can_input: true, can_confirm: true, can_draft: true, can_awaken: true,
    pending: false, open: true, confirmed: false, failure: false,
    opening: "合成白色夢境", scene: "<script>合成場景</script>", dialogue: "合成對話",
    direction_parts: [], thread_choices: [], draft_preferences: null,
    track: { version: 1, completed: 0, pleasure: 0, level: "平靜", ordinal: 0, climax_phase: "未達", converging: false },
    sleep: { tick_from: 17, tick_to: 17, requested_seconds: 0, seconds: 0, event_kinds: [] },
    ending: "", ending_phase: "", ...overrides };
}
function fixture(value = state()) {
  const store = { view: reactive({ connected: true, dispatch: { inFlight: null } }), dispatchAction: vi.fn(() => "synthetic-request") };
  return { store, wrapper: mount(DreamPanel, { props: { state: value, store } }) };
}
describe("server-authored dream surface", () => {
  it("renders validated scene/dialogue safely and submits exact bounded Unicode message parts", async () => {
    const { wrapper, store } = fixture();
    expect(wrapper.text()).toContain("合成對話");
    expect(wrapper.find("script").exists()).toBe(false);
    expect(wrapper.text()).toContain("剩餘交流次數：6");
    await wrapper.find("form textarea").setValue("界".repeat(4000));
    await wrapper.find("form").trigger("submit");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.say", { session_id: "synthetic-dream", revision: 2, message_parts: ["界".repeat(2000), "界".repeat(2000)] }, null);
  });
  it("keeps confirm/draft/awakening usable at cap, during generation and after failure", async () => {
    for (const values of [{ completed: 6, remaining: 0, track: { ...state().track, completed: 6 } }, { pending: true }, { failure: true }]) {
      const { wrapper, store } = fixture(state({ ...values, can_input: false }));
      expect(wrapper.find("form").exists()).toBe(false);
      const buttons = wrapper.findAll("button");
      expect(buttons).toHaveLength(3);
      for (const button of buttons) expect(button.attributes("disabled")).toBeUndefined();
      await buttons[2].trigger("click");
      expect(store.dispatchAction).toHaveBeenCalledWith("dream.awaken", { session_id: "synthetic-dream", revision: 2 }, null);
      wrapper.unmount();
    }
  });
  it("uses the latest server revision after reconnect and retains explicit direction for draft/confirm", async () => {
    const { wrapper, store } = fixture();
    await wrapper.findAll("textarea")[1].setValue("合成新方向");
    await wrapper.setProps({ state: state({ revision: 7, remaining: 4, completed: 2 }) });
    await wrapper.findAll("button")[1].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.confirm", { session_id: "synthetic-dream", revision: 7, direction: { kind: "new_story", thread_id: null, summary: "合成新方向" } }, null);
  });
  it("mirrors the strict panel schema and truthful command echoes", () => {
    const payload = { schema_version: 1, available: true, state: state() };
    expect(Protocol.validatePanel("dream", 1, payload)).toEqual(payload);
    expect(Protocol.validatePanel("dream", 1, { ...payload, state: null }).state).toBeNull();
    expect(() => Protocol.validatePanel("dream", 1, { ...payload, state: state({ remaining: 0 }) })).toThrow();
    expect(() => Protocol.validatePanel("dream", 1, { ...payload, state: state({ pending: true }) })).toThrow();
    expect(CommandEcho.commandLine("explore.wait", { sleep: true, dream: true })).toBe("sleep dream");
    expect(CommandEcho.commandLine("dream.say", { message_parts: ["合成", "方向"] })).toBe("dream say 合成方向");
    expect(CommandEcho.commandLine("dream.awaken", {})).toBe("dream awaken");
  });
});
