import { describe, it, expect, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick, reactive } from "vue";
import DreamPanel from "../components/DreamPanel.vue";
import Protocol from "../../static/webclient/js/elosern/protocol.js";
import CommandEcho from "../../static/webclient/js/elosern/command_echo.js";
import {
  dreamBundledDescriptor,
  dreamDescriptor,
  dreamExhaustedDescriptor,
  dreamRefusedDescriptor,
} from "../stories/fixtures.js";
import { observeError, observeLoad } from "./support/scene_layers.js";

const LISTS = { themes: [], atmosphere: [], participants: [], emphasis: [], exclusions: [] };
function proposal(overrides = {}) {
  return { summary: "", ...LISTS, requirements: [], ...overrides };
}
// A valid schema-4 dream state: conversing, nothing said yet, an empty wish.
function state(overrides = {}) {
  return { session_id: "synthetic-dream", revision: 2, completed: 0, remaining: 6,
    can_input: true, can_confirm: false, can_finalize: true, can_choose_thread: true,
    can_edit: false, can_draft: true, can_awaken: true,
    pending: false, open: true, confirmed: false, failure: false,
    opening: "合成白色夢境", scene: "<script>合成場景</script>", dialogue: "合成對話",
    // The shared canonical scene descriptor of the dream's own source chain.
    scene_art: dreamDescriptor(),
    // Schema-3 keys the wire still carries; the panel never reads them.
    direction_parts: [], thread_choices: [], draft_preferences: null,
    requirements: [], requirement_version: null,
    stage: "conversing", drafted: false, thread_id: null, changes: null,
    proposal: proposal(),
    track: { version: 1, completed: 0, pleasure: 0, level: "平靜", ordinal: 0, climax_phase: "未達", converging: false },
    sleep: { tick_from: 17, tick_to: 17, requested_seconds: 0, seconds: 0, event_kinds: [] },
    ending: "", ending_phase: "", ...overrides };
}
// The same session once free text has closed: the form is the player's.
function finalized(overrides = {}) {
  return state({ stage: "finalized", can_input: false, can_finalize: false, can_choose_thread: false,
    can_edit: true, can_confirm: true, ...overrides });
}
const capped = (overrides = {}) => finalized({ completed: 6, remaining: 0,
  track: { ...state().track, completed: 6, ordinal: 4, level: "極限" }, ...overrides });
function fixture(value = state(), options = {}) {
  const store = { view: reactive({ connected: true, dispatch: { inFlight: null } }), dispatchAction: vi.fn(() => "synthetic-request") };
  return { store, wrapper: mount(DreamPanel, { props: { state: value, store }, ...options }) };
}
const THREADS = [{ id: "synthetic-a", label: "合成甲" }, { id: "synthetic-b", label: "合成乙" }];
const REQUIREMENTS = [
  { kind: "place", text: "合成南門" },
  { kind: "new_character", text: "合成女孩" },
  { kind: "private_commission", text: "合成委託" },
];
const SESSION = { session_id: "synthetic-dream", revision: 2 };
const row = (wrapper, name) => wrapper.find(`[data-row='${name}']`);
const rowNames = (wrapper) => wrapper.findAll(".dream-choice button").map((button) => button.attributes("data-row"));
const reply = (wrapper) => wrapper.find("[data-testid='dream-reply'] textarea");
const layer = (wrapper, id) => wrapper.find(`[data-testid='${id}']`);
const sheetButtons = (wrapper) => layer(wrapper, "dream-sheet").findAll(".dream-sheet__foot button");
const statements = (wrapper) => layer(wrapper, "dream-confirm").findAll("[data-statement]").map((item) => item.attributes("data-statement"));
// One settled frame: the driver's provisional retirement and the resolution
// that follows it are watcher-driven, so a state change needs a real tick.
async function frames() {
  await new Promise((resolve) => setTimeout(resolve, 60));
  await nextTick();
}
async function activate(wrapper, name) {
  await row(wrapper, name).trigger("click");
  await flushPromises();
}
async function openSheet(wrapper) {
  await activate(wrapper, "main");
  return layer(wrapper, "dream-sheet");
}
async function escape(wrapper) {
  await wrapper.trigger("keydown", { key: "Escape" });
  await flushPromises();
}

