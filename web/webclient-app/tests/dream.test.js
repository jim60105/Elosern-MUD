import { describe, it, expect, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick, reactive } from "vue";
import DreamPanel from "../components/DreamPanel.vue";
import Protocol from "../../static/webclient/js/elosern/protocol.js";
import CommandEcho from "../../static/webclient/js/elosern/command_echo.js";
import { Storyboard } from "../stories/World/DreamPanel.stories.js";

function state(overrides = {}) {
  return { session_id: "synthetic-dream", revision: 2, completed: 0, remaining: 6,
    can_input: true, can_confirm: true, can_draft: true, can_awaken: true,
    pending: false, open: true, confirmed: false, failure: false,
    opening: "合成白色夢境", scene: "<script>合成場景</script>", dialogue: "合成對話",
    scene_art: "/art/official/0000000000000000000000000000000000000000000000000000000000000000/npc/dream_goddess/dream-throne.webp",
    direction_parts: [], thread_choices: [], draft_preferences: null,
    track: { version: 1, completed: 0, pleasure: 0, level: "平靜", ordinal: 0, climax_phase: "未達", converging: false },
    sleep: { tick_from: 17, tick_to: 17, requested_seconds: 0, seconds: 0, event_kinds: [] },
    ending: "", ending_phase: "", ...overrides };
}
function fixture(value = state(), options = {}) {
  const store = { view: reactive({ connected: true, dispatch: { inFlight: null } }), dispatchAction: vi.fn(() => "synthetic-request") };
  return { store, wrapper: mount(DreamPanel, { props: { state: value, store }, ...options }) };
}
const row = (wrapper, name) => wrapper.find(`[data-row='${name}']`);
const reply = (wrapper) => wrapper.find("[data-testid='dream-reply'] textarea");
async function openSheet(wrapper) {
  await row(wrapper, "edit").trigger("click");
  await flushPromises();
  return wrapper.find("[data-testid='dream-sheet']");
}