describe("server-authored dream surface", () => {
  it("stages the dream with core button chrome, one decisive action, and a keepsake card", async () => {
    const { wrapper } = fixture(state({ thread_choices: THREADS }));
    expect(wrapper.attributes("role")).toBe("dialog");
    expect(wrapper.attributes("aria-modal")).toBe("true");
    expect(wrapper.find(".dream-keepsake").exists()).toBe(true);
    expect(wrapper.find("[data-testid='dream-reply']").exists()).toBe(true);
    expect(wrapper.find(".dream-window [data-testid='dream-page']").exists()).toBe(true);
    expect(rowNames(wrapper)).toEqual(["main", "take", "draft", "awaken"]);
    // Every button outside the thread choice's inline controls is a core button.
    for (const button of wrapper.findAll("button")) {
      if (!button.element.closest("[data-testid='dream-belong']")) expect(button.classes()).toContain("ui-btn");
    }
    // While conversing, speaking is the one decisive action.
    expect(wrapper.findAll(".ui-btn--primary")).toHaveLength(1);
    expect(wrapper.find(".ui-btn--primary").classes()).toContain("dream-reply__send");
    expect(wrapper.text()).not.toContain("JSON");
    expect(wrapper.find("details").exists()).toBe(false);
    expect(layer(wrapper, "dream-sheet").exists()).toBe(false);
    expect(wrapper.attributes("data-stage")).toBe("conversing");
    // Both tracks have a visual form with a textual value.
    expect(wrapper.findAll(".dream-pip")).toHaveLength(6);
    expect(wrapper.find(".dream-pips").attributes("aria-valuetext")).toMatch(/6\D+6/);
    expect(wrapper.findAll(".dream-gauge__seg")).toHaveLength(5);
    expect(wrapper.find(".dream-gauge").attributes("aria-valuetext")).toContain("平靜");
    wrapper.unmount();
    // Once finalized the free-text form gives way to the end bar and the
    // confirm row is the one decisive action.
    const cap = fixture(capped({ proposal: proposal({ summary: "合成願望" }) })).wrapper;
    expect(cap.attributes("data-stage")).toBe("finalized");
    expect(cap.find("form").exists()).toBe(false);
    expect(cap.find(".dream-reply--ended").exists()).toBe(true);
    expect(rowNames(cap)).toEqual(["main", "confirm", "draft", "awaken"]);
    expect(cap.findAll(".ui-btn--primary")).toHaveLength(1);
    expect(cap.find(".ui-btn--primary").attributes("data-row")).toBe("confirm");
    for (const button of cap.findAll("button")) expect(button.classes()).toContain("ui-btn");
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
  it("keeps draft and awakening usable at cap, during generation and after failure", async () => {
    const cases = [
      capped({ proposal: proposal({ summary: "合成願望" }) }),
      state({ pending: true, can_input: false, can_finalize: false, can_choose_thread: false }),
      state({ failure: true }),
    ];
    for (const value of cases) {
      const { wrapper, store } = fixture(value);
      if (value.pending) expect(reply(wrapper).attributes("disabled")).toBeDefined();
      const second = value.stage === "finalized" ? "confirm" : "take";
      for (const name of ["main", second, "draft", "awaken"]) {
        // Only finalizing waits for the goddess's response.
        if (value.pending && name === "take") expect(row(wrapper, name).attributes("disabled")).toBeDefined();
        else expect(row(wrapper, name).attributes("disabled")).toBeUndefined();
      }
      await row(wrapper, "awaken").trigger("click");
      expect(store.dispatchAction).toHaveBeenCalledWith("dream.awaken", SESSION, null);
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
    const dialog = layer(wrapper, "dream-confirm");
    expect(dialog.attributes("role")).toBe("alertdialog");
    expect(statements(wrapper)).toEqual(["unsent"]);
    const [stay] = dialog.findAll(".dream-confirm__actions button");
    expect(document.activeElement).toBe(stay.element);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await wrapper.trigger("keydown", { key: "Escape" });
    expect(layer(wrapper, "dream-confirm").exists()).toBe(false);
    await row(wrapper, "awaken").trigger("click");
    await flushPromises();
    await layer(wrapper, "dream-confirm").findAll(".dream-confirm__actions button")[0].trigger("click");
    expect(layer(wrapper, "dream-confirm").exists()).toBe(false);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await row(wrapper, "awaken").trigger("click");
    await flushPromises();
    await layer(wrapper, "dream-confirm").findAll(".dream-confirm__actions button")[1].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.awaken", SESSION, null);
    wrapper.unmount();
  });
  it("refuses an empty confirm locally and opens the edit sheet on the summary", async () => {
    const { wrapper, store } = fixture(finalized(), { attachTo: document.body });
    // Unavailable but still focusable, with a visible reason.
    expect(row(wrapper, "confirm").attributes("aria-disabled")).toBe("true");
    expect(row(wrapper, "confirm").attributes("disabled")).toBeUndefined();
    expect(wrapper.find(`#${row(wrapper, "confirm").attributes("aria-describedby")}`).exists()).toBe(true);
    await row(wrapper, "confirm").trigger("click");
    await flushPromises();
    expect(store.dispatchAction).not.toHaveBeenCalled();
    const sheet = layer(wrapper, "dream-sheet");
    expect(sheet.find("[role='alert']").exists()).toBe(true);
    expect(document.activeElement).toBe(sheet.find("textarea").element);
    wrapper.unmount();
  });
  it("blocks an over-length summary instead of truncating it", async () => {
    const { wrapper, store } = fixture(finalized({ proposal: proposal({ summary: "合成願望" }) }));
    const sheet = await openSheet(wrapper);
    await sheet.find("textarea").setValue("長".repeat(2001));
    expect(sheet.find("textarea").element.value).toBe("長".repeat(2001));
    expect(sheet.find(".dream-field__counter--over").exists()).toBe(true);
    expect(sheet.find("textarea").attributes("aria-invalid")).toBe("true");
    await sheetButtons(wrapper)[1].trigger("click");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    expect(sheet.find("[role='alert']").exists()).toBe(true);
    await sheetButtons(wrapper)[0].trigger("click");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    expect(sheet.find("textarea").element.value).toBe("長".repeat(2001));
  });
  it("sends the latest committed revision from the finalized sheet", async () => {
    const { wrapper, store } = fixture(finalized());
    const sheet = await openSheet(wrapper);
    await sheet.find("textarea").setValue("合成新願望");
    await wrapper.setProps({ state: finalized({ revision: 7, remaining: 4, completed: 2 }) });
    await sheetButtons(wrapper)[1].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.confirm", { session_id: "synthetic-dream", revision: 7,
      direction: { kind: "new_story", thread_id: null, summary: "合成新願望", requirements: [] } }, null);
  });
  it("edits preference chips and saves a draft that keeps the dream open", async () => {
    const { wrapper, store } = fixture(finalized({ proposal: proposal({ summary: "合成願望" }) }));
    const sheet = await openSheet(wrapper);
    const themes = sheet.findAll(".dream-tags__box input")[0];
    await themes.setValue("  重逢 ");
    await themes.trigger("keydown", { key: "Enter" });
    await themes.setValue("重逢");
    await themes.trigger("keydown", { key: "Enter" });
    expect(sheet.findAll(".dream-tags__chip")).toHaveLength(1);
    await themes.setValue("信任");
    await themes.trigger("keydown", { key: "Enter" });
    expect(sheet.findAll(".dream-tags__chip")).toHaveLength(2);
    await themes.trigger("keydown", { key: "Backspace" });
    expect(sheet.findAll(".dream-tags__chip")).toHaveLength(1);
    // Escape closes the sheet and keeps its edits.
    await escape(wrapper);
    expect(layer(wrapper, "dream-sheet").exists()).toBe(false);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await openSheet(wrapper);
    expect(wrapper.findAll(".dream-tags__chip")).toHaveLength(1);
    await sheetButtons(wrapper)[0].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.draft", { ...SESSION,
      direction: { kind: "new_story", thread_id: null, summary: "合成願望", themes: ["重逢"], requirements: [] } }, null);
    await flushPromises();
    expect(layer(wrapper, "dream-sheet").exists()).toBe(false);
    expect(wrapper.find("[data-testid='dream-panel']").exists()).toBe(true);
    // The toast waits for the committed draft.
    expect(wrapper.find(".dream-toast").exists()).toBe(false);
    await wrapper.setProps({ state: finalized({ revision: 3, drafted: true, proposal: proposal({ summary: "合成願望", themes: ["重逢"] }) }) });
    expect(wrapper.find(".dream-toast").attributes("role")).toBe("status");
  });
  it("mirrors the strict panel schema and truthful command echoes", () => {
    const payload = { schema_version: 4, available: true, state: state() };
    expect(Protocol.validatePanel("dream", 4, payload)).toEqual(payload);
    // The finalized fixtures are legal schema-4 payloads too.
    for (const value of [finalized(), capped(), finalized({ thread_choices: THREADS, thread_id: "synthetic-a" })]) {
      expect(Protocol.validatePanel("dream", 4, { ...payload, state: value }).state).toEqual(value);
    }
    expect(Protocol.validatePanel("dream", 4, { ...payload, state: null }).state).toBeNull();
    expect(() => Protocol.validatePanel("dream", 4, { ...payload, state: state({ remaining: 0 }) })).toThrow();
    expect(() => Protocol.validatePanel("dream", 4, { ...payload, state: state({ pending: true }) })).toThrow();
    // The retired raw-URL shape is refused, not adapted: the state's artwork is
    // the canonical scene descriptor or nothing at all.
    for (const retired of [
      "/art/official/" + "0".repeat(64) + "/npc/dream_goddess/dream-throne.webp",
      "",
      null,
      { ...dreamDescriptor(), attempts: [{ type: "image", source_id: "scene.operator:dream_throne", rank: 30, resource: { resource_id: "x", version: "y", url: "/art/x", origin: "official", geometry: null } }] },
    ]) {
      expect(() => Protocol.validatePanel("dream", 4, { ...payload, state: state({ scene_art: retired }) }))
        .toThrow();
    }
    expect(Protocol.validatePanel("dream", 4, { ...payload, state: state({
      thread_choices: [{ id: "synthetic-thread", label: "合成已知故事" }],
    }) }).state.thread_choices[0].label).toBe("合成已知故事");
    expect(() => Protocol.validatePanel("dream", 4, { ...payload, state: state({ thread_choices: ["synthetic-thread"] }) })).toThrow();
    expect(CommandEcho.commandLine("explore.wait", { sleep: true })).toBe("sleep");
    expect(CommandEcho.commandLine("explore.sleep_party", {})).toBe("sleep all");
    expect(CommandEcho.commandLine("explore.sleep_continue", {})).toBe("sleep continue");
    expect(CommandEcho.commandLine("explore.sleep_dream", { decision: "enter" })).toBe("dream enter");
    expect(CommandEcho.commandLine("explore.sleep_dream", { decision: "decline" })).toBe("dream decline");
    expect(CommandEcho.commandLine("dream.say", { message_parts: ["合成", "方向"] })).toBe("dream say 合成方向");
    expect(CommandEcho.commandLine("dream.awaken", {})).toBe("dream awaken");
  });
  it("renders the server-resolved scene artwork, degrading on a failed load", async () => {
    const [preferred, bundled] = dreamDescriptor().attempts.map((entry) => entry.resource.url);
    // A healthy preferred operator image paints as soon as its own element
    // reports real pixels, and it carries no failure fact at all.
    const healthy = fixture();
    await observeLoad(healthy.wrapper, preferred);
    expect(healthy.wrapper.find("[data-testid='dream-scene-art']").attributes("src")).toBe(preferred);
    expect(healthy.wrapper.find("[data-testid='dream-scene-art']").attributes("data-art-role")).toBe("attempt");
    expect(healthy.wrapper.find("[data-testid='dream-art-failure']").exists()).toBe(false);
    healthy.wrapper.unmount();
    // A withdrawn operator file 404s by design (the URL embeds the startup
    // fingerprint): the reached failure stays stated while the REQUIRED bundled
    // dream illustration follows it — never a broken-image glyph.
    const broken = fixture();
    await observeError(broken.wrapper, preferred);
    await frames();
    await observeLoad(broken.wrapper, bundled);
    expect(broken.wrapper.find("[data-testid='dream-scene-art']").attributes("src")).toBe(bundled);
    expect(broken.wrapper.find("[data-testid='dream-art-failure']").text()).toBe("圖片載入失敗。");
    broken.wrapper.unmount();
    // When the required bundled dream cannot load either, the distinct
    // declared town terminal is what the shared walk reaches — with the
    // reached failures still stated and no broken image anywhere.
    const terminal = fixture();
    await observeError(terminal.wrapper, preferred);
    await frames();
    await observeError(terminal.wrapper, bundled);
    await frames();
    const town = dreamDescriptor().terminal.resource.url;
    await observeLoad(terminal.wrapper, town);
    expect(terminal.wrapper.find("[data-testid='dream-scene-art']").attributes("src")).toBe(town);
    expect(terminal.wrapper.find("[data-testid='dream-art-failure']").text()).toBe("圖片載入失敗。");
    expect(terminal.wrapper.findAll("img[src='']")).toHaveLength(0);
    terminal.wrapper.unmount();
  });
  it("shows the bundled dream when the preferred image is absent and the reached fact when every illustration is missing", async () => {
    const bundledOnly = dreamBundledDescriptor();
    const { wrapper } = fixture(state({ scene_art: bundledOnly }));
    const bundled = bundledOnly.attempts[0].resource.url;
    await observeLoad(wrapper, bundled);
    expect(wrapper.find("[data-testid='dream-scene-art']").attributes("src")).toBe(bundled);
    // Absence contributes no fact: the required bundled dream simply shows.
    expect(wrapper.find("[data-testid='dream-art-failure']").exists()).toBe(false);
    wrapper.unmount();
    const exhausted = fixture(state({ scene_art: dreamExhaustedDescriptor() }));
    expect(exhausted.wrapper.find("[data-testid='dream-scene-art']").exists()).toBe(false);
    expect(exhausted.wrapper.find("[data-testid='dream-art-control']").exists()).toBe(false);
    expect(exhausted.wrapper.find("[data-testid='dream-art-failure']").text()).toBe("缺少必要的圖片資源。");
    exhausted.wrapper.unmount();
  });
  it("opens the full view on the displayed resource with the same reached failure", async () => {
    const refused = dreamRefusedDescriptor();
    const { wrapper } = fixture(state({ scene_art: refused }));
    const bundled = refused.attempts[1].resource.url;
    await observeLoad(wrapper, bundled);
    // The refused preferred image's reached fact leads the stage...
    const marker = wrapper.find("[data-testid='dream-art-failure']");
    expect(marker.exists()).toBe(true);
    // ...and the full view shows exactly the displayed resource and that same
    // failure, so no second resolution and no broken-only view exists.
    await wrapper.find("[data-testid='dream-art-control']").trigger("click");
    await flushPromises();
    const view = wrapper.find("[data-testid='dream-art-view']");
    expect(view.exists()).toBe(true);
    expect(view.find("[data-testid='dream-art-view-image']").attributes("src")).toBe(bundled);
    expect(view.find("[data-testid='dream-art-view-failure']").text()).toBe(marker.text());
    // The stage beneath the full view is inert while it is open.
    expect(wrapper.find(".dream-scene__main").attributes("inert")).toBeDefined();
    await wrapper.find("[data-testid='dream-art-view']").trigger("keydown", { key: "Escape" });
    expect(wrapper.find("[data-testid='dream-art-view']").exists()).toBe(false);
    expect(wrapper.find(".dream-scene__main").attributes("inert")).toBeUndefined();
    wrapper.unmount();
  });
  it("retires the previous dream session's callbacks when the subject changes", async () => {
    const { wrapper } = fixture();
    const stale = dreamDescriptor().attempts[0].resource.url;
    const second = dreamBundledDescriptor({ subject_id: "dream:1:synthetic-second-session" });
    await wrapper.setProps({ state: state({ session_id: "synthetic-second", scene_art: second }) });
    // A new session is a new logical subject: nothing of the old resolution is
    // presented, and a late event for its retired element settles nothing.
    expect(wrapper.find("[data-testid='dream-scene-art']").exists()).toBe(false);
    const staleLayer = wrapper.findAll("img").find((img) => img.attributes("src") === stale);
    expect(staleLayer).toBeUndefined();
    const bundled = second.attempts[0].resource.url;
    await observeLoad(wrapper, bundled);
    expect(wrapper.find("[data-testid='dream-scene-art']").attributes("src")).toBe(bundled);
    expect(wrapper.find("[data-testid='dream-scene-art']").attributes("data-art-role")).toBe("attempt");
    wrapper.unmount();
  });
  it("recomputes a changed descriptor revision and ignores the retired callback", async () => {
    const { wrapper } = fixture();
    const [preferred] = dreamDescriptor().attempts.map((entry) => entry.resource.url);
    // A same-subject descriptor whose preferred resource changed: a new
    // resource version is a new attempt, so the ordered walk starts afresh.
    const republished = dreamRefusedDescriptor({
      subject_id: dreamDescriptor().subject_id,
    });
    await wrapper.setProps({ state: state({ revision: 3, scene_art: republished }) });
    expect(wrapper.find("[data-testid='dream-scene-art']").exists()).toBe(false);
    // A late event from the retired element settles nothing: its URL is no
    // longer rendered, and the new resolution still needs its own bytes.
    const retired = wrapper.findAll("img").find((img) => img.attributes("src") === preferred);
    expect(retired).toBeUndefined();
    const bundled = republished.attempts[1].resource.url;
    await observeLoad(wrapper, bundled);
    expect(wrapper.find("[data-testid='dream-scene-art']").attributes("src")).toBe(bundled);
    // The reached fact of the refused preferred position stays stated.
    expect(wrapper.find("[data-testid='dream-art-failure']").text()).toBe("此圖片的來源未通過檢查。");
    wrapper.unmount();
  });
  it("rehydrates a same-session external proposal change without clearing unsent chat", async () => {
    const { wrapper } = fixture(state({ thread_choices: THREADS }));
    await reply(wrapper).setValue("尚未送出的交流");
    await wrapper.setProps({ state: state({
      revision: 8, thread_choices: THREADS, thread_id: "synthetic-a", can_choose_thread: false,
      proposal: proposal({ summary: "伺服器保存的願望", themes: ["鐘聲"], exclusions: ["暴力"] }),
    }) });
    expect(reply(wrapper).element.value).toBe("尚未送出的交流");
    expect(wrapper.find("[data-testid='dream-thread-line']").text()).toContain("合成甲");
    expect(wrapper.find(".dream-keepsake__preview").text()).toBe("伺服器保存的願望");
    await activate(wrapper, "main");
    const view = layer(wrapper, "dream-view");
    for (const text of ["伺服器保存的願望", "鐘聲", "暴力", "合成甲"]) expect(view.text()).toContain(text);
  });
  it("keeps an edited summary when the finalized proposal republishes", async () => {
    const { wrapper } = fixture(finalized({ proposal: proposal({ summary: "原本的願望" }) }));
    await openSheet(wrapper);
    const editor = () => layer(wrapper, "dream-sheet").find("textarea");
    expect(editor().element.value).toBe("原本的願望");
    // An untouched field follows the republished proposal.
    await wrapper.setProps({ state: finalized({ revision: 4, proposal: proposal({ summary: "伺服器的願望" }) }) });
    expect(editor().element.value).toBe("伺服器的願望");
    // A field the player has typed into keeps their own text instead.
    await editor().setValue("我還在寫的願望");
    await wrapper.setProps({ state: finalized({ revision: 5, proposal: proposal({ summary: "再一次的願望" }) }) });
    expect(editor().element.value).toBe("我還在寫的願望");
    // Clearing the field restores following the server.
    await editor().setValue("");
    await wrapper.setProps({ state: finalized({ revision: 6, proposal: proposal({ summary: "後來的願望" }) }) });
    expect(editor().element.value).toBe("後來的願望");
  });
});