describe("server-authored dream surface", () => {
  it("stages the dream with core button chrome, one decisive action, and a keepsake card", async () => {
    const { wrapper } = fixture();
    expect(wrapper.attributes("role")).toBe("dialog");
    for (const button of wrapper.findAll("button")) expect(button.classes()).toContain("ui-btn");
    // While the conversation is open, speaking is the decisive action.
    expect(wrapper.findAll(".ui-btn--primary")).toHaveLength(1);
    expect(wrapper.find(".ui-btn--primary").text()).toBe("訴說");
    expect(row(wrapper, "confirm").text()).toContain("帶著這個念頭醒來");
    expect(row(wrapper, "awaken").text()).toContain("醒來");
    expect(wrapper.text()).not.toContain("JSON");
    expect(wrapper.find("details").exists()).toBe(false);
    expect(wrapper.find("[data-testid='dream-sheet']").exists()).toBe(false);
    // Both tracks have a visual form with a textual value.
    expect(wrapper.findAll(".dream-pip")).toHaveLength(6);
    expect(wrapper.find(".dream-pips").attributes("aria-valuetext")).toBe("尚可交談 6 次，共 6 次");
    expect(wrapper.findAll(".dream-gauge__seg")).toHaveLength(5);
    expect(wrapper.find(".dream-gauge").attributes("aria-valuetext")).toBe("女神的興奮：平靜");
    wrapper.unmount();
    const storyboard = mount(Storyboard.render({}), { attachTo: document.body });
    const publishCap = storyboard.findAll("button").find((button) => button.text() === "發布第六次上限");
    expect(publishCap.classes()).toContain("ui-btn");
    await publishCap.trigger("click");
    const panel = storyboard.findComponent(DreamPanel);
    expect(panel.props("state").remaining).toBe(0);
    expect(panel.find("form").exists()).toBe(false);
    expect(panel.find(".dream-reply--ended").text()).toContain("六次交談已盡");
    expect(panel.props("state").sleep).toMatchObject({ tick_from: 100, tick_to: 100 });
    expect(panel.find(".dream-choice").findAll("button")).toHaveLength(4);
    // At the cap the carry-out row becomes the single decisive action.
    expect(panel.findAll(".ui-btn--primary")).toHaveLength(1);
    expect(panel.find(".ui-btn--primary").attributes("data-row")).toBe("confirm");
    storyboard.unmount();
  });
  it("types the opening on arrival and shows a rejoined exchange in full", async () => {
    const arrival = fixture(state({ scene: "", dialogue: "" })).wrapper;
    await flushPromises();
    expect(arrival.find("[data-testid='dream-page']").text()).toBe("合成白色夢境");
    arrival.unmount();
    const { wrapper } = fixture();
    await flushPromises();
    expect(wrapper.find("[data-testid='dream-page']").text()).toBe("合成對話");
    expect(wrapper.find("script").exists()).toBe(false);
    await wrapper.find("button.ui-btn--ghost.ui-btn--sm").trigger("click");
    expect(wrapper.find("[data-testid='dream-page']").text()).toBe("<script>合成場景</script>");
  });
  it("submits exact bounded Unicode message parts on Enter but not Shift+Enter", async () => {
    const { wrapper, store } = fixture();
    await reply(wrapper).setValue("合成");
    await reply(wrapper).trigger("keydown", { key: "Enter", shiftKey: true });
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await reply(wrapper).setValue("界".repeat(4000));
    await reply(wrapper).trigger("keydown", { key: "Enter" });
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.say", { session_id: "synthetic-dream", revision: 2, message_parts: ["界".repeat(2000), "界".repeat(2000)] }, null);
    expect(reply(wrapper).element.value).toBe("");
  });
  it("ignores Enter while an IME composition is in progress", async () => {
    const { wrapper, store } = fixture();
    await reply(wrapper).setValue("合成");
    await reply(wrapper).trigger("keydown", { key: "Enter", isComposing: true });
    expect(store.dispatchAction).not.toHaveBeenCalled();
  });
  it("labels the 念頭 provenance and activates rows by digit outside text fields", async () => {
    const { wrapper } = fixture(state({ direction_parts: ["合成方向"] }));
    expect(wrapper.find(".dream-keepsake__chip").text()).toBe("取自你剛才的話");
    expect(wrapper.find(".dream-keepsake__target").text()).toBe("歸屬：一段新的故事");
    // A digit typed into the reply field is text, never a shortcut.
    await reply(wrapper).trigger("keydown", { key: "1" });
    expect(wrapper.find("[data-testid='dream-sheet']").exists()).toBe(false);
    await wrapper.trigger("keydown", { key: "1" });
    await flushPromises();
    const sheet = wrapper.find("[data-testid='dream-sheet']");
    expect(sheet.exists()).toBe(true);
    await sheet.find("textarea").setValue("合成改寫");
    expect(wrapper.find(".dream-keepsake__chip").text()).toBe("已改寫・未記下");
    wrapper.unmount();
    const drafted = fixture(state({ direction_parts: ["合成方向"], draft_preferences: { kind: "new_story", thread_id: null } })).wrapper;
    expect(drafted.find(".dream-keepsake__chip").text()).toBe("已記下");
  });
  it("filters a long thread list and keeps an orphaned saved thread selectable", async () => {
    const threads = Array.from({ length: 12 }, (_, index) => ({ id: `synthetic-thread-${index}`, label: index === 3 ? "合成港灣委託" : `合成故事 ${index}` }));
    const { wrapper } = fixture(state({ thread_choices: threads }));
    const sheet = await openSheet(wrapper);
    await sheet.find("input[type='search']").setValue("港灣");
    expect(sheet.findAll(".dream-threads__option").map((option) => option.text())).toEqual(["一段新的故事", "合成港灣委託"]);
    wrapper.unmount();
    const orphan = fixture(state({ direction_parts: ["合成方向"], draft_preferences: { kind: "thread_direction", thread_id: "synthetic-gone" } })).wrapper;
    const orphanSheet = await openSheet(orphan);
    expect(orphanSheet.find("input[type='radio']:checked").element.value).toBe("synthetic-gone");
    expect(orphanSheet.text()).toContain("先前選定的故事線（已不在清單中）");
  });
  it("reveals a response only on a live exchange increase", async () => {
    const { wrapper } = fixture(state({ scene: "", dialogue: "" }));
    const page = () => wrapper.find("[data-testid='dream-page']");
    await wrapper.setProps({ state: state({ revision: 3, completed: 1, remaining: 5, scene: "新的場景", dialogue: "新的台詞",
      track: { ...state().track, completed: 1, ordinal: 1, level: "微興奮" } }) });
    await flushPromises();
    expect(page().text()).toBe("新的場景");
    await page().trigger("click");
    expect(page().text()).toBe("新的台詞");
    expect(wrapper.find(".dream-live").text()).toContain("王座上的女神說：新的台詞");
    expect(wrapper.findAll(".dream-pip--spent")).toHaveLength(1);
    // A republish at the same count (a reconnect) presents nothing new.
    await wrapper.setProps({ state: state({ revision: 4, completed: 1, remaining: 5, scene: "新的場景", dialogue: "新的台詞",
      track: { ...state().track, completed: 1, ordinal: 1, level: "微興奮" } }) });
    expect(page().text()).toBe("新的台詞");
  });
  it("keeps confirm/draft/awakening usable at cap, during generation and after failure", async () => {
    for (const values of [{ completed: 6, remaining: 0, track: { ...state().track, completed: 6 } }, { pending: true }, { failure: true }]) {
      const { wrapper, store } = fixture(state({ ...values, can_input: false, direction_parts: ["合成方向"] }));
      if (values.pending) expect(reply(wrapper).attributes("disabled")).toBeDefined();
      for (const name of ["edit", "confirm", "draft", "awaken"]) expect(row(wrapper, name).attributes("disabled")).toBeUndefined();
      await row(wrapper, "awaken").trigger("click");
      expect(store.dispatchAction).toHaveBeenCalledWith("dream.awaken", { session_id: "synthetic-dream", revision: 2 }, null);
      wrapper.unmount();
    }
  });
  it("hands the sent words back for a retry after a failed generation", async () => {
    const { wrapper } = fixture();
    await reply(wrapper).setValue("合成的話");
    await wrapper.find("form").trigger("submit");
    await wrapper.setProps({ state: state({ revision: 3, pending: true, can_input: false }) });
    expect(wrapper.find("[data-testid='dream-page']").text()).toBe("你：「合成的話」");
    await wrapper.setProps({ state: state({ revision: 4, failure: true }) });
    expect(reply(wrapper).element.value).toBe("合成的話");
    expect(wrapper.find(".dream-reply__send").text()).toBe("再說一次");
    expect(wrapper.findAll(".dream-pip--spent")).toHaveLength(0);
  });
  it("never awakens on Escape and confirms before discarding unsent words", async () => {
    const { wrapper, store } = fixture(state(), { attachTo: document.body });
    await wrapper.trigger("keydown", { key: "Escape" });
    expect(document.activeElement).toBe(row(wrapper, "awaken").element);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await reply(wrapper).setValue("尚未送出的話");
    await row(wrapper, "awaken").trigger("click");
    await flushPromises();
    const dialog = wrapper.find("[data-testid='dream-confirm']");
    expect(dialog.attributes("role")).toBe("alertdialog");
    expect(dialog.text()).toContain("尚未說出口的話會隨夢消散");
    expect(document.activeElement.textContent).toBe("回到夢中");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await wrapper.trigger("keydown", { key: "Escape" });
    expect(wrapper.find("[data-testid='dream-confirm']").exists()).toBe(false);
    await row(wrapper, "awaken").trigger("click");
    await flushPromises();
    await wrapper.find("[data-testid='dream-confirm']").findAll("button")[1].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.awaken", { session_id: "synthetic-dream", revision: 2 }, null);
    wrapper.unmount();
  });
  it("refuses an empty carry-out locally and opens the 念頭 sheet", async () => {
    const { wrapper, store } = fixture();
    expect(row(wrapper, "confirm").attributes("aria-disabled")).toBe("true");
    await row(wrapper, "confirm").trigger("click");
    await flushPromises();
    expect(store.dispatchAction).not.toHaveBeenCalled();
    expect(wrapper.find("[data-testid='dream-sheet'] [role='alert']").text()).toContain("念頭還是空的");
  });
  it("blocks an over-length summary instead of truncating it", async () => {
    const { wrapper, store } = fixture(state({ direction_parts: ["長".repeat(2000), "長"] }));
    const sheet = await openSheet(wrapper);
    expect(sheet.find("textarea").element.value).toBe("長".repeat(2001));
    expect(sheet.find(".dream-field__counter--over").exists()).toBe(true);
    await sheet.findAll(".dream-sheet__foot button")[1].trigger("click");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    expect(sheet.find("[role='alert']").text()).toContain("2000");
  });
  it("uses the latest server revision after reconnect and retains explicit direction for draft/confirm", async () => {
    const { wrapper, store } = fixture();
    const sheet = await openSheet(wrapper);
    await sheet.find("textarea").setValue("合成新方向");
    await wrapper.setProps({ state: state({ revision: 7, remaining: 4, completed: 2 }) });
    await sheet.findAll(".dream-sheet__foot button")[1].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.confirm", { session_id: "synthetic-dream", revision: 7, direction: { kind: "new_story", thread_id: null, summary: "合成新方向" } }, null);
  });
  it("edits preference chips and saves a draft that keeps the dream open", async () => {
    const { wrapper, store } = fixture(state({ direction_parts: ["合成方向"] }));
    const sheet = await openSheet(wrapper);
    const themes = sheet.findAll(".dream-tags__box input")[0];
    await themes.setValue("重逢");
    await themes.trigger("keydown", { key: "Enter" });
    await themes.setValue("重逢");
    await themes.trigger("keydown", { key: "Enter" });
    expect(sheet.findAll(".dream-tags__chip")).toHaveLength(1);
    await themes.setValue("信任");
    await themes.trigger("keydown", { key: "Enter" });
    await themes.trigger("keydown", { key: "Backspace" });
    expect(sheet.findAll(".dream-tags__chip").map((chip) => chip.text())).toEqual(["重逢×"]);
    // Escape closes the sheet and keeps its edits.
    await wrapper.trigger("keydown", { key: "Escape" });
    expect(wrapper.find("[data-testid='dream-sheet']").exists()).toBe(false);
    await row(wrapper, "edit").trigger("click");
    await flushPromises();
    expect(wrapper.findAll(".dream-tags__chip")).toHaveLength(1);
    await wrapper.findAll(".dream-sheet__foot button")[0].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.draft", { session_id: "synthetic-dream", revision: 2,
      direction: { kind: "new_story", thread_id: null, summary: "合成方向", themes: ["重逢"] } }, null);
    await flushPromises();
    expect(wrapper.find("[data-testid='dream-sheet']").exists()).toBe(false);
    // The toast waits for the committed draft; a refusal republishes none.
    expect(wrapper.find(".dream-toast").exists()).toBe(false);
    await wrapper.setProps({ state: state({ revision: 3, direction_parts: ["合成方向"], draft_preferences: { kind: "new_story", thread_id: null, themes: ["重逢"] } }) });
    expect(wrapper.find(".dream-toast").text()).toBe("念頭已記下，夢仍在繼續。");
  });
  it("mirrors the strict panel schema and truthful command echoes", () => {
    const payload = { schema_version: 2, available: true, state: state() };
    expect(Protocol.validatePanel("dream", 2, payload)).toEqual(payload);
    expect(Protocol.validatePanel("dream", 2, { ...payload, state: null }).state).toBeNull();
    expect(() => Protocol.validatePanel("dream", 2, { ...payload, state: state({ remaining: 0 }) })).toThrow();
    expect(() => Protocol.validatePanel("dream", 2, { ...payload, state: state({ pending: true }) })).toThrow();
    expect(() => Protocol.validatePanel("dream", 2, { ...payload, state: state({ scene_art: null }) })).toThrow();
    expect(Protocol.validatePanel("dream", 2, { ...payload, state: state({
      thread_choices: [{ id: "synthetic-thread", label: "合成已知故事" }],
    }) }).state.thread_choices[0].label).toBe("合成已知故事");
    expect(() => Protocol.validatePanel("dream", 2, { ...payload, state: state({ thread_choices: ["synthetic-thread"] }) })).toThrow();
    expect(CommandEcho.commandLine("explore.wait", { sleep: true, dream: true })).toBe("sleep dream");
    expect(CommandEcho.commandLine("dream.say", { message_parts: ["合成", "方向"] })).toBe("dream say 合成方向");
    expect(CommandEcho.commandLine("dream.awaken", {})).toBe("dream awaken");
  });
  it("renders the server-resolved scene artwork, degrading on a failed load", async () => {
    const { wrapper } = fixture();
    expect(wrapper.find("img.dream-scene__art").attributes("src")).toBe(state().scene_art);
    // A replaced or withdrawn file 404s by design (the URL embeds the startup
    // fingerprint): the stage falls back to the flat ink background instead of
    // a broken-image glyph.
    await wrapper.find("img.dream-scene__art").trigger("error");
    expect(wrapper.find("img.dream-scene__art").exists()).toBe(false);
    // A changed URL is a new attempt.
    const republished = state().scene_art.replace("0000", "1111");
    await wrapper.setProps({ state: state({ scene_art: republished }) });
    expect(wrapper.find("img.dream-scene__art").attributes("src")).toBe(republished);
    wrapper.unmount();
    const blank = mount(DreamPanel, {
      props: { state: state({ scene_art: "" }), store: { view: reactive({ connected: true, dispatch: { inFlight: null } }), dispatchAction: vi.fn() } },
    });
    expect(blank.find("img.dream-scene__art").exists()).toBe(false);
    blank.unmount();
  });
  it("rehydrates a same-session external draft change without clearing unsent chat", async () => {
    const { wrapper, store } = fixture();
    await reply(wrapper).setValue("尚未送出的交流");
    await wrapper.setProps({ state: state({
      revision: 8, direction_parts: ["伺服器保存的故事方向"], thread_choices: [{ id: "synthetic-thread", label: "合成已知故事" }],
      draft_preferences: { kind: "thread_direction", thread_id: "synthetic-thread", themes: ["鐘聲"], exclusions: ["暴力"] },
    }) });
    expect(reply(wrapper).element.value).toBe("尚未送出的交流");
    expect(wrapper.find(".dream-keepsake__target").text()).toBe("歸屬：延續：合成已知故事");
    const sheet = await openSheet(wrapper);
    expect(sheet.find("input[type='radio']:checked").element.value).toBe("synthetic-thread");
    await sheet.findAll(".dream-sheet__foot button")[1].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.confirm", {
      session_id: "synthetic-dream", revision: 8,
      direction: { kind: "thread_direction", thread_id: "synthetic-thread", summary: "伺服器保存的故事方向", themes: ["鐘聲"], exclusions: ["暴力"] },
    }, null);
  });
  it("keeps an unsent direction edit when an exchange republishes the authored direction", async () => {
    const { wrapper } = fixture();
    await openSheet(wrapper);
    const editor = () => wrapper.find("[data-testid='dream-sheet'] textarea");
    // An untouched editor follows the authoritative direction the server
    // republishes after every accepted exchange.
    await wrapper.setProps({ state: state({ revision: 4, direction_parts: ["交換後提出的方向"] }) });
    expect(editor().element.value).toBe("交換後提出的方向");
    // A field the player has typed into keeps their own text instead.
    await editor().setValue("我還在寫的方向");
    await wrapper.setProps({ state: state({ revision: 5, direction_parts: ["交換後提出的方向", "再一次"] }) });
    expect(editor().element.value).toBe("我還在寫的方向");
    // Clearing the field restores the follow-the-server behaviour.
    await editor().setValue("");
    await wrapper.setProps({ state: state({ revision: 6, direction_parts: ["後來的方向"] }) });
    expect(editor().element.value).toBe("後來的方向");
  });
});