describe("dream stage review coverage", () => {
  const lockedViews = [
    { connected: false, dispatch: { inFlight: null } },
    { connected: true, dispatch: { inFlight: { requestId: "synthetic" } } },
    { connected: true, mutationsLocked: true, dispatch: { inFlight: null } },
    { connected: true, phase: "reconnecting", dispatch: { inFlight: null } },
  ];
  it("loads a saved finalized proposal on mount as unedited values", async () => {
    const saved = finalized({ drafted: true, proposal: proposal({ summary: "合成願望", themes: ["重逢"] }) });
    const { wrapper, store } = fixture(saved);
    // Nothing is marked as an unsaved edit.
    expect(wrapper.find(".dream-ink").exists()).toBe(false);
    await row(wrapper, "awaken").trigger("click");
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.awaken", SESSION, null);
    await row(wrapper, "confirm").trigger("click");
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.confirm", { ...SESSION,
      direction: { kind: "new_story", thread_id: null, summary: "合成願望", themes: ["重逢"], requirements: [] } }, null);
  });
  it("loads an unchanged proposal as unedited when the session becomes finalized", async () => {
    const wish = proposal({ summary: "合成願望", atmosphere: ["溫柔"] });
    const { wrapper, store } = fixture(state({ completed: 2, remaining: 4, proposal: wish }));
    await wrapper.setProps({ state: finalized({ revision: 3, completed: 2, remaining: 4, proposal: wish }) });
    await flushPromises();
    expect(layer(wrapper, "dream-sheet").exists()).toBe(true);
    await escape(wrapper);
    await row(wrapper, "awaken").trigger("click");
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.awaken", { ...SESSION, revision: 3 }, null);
    await row(wrapper, "confirm").trigger("click");
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.confirm", { ...SESSION, revision: 3,
      direction: { kind: "new_story", thread_id: null, summary: "合成願望", atmosphere: ["溫柔"], requirements: [] } }, null);
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
    await wrapper.setProps({ state: state({ revision: 5, completed: 1, remaining: 5, failure: true, track: { ...state().track, completed: 1 } }) });
    expect(live()).toContain("夢境一時模糊");
  });
  it("keeps the next pip marked while a response is pending", async () => {
    const { wrapper } = fixture(state({ completed: 2, remaining: 4, track: { ...state().track, completed: 2 } }));
    await reply(wrapper).setValue("合成");
    const marked = () => wrapper.findAll(".dream-pip").findIndex((pip) => pip.classes().includes("dream-pip--next"));
    expect(marked()).toBe(2);
    await wrapper.find("form").trigger("submit");
    await wrapper.setProps({ state: state({ revision: 3, completed: 2, remaining: 4, pending: true, can_input: false,
      can_finalize: false, can_choose_thread: false, track: { ...state().track, completed: 2 } }) });
    expect(reply(wrapper).element.value).toBe("");
    expect(marked()).toBe(2);
    expect(wrapper.findAll(".dream-pip--spent")).toHaveLength(2);
  });
  it("disables every dream action while the transport is locked and keeps typed text", async () => {
    for (const view of lockedViews) {
      const store = { view: reactive(view), dispatchAction: vi.fn() };
      const wrapper = mount(DreamPanel, { props: { state: state({ thread_choices: THREADS }), store } });
      for (const name of ["main", "take", "draft", "awaken"]) expect(row(wrapper, name).attributes("disabled")).toBeDefined();
      expect(reply(wrapper).attributes("disabled")).toBeDefined();
      expect(wrapper.find("[data-testid='dream-belong'] [aria-haspopup='listbox']").attributes("disabled")).toBeDefined();
      if (!view.connected) expect(wrapper.find(".dream-reply__caption[role='status']").exists()).toBe(true);
      wrapper.unmount();
      const closed = mount(DreamPanel, { props: { state: finalized({ proposal: proposal({ summary: "合成願望" }) }), store } });
      for (const name of ["main", "confirm", "draft", "awaken"]) expect(row(closed, name).attributes("disabled")).toBeDefined();
      closed.unmount();
    }
  });
  it("captions the converging and final exchange and focuses the confirm row on a live sixth exchange", async () => {
    const converging = { ...state().track, completed: 4, ordinal: 3, level: "高度", converging: true };
    const wish = proposal({ summary: "合成願望" });
    const { wrapper } = fixture(state({ completed: 4, remaining: 2, track: converging, proposal: wish }), { attachTo: document.body });
    const caption = () => wrapper.find(".dream-reply__caption");
    expect(caption().exists()).toBe(true);
    const first = caption().text();
    await wrapper.setProps({ state: state({ revision: 3, completed: 5, remaining: 1, track: { ...converging, completed: 5 }, proposal: wish }) });
    // The last exchange extends the caption.
    expect(caption().text().startsWith(first)).toBe(true);
    expect(caption().text().length).toBeGreaterThan(first.length);
    await wrapper.setProps({ state: capped({ revision: 4, track: { ...converging, completed: 6, ordinal: 4, level: "極限" }, proposal: wish }) });
    await flushPromises();
    expect(document.activeElement).toBe(row(wrapper, "confirm").element);
    // The sixth exchange finalizes without opening the sheet by itself, and a
    // finalized session never shows the converging caption.
    expect(layer(wrapper, "dream-sheet").exists()).toBe(false);
    expect(caption().exists()).toBe(false);
    wrapper.unmount();
  });
  it("focuses the first row on a live sixth exchange without a summary", async () => {
    const { wrapper } = fixture(state({ completed: 5, remaining: 1 }), { attachTo: document.body });
    await wrapper.setProps({ state: capped({ revision: 3 }) });
    await flushPromises();
    expect(document.activeElement).toBe(row(wrapper, "main").element);
    expect(layer(wrapper, "dream-sheet").exists()).toBe(false);
    wrapper.unmount();
  });
  it("names the dialog by its visible title and shows the empty invitation", () => {
    const { wrapper } = fixture();
    expect(wrapper.find(`#${wrapper.attributes("aria-labelledby")}`).text()).toBe("雲上王座之夢");
    expect(wrapper.find(".dream-keepsake__empty").exists()).toBe(true);
    expect(wrapper.find(".dream-keepsake__preview").exists()).toBe(false);
    expect(wrapper.find("[data-testid='dream-stage-indicator']").findAll("li")).toHaveLength(2);
  });
  it("leaves a text field on Escape, focuses the summary on an empty confirm, and makes the stage inert under the sheet", async () => {
    const { wrapper, store } = fixture(state(), { attachTo: document.body });
    reply(wrapper).element.focus();
    await reply(wrapper).trigger("keydown", { key: "Escape" });
    expect(document.activeElement).toBe(wrapper.find("[data-testid='dream-page']").element);
    await wrapper.setProps({ state: finalized({ revision: 3, completed: 6, remaining: 0 }) });
    await row(wrapper, "confirm").trigger("click");
    await flushPromises();
    const sheet = layer(wrapper, "dream-sheet");
    expect(document.activeElement).toBe(sheet.find("textarea").element);
    expect(wrapper.find(".dream-scene__main").attributes("inert")).toBeDefined();
    expect(sheet.find(".dream-field__counter").text()).toBe("0 / 2000");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    wrapper.unmount();
  });
  it("protects an unsaved edit of the finalized wish and refuses an over-length draft", async () => {
    const { wrapper, store } = fixture(finalized({ drafted: true, proposal: proposal({ summary: "合成願望" }) }));
    let sheet = await openSheet(wrapper);
    await sheet.find("textarea").setValue("合成改寫");
    // A revert control appears once the summary differs from the server's.
    expect(sheet.find(".dream-field__foot .dream-link").exists()).toBe(true);
    expect(wrapper.find(".dream-ink").exists()).toBe(true);
    await escape(wrapper);
    await row(wrapper, "awaken").trigger("click");
    await flushPromises();
    expect(statements(wrapper)).toEqual(["edits"]);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await escape(wrapper);
    sheet = await openSheet(wrapper);
    await sheet.find("textarea").setValue("長".repeat(2001));
    await sheetButtons(wrapper)[0].trigger("click");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    expect(sheet.find("[role='alert']").exists()).toBe(true);
  });
  it("keeps edited chips across a republish and new reply text across a failure", async () => {
    const { wrapper } = fixture(finalized({ proposal: proposal({ summary: "合成願望" }) }));
    const sheet = await openSheet(wrapper);
    const themes = sheet.findAll(".dream-tags__box input")[0];
    await themes.setValue("合成主題");
    await themes.trigger("keydown", { key: "Enter" });
    await wrapper.setProps({ state: finalized({ revision: 5, proposal: proposal({ summary: "合成願望", themes: ["伺服器主題"] }) }) });
    expect(sheet.findAll(".dream-tags__chip").map((chip) => chip.text())).toEqual(["合成主題×"]);
    wrapper.unmount();
    const talking = fixture().wrapper;
    await reply(talking).setValue("先送出的話");
    await talking.find("form").trigger("submit");
    await reply(talking).setValue("新打的字");
    await talking.setProps({ state: state({ revision: 6, failure: true }) });
    expect(reply(talking).element.value).toBe("新打的字");
  });
  it("lets unedited lists follow a republished finalized proposal", async () => {
    const { wrapper } = fixture(finalized({ proposal: proposal({ summary: "合成願望", themes: ["重逢"] }) }));
    const sheet = await openSheet(wrapper);
    await wrapper.setProps({ state: finalized({ revision: 3, proposal: proposal({ summary: "合成願望", themes: ["重逢", "信任"], exclusions: ["暴力"] }) }) });
    expect(sheet.findAll(".dream-tags__chip").map((chip) => chip.text())).toEqual(["重逢×", "信任×", "暴力×"]);
  });
  it("names what the awaken check would lose and that the wish is kept", async () => {
    // While conversing an unedited form never asks.
    const quiet = fixture(state({ proposal: proposal({ summary: "合成願望" }) }));
    await row(quiet.wrapper, "awaken").trigger("click");
    expect(quiet.store.dispatchAction).toHaveBeenCalledWith("dream.awaken", SESSION, null);
    quiet.wrapper.unmount();
    // Unsent words with a wish that has no saved draft yet.
    const { wrapper, store } = fixture(state({ proposal: proposal({ summary: "合成願望" }) }));
    await reply(wrapper).setValue("尚未送出的話");
    await row(wrapper, "awaken").trigger("click");
    await flushPromises();
    expect(statements(wrapper)).toEqual(["unsent", "kept"]);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    wrapper.unmount();
    // A saved draft is not announced as kept again.
    const drafted = fixture(state({ drafted: true, proposal: proposal({ summary: "合成願望" }) }));
    await reply(drafted.wrapper).setValue("尚未送出的話");
    await row(drafted.wrapper, "awaken").trigger("click");
    await flushPromises();
    expect(statements(drafted.wrapper)).toEqual(["unsent"]);
  });
});

describe("staged keepsake rows", () => {
  it("opens the read-only view, asks before finalizing and drafts without content while conversing", async () => {
    const { wrapper, store } = fixture(state({ proposal: proposal({ summary: "合成願望" }) }), { attachTo: document.body });
    await activate(wrapper, "main");
    expect(layer(wrapper, "dream-view").exists()).toBe(true);
    expect(layer(wrapper, "dream-sheet").exists()).toBe(false);
    await escape(wrapper);
    expect(layer(wrapper, "dream-view").exists()).toBe(false);
    await activate(wrapper, "take");
    expect(layer(wrapper, "dream-take").exists()).toBe(true);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await escape(wrapper);
    await activate(wrapper, "draft");
    expect(store.dispatchAction).toHaveBeenCalledTimes(1);
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.draft", SESSION, null);
    wrapper.unmount();
  });
  it("opens the edit sheet, drafts and confirms the form when finalized", async () => {
    const wish = proposal({ summary: "合成願望", themes: ["重逢"] });
    const { wrapper, store } = fixture(finalized({ proposal: wish }));
    await activate(wrapper, "main");
    expect(layer(wrapper, "dream-sheet").exists()).toBe(true);
    expect(layer(wrapper, "dream-view").exists()).toBe(false);
    await escape(wrapper);
    const direction = { kind: "new_story", thread_id: null, summary: "合成願望", themes: ["重逢"], requirements: [] };
    await activate(wrapper, "draft");
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.draft", { ...SESSION, direction }, null);
    await activate(wrapper, "confirm");
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.confirm", { ...SESSION, direction }, null);
  });
  it("holds the finalize row while a response is pending", () => {
    const { wrapper } = fixture(state({ pending: true, can_input: false, can_finalize: false, can_choose_thread: false }));
    expect(row(wrapper, "take").attributes("disabled")).toBeDefined();
    expect(row(wrapper, "draft").attributes("disabled")).toBeUndefined();
    expect(row(wrapper, "awaken").attributes("disabled")).toBeUndefined();
  });
  it("activates rows by digit only outside text fields and without modifiers", async () => {
    const { wrapper, store } = fixture(state(), { attachTo: document.body });
    await wrapper.trigger("keydown", { key: "1", ctrlKey: true });
    await flushPromises();
    expect(layer(wrapper, "dream-view").exists()).toBe(false);
    await reply(wrapper).trigger("keydown", { key: "1" });
    await flushPromises();
    expect(layer(wrapper, "dream-view").exists()).toBe(false);
    await wrapper.trigger("keydown", { key: "1" });
    await flushPromises();
    expect(layer(wrapper, "dream-view").exists()).toBe(true);
    await escape(wrapper);
    await wrapper.trigger("keydown", { key: "3" });
    expect(store.dispatchAction).toHaveBeenLastCalledWith("dream.draft", SESSION, null);
    await wrapper.trigger("keydown", { key: "2" });
    await flushPromises();
    expect(layer(wrapper, "dream-take").exists()).toBe(true);
    wrapper.unmount();
  });
  it("marks the thread line locked and names the new, chosen or vanished thread", () => {
    const open = fixture(state({ thread_choices: THREADS })).wrapper;
    expect(open.find("[data-testid='dream-thread-lock']").exists()).toBe(false);
    open.unmount();
    const lines = ["", "synthetic-a", "synthetic-gone"].map((threadId) => {
      const { wrapper } = fixture(state({ completed: 1, remaining: 5, can_choose_thread: false, thread_choices: THREADS,
        thread_id: threadId || null, track: { ...state().track, completed: 1 } }));
      expect(wrapper.find("[data-testid='dream-thread-lock']").exists()).toBe(true);
      const text = wrapper.find("[data-testid='dream-thread-line']").text();
      wrapper.unmount();
      return text;
    });
    expect(lines[1]).toContain("合成甲");
    for (const text of [lines[0], lines[2]]) {
      expect(text).not.toContain("合成甲");
      expect(text).not.toContain("合成乙");
    }
    expect(new Set(lines).size).toBe(3);
  });
  it("shows the draft toast only once a newer committed state reports a saved draft", async () => {
    const { wrapper } = fixture(state({ proposal: proposal({ summary: "合成願望" }) }));
    await activate(wrapper, "draft");
    expect(wrapper.find(".dream-toast").exists()).toBe(false);
    // A refused draft republishes a newer state without a saved draft.
    await wrapper.setProps({ state: state({ revision: 3, proposal: proposal({ summary: "合成願望" }) }) });
    expect(wrapper.find(".dream-toast").exists()).toBe(false);
    await activate(wrapper, "draft");
    await wrapper.setProps({ state: state({ revision: 4, drafted: true, proposal: proposal({ summary: "合成願望" }) }) });
    expect(wrapper.find(".dream-toast").attributes("role")).toBe("status");
    expect(wrapper.find(".dream-live").text()).toBe(wrapper.find(".dream-toast").text());
  });
});