describe("dream stage review coverage", () => {
  const lockedViews = [
    { connected: false, dispatch: { inFlight: null } },
    { connected: true, dispatch: { inFlight: { requestId: "synthetic" } } },
    { connected: true, mutationsLocked: true, dispatch: { inFlight: null } },
    { connected: true, phase: "reconnecting", dispatch: { inFlight: null } },
  ];
  it("loads saved draft preferences on mount as already saved", async () => {
    const saved = state({ direction_parts: ["合成方向"], draft_preferences: { kind: "new_story", thread_id: null, themes: ["重逢"] } });
    const { wrapper, store } = fixture(saved);
    expect(wrapper.find(".dream-keepsake__chip").text()).toBe("已記下");
    await row(wrapper, "awaken").trigger("click");
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.awaken", { session_id: "synthetic-dream", revision: 2 }, null);
    await row(wrapper, "confirm").trigger("click");
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.confirm", { session_id: "synthetic-dream", revision: 2,
      direction: { kind: "new_story", thread_id: null, summary: "合成方向", themes: ["重逢"] } }, null);
  });
  it("types a live reveal at full motion and completes, then advances, on activation", async () => {
    vi.useFakeTimers();
    try {
      const store = { view: reactive({ connected: true, motionLevel: "full", textSpeed: "normal", dispatch: { inFlight: null } }), dispatchAction: vi.fn() };
      const wrapper = mount(DreamPanel, { props: { state: state({ scene: "", dialogue: "" }), store } });
      const page = () => wrapper.find("[data-testid='dream-page']");
      await wrapper.setProps({ state: state({ revision: 3, completed: 1, remaining: 5, scene: "長長的合成場景敘述文字", dialogue: "合成台詞",
        track: { ...state().track, completed: 1, ordinal: 1, level: "微興奮" } }) });
      vi.advanceTimersByTime(50);
      await nextTick();
      expect(page().text().length).toBeLessThan("長長的合成場景敘述文字".length);
      await page().trigger("click");
      expect(page().text()).toBe("長長的合成場景敘述文字");
      await page().trigger("click");
      vi.advanceTimersByTime(5000);
      await nextTick();
      expect(page().text()).toBe("合成台詞");
      wrapper.unmount();
    } finally {
      vi.useRealTimers();
    }
  });
  it("lights the gauge to the ordinal and marks the next pip while composing", async () => {
    const { wrapper } = fixture();
    expect(wrapper.find(".dream-gauge").attributes("role")).toBe("meter");
    expect(wrapper.find(".dream-pips").attributes("role")).toBe("meter");
    expect(wrapper.findAll(".dream-gauge__seg--lit")).toHaveLength(1);
    expect(wrapper.find(".dream-pips__count").text()).toBe("尚餘 6");
    expect(wrapper.findAll(".dream-pip--next")).toHaveLength(0);
    await reply(wrapper).setValue("合成");
    expect(wrapper.findAll(".dream-pip").findIndex((pip) => pip.classes().includes("dream-pip--next"))).toBe(0);
    await wrapper.setProps({ state: state({ completed: 3, remaining: 3, track: { ...state().track, completed: 3, ordinal: 2, level: "中等" } }) });
    expect(wrapper.findAll(".dream-gauge__seg--lit")).toHaveLength(3);
  });
  it("announces a response, pending and failure once each", async () => {
    const { wrapper } = fixture(state({ scene: "", dialogue: "" }));
    const live = () => wrapper.find(".dream-live").text();
    await wrapper.setProps({ state: state({ revision: 3, pending: true, can_input: false }) });
    expect(live()).toBe("女神正在回應。");
    await wrapper.setProps({ state: state({ revision: 4, completed: 1, remaining: 5, scene: "合成場景", dialogue: "合成台詞",
      track: { ...state().track, completed: 1, ordinal: 1, level: "微興奮" } }) });
    expect(live()).toContain("合成場景");
    expect(live()).toContain("女神的興奮：微興奮。");
    expect(live()).toContain("尚可交談 5 次。");
    await wrapper.setProps({ state: state({ revision: 5, completed: 1, remaining: 5, failure: true, track: { ...state().track, completed: 1 } }) });
    expect(live()).toContain("夢境一時模糊");
  });
  it("disables every dream action while the transport is locked and keeps typed text", async () => {
    for (const view of lockedViews) {
      const store = { view: reactive(view), dispatchAction: vi.fn() };
      const wrapper = mount(DreamPanel, { props: { state: state({ direction_parts: ["合成方向"] }), store } });
      for (const name of ["edit", "confirm", "draft", "awaken"]) expect(row(wrapper, name).attributes("disabled")).toBeDefined();
      expect(reply(wrapper).attributes("disabled")).toBeDefined();
      if (!view.connected) expect(wrapper.find(".dream-reply__caption").text()).toContain("與夢的聯繫中斷了");
      wrapper.unmount();
    }
  });
  it("captions the converging and final exchange and focuses the carry-out row on a live sixth exchange", async () => {
    const converging = { ...state().track, completed: 4, ordinal: 3, level: "高度", converging: true };
    const { wrapper } = fixture(state({ completed: 4, remaining: 2, track: converging, direction_parts: ["合成方向"] }), { attachTo: document.body });
    expect(wrapper.find(".dream-reply__caption").text()).toBe("夢將抵達盡頭");
    await wrapper.setProps({ state: state({ revision: 3, completed: 5, remaining: 1, track: { ...converging, completed: 5 }, direction_parts: ["合成方向"] }) });
    expect(wrapper.find(".dream-reply__caption").text()).toBe("夢將抵達盡頭 · 最後一次交談");
    await wrapper.setProps({ state: state({ revision: 4, completed: 6, remaining: 0, can_input: false, track: { ...converging, completed: 6, ordinal: 4, level: "極限" }, direction_parts: ["合成方向"] }) });
    await flushPromises();
    expect(document.activeElement).toBe(row(wrapper, "confirm").element);
    expect(row(wrapper, "draft").text()).toContain("記下念頭");
    expect(row(wrapper, "draft").text()).not.toContain("繼續作夢");
    wrapper.unmount();
  });
  it("names the dialog, shows the empty invitation, orders rows and maps digits 2 and 3", async () => {
    const { wrapper, store } = fixture(state({ direction_parts: [] }));
    expect(wrapper.find(`#${wrapper.attributes("aria-labelledby")}`).text()).toBe("雲上王座之夢");
    expect(wrapper.find(".dream-keepsake__empty").text()).toBe("念頭尚未成形。和女神談談，或親手寫下。");
    expect(wrapper.findAll(".dream-choice button").map((button) => button.attributes("data-row"))).toEqual(["edit", "confirm", "draft", "awaken"]);
    await wrapper.trigger("keydown", { key: "1", ctrlKey: true });
    expect(wrapper.find("[data-testid='dream-sheet']").exists()).toBe(false);
    await wrapper.setProps({ state: state({ revision: 3, direction_parts: ["合成方向"] }) });
    await wrapper.trigger("keydown", { key: "3" });
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.draft", expect.objectContaining({ revision: 3 }), null);
    await wrapper.trigger("keydown", { key: "2" });
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.confirm", expect.objectContaining({ revision: 3 }), null);
  });
  it("leaves a text field on Escape, focuses the summary on an empty confirm, and makes the stage inert under the sheet", async () => {
    const { wrapper, store } = fixture(state({ direction_parts: [] }), { attachTo: document.body });
    reply(wrapper).element.focus();
    await reply(wrapper).trigger("keydown", { key: "Escape" });
    expect(document.activeElement).toBe(wrapper.find("[data-testid='dream-page']").element);
    await row(wrapper, "confirm").trigger("click");
    await flushPromises();
    const sheet = wrapper.find("[data-testid='dream-sheet']");
    expect(document.activeElement).toBe(sheet.find("textarea").element);
    expect(wrapper.find(".dream-scene__main").attributes("inert")).toBeDefined();
    expect(sheet.find(".dream-field__counter").text()).toBe("0 / 2000");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    wrapper.unmount();
  });
  it("protects an unsaved 念頭 edit and refuses an over-length draft", async () => {
    const { wrapper, store } = fixture(state({ direction_parts: ["合成方向"] }));
    let sheet = await openSheet(wrapper);
    await sheet.find("textarea").setValue("合成改寫");
    expect(sheet.find(".dream-link").text()).toBe("還原為剛才的話");
    await wrapper.trigger("keydown", { key: "Escape" });
    await row(wrapper, "awaken").trigger("click");
    await flushPromises();
    expect(wrapper.find("[data-testid='dream-confirm']").text()).toContain("尚未記下的改寫會隨夢消散");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await wrapper.trigger("keydown", { key: "Escape" });
    sheet = await openSheet(wrapper);
    await sheet.find("textarea").setValue("長".repeat(2001));
    await sheet.findAll(".dream-sheet__foot button")[0].trigger("click");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    expect(sheet.find("[role='alert']").text()).toContain("2000");
  });
  it("keeps edited thread and chips across a republish and new reply text across a failure", async () => {
    const threads = [{ id: "synthetic-a", label: "合成甲" }, { id: "synthetic-b", label: "合成乙" }];
    const { wrapper } = fixture(state({ direction_parts: ["合成方向"], thread_choices: threads }));
    const sheet = await openSheet(wrapper);
    await sheet.findAll("input[type='radio']")[1].setValue(true);
    const themes = sheet.findAll(".dream-tags__box input")[0];
    await themes.setValue("合成主題");
    await themes.trigger("keydown", { key: "Enter" });
    await wrapper.setProps({ state: state({ revision: 5, direction_parts: ["合成方向"], thread_choices: threads,
      draft_preferences: { kind: "thread_direction", thread_id: "synthetic-b", themes: ["伺服器主題"] } }) });
    expect(sheet.find("input[type='radio']:checked").element.value).toBe("synthetic-a");
    expect(sheet.findAll(".dream-tags__chip").map((chip) => chip.text())).toEqual(["合成主題×"]);
    await wrapper.trigger("keydown", { key: "Escape" });
    await reply(wrapper).setValue("先送出的話");
    await wrapper.find("form").trigger("submit");
    await reply(wrapper).setValue("新打的字");
    await wrapper.setProps({ state: state({ revision: 6, failure: true, direction_parts: ["合成方向"], thread_choices: threads }) });
    expect(reply(wrapper).element.value).toBe("新打的字");
  });
});