describe("whole-wish view", () => {
  const WISH = proposal({ summary: "合成願望", themes: ["重逢"], exclusions: ["暴力"], requirements: REQUIREMENTS });
  it("renders every proposal field as plain text with placeholders and no form fields", async () => {
    const { wrapper } = fixture(state({ proposal: WISH }), { attachTo: document.body });
    await activate(wrapper, "main");
    const view = layer(wrapper, "dream-view");
    expect(view.attributes("role")).toBe("dialog");
    expect(view.attributes("aria-modal")).toBe("true");
    for (const text of ["合成願望", "重逢", "暴力", "合成南門", "合成女孩", "合成委託"]) expect(view.text()).toContain(text);
    expect(view.findAll("input, textarea, select")).toHaveLength(0);
    // Atmosphere, participants and emphasis are empty.
    expect(view.findAll(".dream-scroll__none")).toHaveLength(3);
    expect(wrapper.find(".dream-scene__main").attributes("inert")).toBeDefined();
    expect(view.element.contains(document.activeElement)).toBe(true);
    wrapper.unmount();
    const empty = fixture(state(), { attachTo: document.body }).wrapper;
    await activate(empty, "main");
    // The summary, the requirement rows and the five lists all show placeholders.
    expect(layer(empty, "dream-view").findAll(".dream-scroll__none")).toHaveLength(7);
    empty.unmount();
  });
  it("closes the view and opens the finalize confirmation from its finalize control", async () => {
    const { wrapper, store } = fixture(state({ proposal: WISH }), { attachTo: document.body });
    await activate(wrapper, "main");
    await layer(wrapper, "dream-view").find("[data-testid='dream-view-take']").trigger("click");
    await flushPromises();
    expect(layer(wrapper, "dream-view").exists()).toBe(false);
    expect(layer(wrapper, "dream-take").exists()).toBe(true);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    wrapper.unmount();
  });
  it("follows a republished proposal while open", async () => {
    const { wrapper } = fixture(state({ proposal: WISH }));
    await activate(wrapper, "main");
    await wrapper.setProps({ state: state({ revision: 3, proposal: proposal({ summary: "新的願望", atmosphere: ["溫柔"] }) }) });
    const view = layer(wrapper, "dream-view");
    expect(view.text()).toContain("新的願望");
    expect(view.text()).toContain("溫柔");
    expect(view.text()).not.toContain("合成南門");
  });
});

describe("finalize confirmation", () => {
  const midway = () => state({ completed: 3, remaining: 3, track: { ...state().track, completed: 3, ordinal: 2, level: "中等" } });
  const stay = (wrapper) => layer(wrapper, "dream-take").find(".dream-confirm__actions button");
  it("names the exchanges given up and rests focus on staying", async () => {
    const { wrapper, store } = fixture(midway(), { attachTo: document.body });
    await activate(wrapper, "take");
    const take = layer(wrapper, "dream-take");
    expect(take.attributes("role")).toBe("alertdialog");
    expect(take.find(".dream-confirm__cost").attributes("data-remaining")).toBe("3");
    expect(take.find(".dream-confirm__cost").text()).toContain("3");
    expect(document.activeElement).toBe(stay(wrapper).element);
    await stay(wrapper).trigger("click");
    await flushPromises();
    expect(layer(wrapper, "dream-take").exists()).toBe(false);
    await activate(wrapper, "take");
    await escape(wrapper);
    expect(layer(wrapper, "dream-take").exists()).toBe(false);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    wrapper.unmount();
  });
  it("cannot finalize and submit from a repeated key", async () => {
    const { wrapper, store } = fixture(midway(), { attachTo: document.body });
    await wrapper.trigger("keydown", { key: "2" });
    await flushPromises();
    expect(document.activeElement).toBe(stay(wrapper).element);
    await stay(wrapper).trigger("keydown", { key: "2" });
    await flushPromises();
    expect(document.activeElement).toBe(stay(wrapper).element);
    await stay(wrapper).trigger("click");
    await flushPromises();
    expect(layer(wrapper, "dream-take").exists()).toBe(false);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    wrapper.unmount();
  });
  it("dispatches exactly one finalize from its explicit control", async () => {
    const { wrapper, store } = fixture(midway());
    await activate(wrapper, "take");
    await layer(wrapper, "dream-take").find("[data-testid='dream-take-finalize']").trigger("click");
    await flushPromises();
    expect(store.dispatchAction).toHaveBeenCalledTimes(1);
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.finalize", SESSION, null);
    expect(layer(wrapper, "dream-take").exists()).toBe(false);
  });
  it("opens the edit sheet when the session becomes finalized before the cap", async () => {
    const { wrapper } = fixture(midway(), { attachTo: document.body });
    await wrapper.setProps({ state: finalized({ revision: 3, completed: 3, remaining: 3, track: midway().track }) });
    await flushPromises();
    const sheet = layer(wrapper, "dream-sheet");
    expect(sheet.exists()).toBe(true);
    expect(document.activeElement).toBe(sheet.find("textarea").element);
    expect(wrapper.find("form").exists()).toBe(false);
    wrapper.unmount();
  });
});

describe("thread choice", () => {
  const choosing = () => state({ thread_choices: THREADS });
  const pick = (wrapper) => wrapper.find("[data-testid='dream-belong'] [aria-haspopup='listbox']");
  const options = (wrapper) => wrapper.findAll("[data-testid='dream-belong'] [role='option']");
  it("dispatches a newly chosen thread and returns focus to the reply field", async () => {
    const { wrapper, store } = fixture(choosing(), { attachTo: document.body });
    expect(pick(wrapper).attributes("aria-expanded")).toBe("false");
    await pick(wrapper).trigger("click");
    await flushPromises();
    expect(pick(wrapper).attributes("aria-expanded")).toBe("true");
    expect(options(wrapper)).toHaveLength(3);
    // The new story is preselected and focused first.
    expect(options(wrapper)[0].attributes("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(options(wrapper)[0].element);
    await options(wrapper)[0].trigger("keydown", { key: "ArrowDown" });
    expect(document.activeElement).toBe(options(wrapper)[1].element);
    // Digits do not reach the keepsake rows while the list is open.
    await options(wrapper)[1].trigger("keydown", { key: "1" });
    await flushPromises();
    expect(layer(wrapper, "dream-view").exists()).toBe(false);
    expect(options(wrapper)).toHaveLength(3);
    // Escape closes the list without choosing and returns to the picker.
    await wrapper.trigger("keydown", { key: "Escape" });
    await flushPromises();
    expect(options(wrapper)).toHaveLength(0);
    expect(document.activeElement).toBe(pick(wrapper).element);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    await pick(wrapper).trigger("click");
    await flushPromises();
    await options(wrapper)[2].trigger("click");
    await flushPromises();
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.choose_thread", { ...SESSION, thread_id: "synthetic-b" }, null);
    expect(options(wrapper)).toHaveLength(0);
    expect(document.activeElement).toBe(reply(wrapper).element);
    wrapper.unmount();
  });
  it("dispatches nothing when the chosen option is reselected", async () => {
    const { wrapper, store } = fixture(choosing());
    await pick(wrapper).trigger("click");
    await flushPromises();
    await options(wrapper)[0].trigger("click");
    wrapper.unmount();
    const chosen = fixture(state({ thread_choices: THREADS, thread_id: "synthetic-a" }));
    await pick(chosen.wrapper).trigger("click");
    await flushPromises();
    expect(options(chosen.wrapper)[1].attributes("aria-selected")).toBe("true");
    await options(chosen.wrapper)[1].trigger("click");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    expect(chosen.store.dispatchAction).not.toHaveBeenCalled();
  });
  it("closes the list only when focus really moves elsewhere", async () => {
    const { wrapper, store } = fixture(choosing(), { attachTo: document.body });
    await pick(wrapper).trigger("click");
    await flushPromises();
    // A pointer press that moves no focus keeps the list open for its click.
    await options(wrapper)[1].trigger("focusout", { relatedTarget: null });
    expect(options(wrapper)).toHaveLength(3);
    await options(wrapper)[1].trigger("focusout", { relatedTarget: options(wrapper)[2].element });
    expect(options(wrapper)).toHaveLength(3);
    await options(wrapper)[1].trigger("focusout", { relatedTarget: row(wrapper, "awaken").element });
    expect(options(wrapper)).toHaveLength(0);
    expect(store.dispatchAction).not.toHaveBeenCalled();
    wrapper.unmount();
  });
  it("sends only the message when the player speaks without choosing", async () => {
    const { wrapper, store } = fixture(choosing());
    await reply(wrapper).setValue("合成");
    await reply(wrapper).trigger("keydown", { key: "Enter" });
    expect(store.dispatchAction).toHaveBeenCalledTimes(1);
    expect(store.dispatchAction.mock.calls[0][0]).toBe("dream.say");
  });
  it("is absent with nothing offered or once choosing is locked", () => {
    for (const value of [state(), state({ thread_choices: THREADS, can_choose_thread: false })]) {
      const { wrapper } = fixture(value);
      expect(wrapper.find("[data-testid='dream-belong']").exists()).toBe(false);
      wrapper.unmount();
    }
    const { wrapper } = fixture(choosing());
    expect(wrapper.find("[data-testid='dream-belong']").exists()).toBe(true);
  });
});

describe("finalized edit sheet", () => {
  it("sends the same payload shape from both sheet controls", async () => {
    const wish = proposal({ summary: "合成願望", themes: ["重逢"], exclusions: ["暴力"], requirements: REQUIREMENTS });
    const { wrapper, store } = fixture(finalized({ thread_choices: THREADS, thread_id: "synthetic-a", proposal: wish }));
    await openSheet(wrapper);
    await sheetButtons(wrapper)[1].trigger("click");
    await sheetButtons(wrapper)[0].trigger("click");
    const direction = { kind: "thread_direction", thread_id: "synthetic-a", summary: "合成願望",
      themes: ["重逢"], exclusions: ["暴力"], requirements: REQUIREMENTS };
    expect(store.dispatchAction.mock.calls).toEqual([
      ["dream.confirm", { ...SESSION, direction }, null],
      ["dream.draft", { ...SESSION, direction }, null],
    ]);
  });
  it("shows the chosen thread as fixed text with no control that changes it", async () => {
    const { wrapper } = fixture(finalized({ thread_choices: THREADS, thread_id: "synthetic-a", proposal: proposal({ summary: "合成願望" }) }));
    const sheet = await openSheet(wrapper);
    expect(sheet.find("[data-testid='dream-thread-fixed']").text()).toContain("合成甲");
    expect(sheet.findAll("input[type='radio'], select, [role='option'], [role='listbox']")).toHaveLength(0);
    expect(sheet.find("[data-testid='dream-thread-release']").exists()).toBe(false);
  });
  it("releases an ended thread to a new story", async () => {
    const { wrapper, store } = fixture(finalized({ thread_choices: THREADS, thread_id: "synthetic-gone", proposal: proposal({ summary: "合成願望" }) }));
    const sheet = await openSheet(wrapper);
    await sheet.find("[data-testid='dream-thread-release']").trigger("click");
    expect(sheet.find("[data-testid='dream-thread-release']").exists()).toBe(false);
    await sheetButtons(wrapper)[1].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.confirm", { ...SESSION,
      direction: { kind: "new_story", thread_id: null, summary: "合成願望", requirements: [] } }, null);
  });
  it("cannot be reached while conversing", async () => {
    const { wrapper, store } = fixture(state({ proposal: proposal({ summary: "合成願望" }) }));
    expect(row(wrapper, "confirm").exists()).toBe(false);
    await activate(wrapper, "main");
    expect(layer(wrapper, "dream-sheet").exists()).toBe(false);
    await escape(wrapper);
    await wrapper.trigger("keydown", { key: "Enter", ctrlKey: true });
    await activate(wrapper, "take");
    await escape(wrapper);
    expect(layer(wrapper, "dream-sheet").exists()).toBe(false);
    expect(store.dispatchAction).not.toHaveBeenCalled();
  });
});

describe("shown experience requirements", () => {
  const labelled = (list) => list.findAll("li").map((item) => [item.find("span").text(), item.text()]);
  // A sheet row is a kind select and a text input: read the chosen option's
  // label and the typed text, not every option the select carries.
  const sheetRowsOf = (sheet) => sheet.findAll(".dream-requirements__row").map((item) => {
    const select = item.find("select").element;
    const label = select.options[select.selectedIndex].text;
    return [label, label + item.find("input").element.value];
  });
  it("lists the rows with readable kind labels in the view and the sheet and sends exactly those rows", async () => {
    const wish = proposal({ summary: "合成願望", requirements: REQUIREMENTS });
    const talking = fixture(state({ proposal: wish })).wrapper;
    await activate(talking, "main");
    const viewRows = labelled(layer(talking, "dream-view").find("[data-testid='dream-view-requirements']"));
    talking.unmount();
    const { wrapper, store } = fixture(finalized({ proposal: wish }));
    const sheet = await openSheet(wrapper);
    const sheetRows = sheetRowsOf(sheet);
    for (const rows of [viewRows, sheetRows]) {
      expect(rows).toHaveLength(3);
      rows.forEach(([label, text], index) => {
        expect(label.length).toBeGreaterThan(0);
        expect(label).not.toBe(REQUIREMENTS[index].kind);
        expect(text).toBe(label + REQUIREMENTS[index].text);
      });
      expect(new Set(rows.map(([label]) => label)).size).toBe(3);
    }
    expect(sheetRows).toEqual(viewRows);
    await sheetButtons(wrapper)[1].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.confirm", { ...SESSION,
      direction: { kind: "new_story", thread_id: null, summary: "合成願望", requirements: REQUIREMENTS } }, null);
    wrapper.unmount();
    // Without rows the sheet still offers the section, empty, to add one.
    const plain = fixture(finalized({ proposal: proposal({ summary: "合成願望" }) })).wrapper;
    const empty = (await openSheet(plain)).find("[data-testid='dream-requirements']");
    expect(empty.findAll(".dream-requirements__row")).toHaveLength(0);
    expect(empty.find("[data-testid='dream-requirement-add']").exists()).toBe(true);
  });
  it("shows republished rows without clearing unsent words", async () => {
    const { wrapper } = fixture(state({ proposal: proposal({ summary: "合成願望", requirements: REQUIREMENTS }) }));
    await reply(wrapper).setValue("尚未送出的話");
    await wrapper.setProps({ state: state({ revision: 3, proposal: proposal({ summary: "合成願望", requirements: [{ kind: "place", text: "合成北門" }] }) }) });
    expect(reply(wrapper).element.value).toBe("尚未送出的話");
    await activate(wrapper, "main");
    const list = layer(wrapper, "dream-view").find("[data-testid='dream-view-requirements']");
    expect(list.findAll("li")).toHaveLength(1);
    expect(list.text()).toContain("合成北門");
  });
});

// A change report: every field untouched unless overridden.
function report({ summary = null, lists = {}, requirements = { added: [], removed: [] } } = {}) {
  const all = Object.fromEntries(Object.keys(LISTS).map((key) => [key, { added: [], removed: [], ...(lists[key] || {}) }]));
  return { summary, lists: all, requirements };
}
const ink = (wrapper) => wrapper.find("[data-testid='dream-ink']");
const cardWish = (wrapper) => wrapper.find(".dream-keepsake__preview");

describe("keepsake change line", () => {
  const CHANGED = report({ summary: "changed", lists: { themes: { added: ["重逢"], removed: ["離別"] } } });
  it("names the changed fields with their added and removed counts", () => {
    const { wrapper } = fixture(state({ completed: 1, remaining: 5, track: { ...state().track, completed: 1 },
      proposal: proposal({ summary: "合成願望", themes: ["重逢"] }), changes: CHANGED }));
    const strokes = ink(wrapper).findAll(".dream-ink__stroke");
    expect(strokes.map((item) => item.attributes("data-stroke"))).toEqual(["summary", "themes"]);
    expect(strokes[0].text()).toBe("願望更動");
    expect(strokes[1].text()).toBe("主題＋1−1");
    expect(ink(wrapper).text()).toContain("女神為你改了");
    for (const name of ["氛圍", "人物", "描寫", "避開", "需求"]) expect(ink(wrapper).text()).not.toContain(name);
  });
  it("states that nothing changed in words different from a changed turn", () => {
    const changed = fixture(state({ changes: CHANGED, proposal: proposal({ summary: "合成願望" }) })).wrapper;
    const still = fixture(state({ changes: report(), proposal: proposal({ summary: "合成願望" }) })).wrapper;
    expect(still.find(".dream-ink__stroke").exists()).toBe(false);
    expect(ink(still).text()).toContain("女神這次沒有更動願望");
    expect(ink(still).text()).not.toBe(ink(changed).text());
  });
  it("renders no change line without a report", () => {
    const { wrapper } = fixture(state({ proposal: proposal({ summary: "合成願望" }) }));
    expect(ink(wrapper).exists()).toBe(false);
  });
  it("holds the wish and its line until the last beat has been read in full", async () => {
    vi.useFakeTimers();
    try {
      const store = { view: reactive({ connected: true, motionLevel: "full", textSpeed: "normal", dispatch: { inFlight: null } }), dispatchAction: vi.fn() };
      const before = state({ completed: 1, remaining: 5, track: { ...state().track, completed: 1 }, scene: "", dialogue: "舊台詞",
        proposal: proposal({ summary: "舊願望" }), changes: report({ summary: "formed" }) });
      const wrapper = mount(DreamPanel, { props: { state: before, store } });
      expect(ink(wrapper).text()).toContain("願望成形");
      await wrapper.setProps({ state: state({ revision: 3, completed: 2, remaining: 4, track: { ...state().track, completed: 2 },
        scene: "合成場景敘述", dialogue: "合成台詞", proposal: proposal({ summary: "新願望", themes: ["重逢"] }),
        changes: report({ summary: "changed", lists: { themes: { added: ["重逢"] } } }) }) });
      await nextTick();
      // Her words are still being presented: the card keeps the previous wish.
      expect(cardWish(wrapper).text()).toBe("舊願望");
      expect(ink(wrapper).text()).toContain("願望成形");
      const page = wrapper.find("[data-testid='dream-page']");
      for (let step = 0; step < 6 && cardWish(wrapper).text() === "舊願望"; step += 1) {
        expect(ink(wrapper).text()).toContain("願望成形");
        await page.trigger("click");
        await nextTick();
      }
      expect(page.text()).toBe("合成台詞");
      expect(cardWish(wrapper).text()).toBe("新願望");
      expect(ink(wrapper).text()).toContain("願望更動");
      expect(ink(wrapper).text()).toContain("主題＋1");
      wrapper.unmount();
    } finally {
      vi.useRealTimers();
    }
  });
  it("announces a settled line once and not again on a republish of the same report", async () => {
    const { wrapper } = fixture(state({ scene: "", dialogue: "" }));
    const live = () => wrapper.find(".dream-live").text();
    const next = (revision) => state({ revision, completed: 1, remaining: 5, track: { ...state().track, completed: 1 },
      scene: "", dialogue: "合成台詞", proposal: proposal({ summary: "合成願望" }), changes: report({ summary: "formed" }) });
    await wrapper.setProps({ state: next(3) });
    await nextTick();
    expect(live()).toContain("王座上的女神說：合成台詞");
    expect(live().split("女神為你改了：願望成形。")).toHaveLength(2);
    await escape(wrapper);
    const prompt = live();
    expect(prompt).not.toContain("女神為你改了");
    await wrapper.setProps({ state: next(4) });
    await nextTick();
    expect(live()).toBe(prompt);
  });
  it("shows the committed report at once on mount", () => {
    const { wrapper } = fixture(state({ completed: 2, remaining: 4, track: { ...state().track, completed: 2 },
      proposal: proposal({ summary: "合成願望" }), changes: report({ summary: "changed" }) }));
    expect(cardWish(wrapper).text()).toBe("合成願望");
    expect(ink(wrapper).text()).toContain("願望更動");
  });
  it("shows no change line once finalized", () => {
    const { wrapper } = fixture(finalized({ proposal: proposal({ summary: "合成願望" }), changes: CHANGED }));
    expect(ink(wrapper).exists()).toBe(false);
  });
});

describe("whole-wish change marks", () => {
  const field = (wrapper, key) => layer(wrapper, "dream-view").find(`[data-field='${key}']`);
  async function viewOf(changes, extra = {}) {
    const { wrapper } = fixture(state({ changes, proposal: proposal({ summary: "合成願望", themes: ["重逢", "鐘聲"], ...extra }) }));
    await activate(wrapper, "main");
    return wrapper;
  }
  it("marks the changed field, the added item and names the removed one under it", async () => {
    const wrapper = await viewOf(report({ lists: { themes: { added: ["重逢"], removed: ["離別"] } } }));
    const themes = field(wrapper, "themes");
    expect(themes.classes()).toContain("dream-scroll--touched");
    expect(themes.find("h4 .dream-scroll__mark").text()).toContain("✎");
    const items = themes.findAll(".dream-scroll__tags > span");
    expect(items[0].text()).toBe("重逢新添");
    expect(items[1].text()).toBe("鐘聲");
    const gone = themes.find("[data-testid='dream-view-removed']");
    expect(gone.text()).toContain("劃去");
    expect(gone.findAll("s").map((item) => item.text())).toEqual(["離別"]);
  });
  it("names a removed requirement row under the requirement section", async () => {
    const wrapper = await viewOf(report({ requirements: { added: [REQUIREMENTS[1]], removed: [{ kind: "place", text: "合成北門" }] } }),
      { requirements: [REQUIREMENTS[0], REQUIREMENTS[1]] });
    const rows = field(wrapper, "requirements");
    expect(rows.find("h4 .dream-scroll__mark").exists()).toBe(true);
    expect(rows.find("[data-testid='dream-view-removed'] s").text()).toBe("合成北門");
    const items = rows.findAll("[data-testid='dream-view-requirements'] li");
    expect(items[0].find("b").exists()).toBe(false);
    expect(items[1].find("b").text()).toBe("新添");
  });
  it("leaves untouched fields unmarked", async () => {
    const wrapper = await viewOf(report({ lists: { themes: { added: ["重逢"] } } }));
    for (const key of ["summary", "requirements", "atmosphere", "participants", "emphasis", "exclusions"]) {
      const section = field(wrapper, key);
      expect(section.classes()).not.toContain("dream-scroll--touched");
      expect(section.find(".dream-scroll__mark").exists()).toBe(false);
      expect(section.find("[data-testid='dream-view-removed']").exists()).toBe(false);
    }
  });
  it("marks a formed summary differently from a changed one", async () => {
    const formed = field(await viewOf(report({ summary: "formed" })), "summary").find(".dream-scroll__mark").text();
    const changed = field(await viewOf(report({ summary: "changed" })), "summary").find(".dream-scroll__mark").text();
    expect(formed).toContain("✎");
    expect(changed).toContain("✎");
    expect(formed).not.toBe(changed);
  });
});

describe("editable requirement rows", () => {
  const sheetRows = (wrapper) => layer(wrapper, "dream-sheet").findAll(".dream-requirements__row");
  const textOf = (item) => item.find("input");
  it("adds, edits and removes rows and drafts exactly the remaining rows in order", async () => {
    const { wrapper, store } = fixture(finalized({ proposal: proposal({ summary: "合成願望", requirements: REQUIREMENTS }) }), { attachTo: document.body });
    const sheet = await openSheet(wrapper);
    expect(sheet.find("[data-testid='dream-requirement-count']").text()).toBe("3 / 8");
    await sheet.find("[data-testid='dream-requirement-add']").trigger("click");
    await flushPromises();
    expect(sheetRows(wrapper)).toHaveLength(4);
    const added = sheetRows(wrapper)[3];
    expect(added.find("select").element.value).toBe("place");
    expect(document.activeElement).toBe(textOf(added).element);
    await added.find("select").setValue("private_commission");
    await textOf(added).setValue("  合成新需求 ");
    await sheetRows(wrapper)[0].find(".dream-requirements__remove").trigger("click");
    expect(sheet.find("[data-testid='dream-requirement-count']").text()).toBe("3 / 8");
    await sheetButtons(wrapper)[0].trigger("click");
    expect(store.dispatchAction).toHaveBeenCalledWith("dream.draft", { ...SESSION, direction: { kind: "new_story", thread_id: null,
      summary: "合成願望", requirements: [REQUIREMENTS[1], REQUIREMENTS[2], { kind: "private_commission", text: "合成新需求" }] } }, null);
    wrapper.unmount();
  });
  it("counts eight of eight and offers no add control at the limit", async () => {
    const seven = Array.from({ length: 7 }, (_, index) => ({ kind: "place", text: `合成地點${index}` }));
    const { wrapper } = fixture(finalized({ proposal: proposal({ summary: "合成願望", requirements: seven }) }));
    const sheet = await openSheet(wrapper);
    await sheet.find("[data-testid='dream-requirement-add']").trigger("click");
    expect(sheet.find("[data-testid='dream-requirement-count']").text()).toBe("8 / 8");
    expect(sheet.find("[data-testid='dream-requirement-add']").exists()).toBe(false);
  });
  it("blocks draft and confirm on a blank row, marks it and keeps every other value", async () => {
    const { wrapper, store } = fixture(finalized({ proposal: proposal({ summary: "合成願望", themes: ["重逢"], requirements: REQUIREMENTS }) }), { attachTo: document.body });
    const sheet = await openSheet(wrapper);
    await sheet.find("textarea").setValue("合成新願望");
    await textOf(sheetRows(wrapper)[1]).setValue("   ");
    for (const control of [1, 0]) {
      await sheetButtons(wrapper)[control].trigger("click");
      await flushPromises();
      expect(store.dispatchAction).not.toHaveBeenCalled();
      const invalid = sheetRows(wrapper)[1];
      expect(textOf(invalid).attributes("aria-invalid")).toBe("true");
      expect(invalid.find("[role='alert']").text()).toBe("請填上內容");
      expect(document.activeElement).toBe(textOf(invalid).element);
      for (const index of [0, 2]) expect(textOf(sheetRows(wrapper)[index]).attributes("aria-invalid")).toBeUndefined();
      expect(textOf(sheetRows(wrapper)[0]).element.value).toBe(REQUIREMENTS[0].text);
      expect(textOf(sheetRows(wrapper)[2]).element.value).toBe(REQUIREMENTS[2].text);
      expect(layer(wrapper, "dream-sheet").find("textarea").element.value).toBe("合成新願望");
      expect(layer(wrapper, "dream-sheet").find(".dream-tags__chip").text()).toContain("重逢");
    }
    // The card's confirm row opens the closed sheet on the same refusal.
    await escape(wrapper);
    await activate(wrapper, "confirm");
    expect(store.dispatchAction).not.toHaveBeenCalled();
    expect(layer(wrapper, "dream-sheet").exists()).toBe(true);
    expect(document.activeElement).toBe(textOf(sheetRows(wrapper)[1]).element);
    // Filling the row clears its mark.
    await textOf(sheetRows(wrapper)[1]).setValue("合成女孩");
    expect(textOf(sheetRows(wrapper)[1]).attributes("aria-invalid")).toBeUndefined();
    wrapper.unmount();
  });
  it("names an unsaved row edit in the awaken check", async () => {
    const { wrapper } = fixture(finalized({ proposal: proposal({ summary: "合成願望", requirements: REQUIREMENTS }) }), { attachTo: document.body });
    await openSheet(wrapper);
    await sheetRows(wrapper)[0].find("select").setValue("new_character");
    await escape(wrapper);
    await activate(wrapper, "awaken");
    expect(statements(wrapper)).toContain("edits");
    wrapper.unmount();
  });
  it("lets unedited rows follow a republish and keeps edited ones", async () => {
    const { wrapper } = fixture(finalized({ proposal: proposal({ summary: "合成願望", requirements: REQUIREMENTS }) }));
    await openSheet(wrapper);
    const values = () => sheetRows(wrapper).map((item) => [item.find("select").element.value, textOf(item).element.value]);
    await wrapper.setProps({ state: finalized({ revision: 3, proposal: proposal({ summary: "合成願望", requirements: [{ kind: "place", text: "合成北門" }] }) }) });
    expect(values()).toEqual([["place", "合成北門"]]);
    await textOf(sheetRows(wrapper)[0]).setValue("合成西門");
    await wrapper.setProps({ state: finalized({ revision: 4, proposal: proposal({ summary: "合成願望", requirements: REQUIREMENTS }) }) });
    expect(values()).toEqual([["place", "合成西門"]]);
  });
});
