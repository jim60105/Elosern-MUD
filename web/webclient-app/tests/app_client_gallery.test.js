// The gallery window mounted in the client (gallery-window-mount): the 圖庫
// tool opens it under the `gallery` drawer key, outside the overlay host,
// and every gallery mutation leaves through the store's single dispatch
// entry. A real pinia store, the real protocol validators and a fake sender;
// committed panels arrive as snapshots.
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../AppClient.vue";
import GalleryGenerateDrawer from "../components/GalleryGenerateDrawer.vue";
import GalleryStageTransformModal from "../components/GalleryStageTransformModal.vue";
import { useElosernStore } from "../stores/elosern.js";
import { GALLERY_V4_MINE as GALLERY_SAMPLE } from "../stories/gallery-fixtures-v4.js";
import * as fx from "./store/protocol_fixtures.js";

const UNAVAILABLE = { schema_version: 4, available: false, reason: { code: "gallery_unavailable", message: "圖庫資料暫時無法使用。" } };

describe("gallery application integration", () => {
  let store, sender, wrapper;
  const button = (surface, text) => surface.findAll("button").find((item) => item.text() === text);
  const win = () => wrapper.get('[data-testid="gallery-window"]');
  const trayItem = (id) => win().get(`[data-testid="gallery-tray-item"][data-item-id="${id}"]`);
  const footer = (key) => wrapper.find(`[data-testid="gallery-page__${key}"]`);
  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    wrapper = mount(AppClient, { attachTo: document.body });
    store.beginTransport(1);
    store.setConnected(true);
  });
  afterEach(() => { wrapper.unmount(); document.body.replaceChildren(); });
  async function snapshot(gallery, revision = 1) {
    const panels = { status: fx.statusPanel(), exploration: fx.explorationPanel(), context_actions: fx.explorationActions() };
    if (gallery) panels.gallery = gallery;
    const response = store.receive(1, "ui_snapshot", [fx.snapshot({ panels, revision })]);
    expect(response.accepted).toBe(true);
    await wrapper.vm.$nextTick();
  }
  async function open() {
    await snapshot(GALLERY_SAMPLE);
    const opener = wrapper.get('[data-testid="gallery-opener"]');
    opener.element.focus();
    await opener.trigger("click");
    return opener;
  }
  async function loadFigure(modal) {
    // The shared lifecycle reports success only for a REAL decoded size.
    const figure = modal.get(".stage-transform__figure");
    Object.defineProperty(figure.element, "naturalWidth", { value: 768, configurable: true });
    Object.defineProperty(figure.element, "naturalHeight", { value: 1024, configurable: true });
    await figure.trigger("load");
  }
  // Every test in this file pays the mount cost of the whole AppClient on a
  // loaded CI runner (measured 5.3–12.8s per test against vitest's 5s
  // default, with the same tests completing in well under a second locally),
  // so each one carries this file's explicit budget.
  it("opens the window from the 圖庫 tool under the gallery drawer key and restores focus on Escape", async () => {
    await snapshot(null);
    expect(wrapper.find('[data-testid="gallery-opener"]').exists()).toBe(false);
    await snapshot(GALLERY_SAMPLE, 2);
    const opener = wrapper.get('[data-testid="gallery-opener"]');
    expect(opener.attributes("aria-label")).toBe("圖庫");
    expect(opener.element.closest('[data-testid="nav-tools"]')).not.toBeNull();
    expect(opener.element.closest('[data-testid="command-line"]')).toBeNull();
    opener.element.focus();
    await opener.trigger("click");
    expect(store.view.hudDrawer).toBe("gallery");
    expect(store.view.hudOverlay).toBeNull();
    expect(wrapper.find('[data-testid="overlay-host"]').exists()).toBe(false);
    expect(win().element.closest('[data-drawer-key="gallery"]')).not.toBeNull();
    expect(wrapper.get(".drawer-header__title").text()).toBe("圖庫");

    // Escape on the wall closes the window and returns focus to the tool.
    const tile = win().get(`[data-testid="gallery-subject"][data-subject-key="${GALLERY_SAMPLE.selected}"]`);
    tile.element.focus();
    await tile.trigger("keydown", { key: "Escape" });
    await flushPromises();
    expect(wrapper.find('[data-testid="gallery-window"]').exists()).toBe(false);
    expect(store.view.hudDrawer).toBeNull();
    expect(document.activeElement).toBe(opener.element);
    expect(sender.sent.actions).toEqual([]);
  }, 20000);

  it("closes an open overlay when the window opens and the window when an overlay opens", async () => {
    await snapshot(GALLERY_SAMPLE);
    await wrapper.get('[data-testid="nav-tool-help"]').trigger("click");
    expect(store.view.hudOverlay).toBe("help");
    await wrapper.get('[data-testid="gallery-opener"]').trigger("click");
    expect(store.view.hudOverlay).toBeNull();
    expect(store.view.hudDrawer).toBe("gallery");
    expect(wrapper.find('[data-testid="overlay-host"]').exists()).toBe(false);
    store.openOverlay("help");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBeNull();
    expect(wrapper.find('[data-testid="gallery-window"]').exists()).toBe(false);
    expect(store.openOverlay("gallery")).toBe(false);
  }, 20000);

  it("locks the open window with the committed reason when the panel becomes unavailable", async () => {
    await open();
    await snapshot(UNAVAILABLE, 3);
    // The tool leaves the bar; the open window stays and shows the reason.
    expect(wrapper.find('[data-testid="gallery-opener"]').exists()).toBe(false);
    expect(store.view.hudDrawer).toBe("gallery");
    expect(win().text()).toContain(UNAVAILABLE.reason.message);
    expect(win().find('[data-testid="gallery-window__rail"]').exists()).toBe(false);
    expect(win().find('[data-testid="gallery-wall"]').exists()).toBe(false);
    expect(win().find('[data-testid="gallery-page"]').exists()).toBe(false);
    // The drawer's close control is the only control left: no gallery
    // action can be sent from the locked window.
    const drawer = wrapper.get('[data-drawer-key="gallery"]');
    expect(drawer.findAll("button").map((item) => item.attributes("data-testid"))).toEqual(["hud-drawer-close"]);
    expect(sender.sent.actions).toEqual([]);
  }, 20000);

  it("confirms deletion through the shared entry and blocks concurrent mutation", async () => {
    await open();
    const card = GALLERY_SAMPLE.cards[0];
    await trayItem(card.image_id).trigger("click");
    await footer("delete").trigger("click");
    await footer("cancel").trigger("click");
    expect(sender.sent.actions).toEqual([]);
    await footer("delete").trigger("click");
    await footer("confirm-delete").trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].action_id).toBe("gallery.card.delete");
    expect(sender.sent.actions[0].payload).toEqual({ subject_key: GALLERY_SAMPLE.selected, image_id: card.image_id });
    // While the delete is in flight the 生成新圖 tile opens nothing.
    await trayItem("generate").trigger("click");
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    expect(sender.sent.actions).toHaveLength(1);
  }, 20000);

  it("keeps a rejected generation draft and exposes exactly one server error through the log", async () => {
    await open();
    await trayItem("generate").trigger("click");
    const drawer = wrapper.getComponent(GalleryGenerateDrawer);
    await drawer.get("textarea").setValue("𠮷".repeat(513));
    await button(drawer, "開始生成").trigger("click");
    expect(sender.sent.actions[0].payload.custom_prompt).toBe("𠮷".repeat(513));
    const rejection = fx.actionResult({ outcome: "rejected", code: "malformed_payload", message: "測試伺服器的拒絕訊息。", presentation_revision: 1 });
    store.receive(1, "ui_action_result", [rejection]);
    store.receive(1, "ui_action_result", [rejection]);
    await wrapper.vm.$nextTick();
    expect(drawer.get("textarea").element.value).toBe("𠮷".repeat(513));
    expect(store.narrative.filter((line) => line.text === rejection.message)).toHaveLength(1);
    await button(drawer, "查看伺服器訊息").trigger("click");
    expect(wrapper.text()).toContain(rejection.message);
  }, 20000);

  it("tears down an editor on transport loss and cannot dispatch from the stale surface", async () => {
    await open();
    await trayItem("generate").trigger("click");
    store.setConnected(false);
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    expect(store.dispatchAction("gallery.generate", { subject_key: GALLERY_SAMPLE.selected, fields: [], custom_prompt: "" })).toBeNull();
    expect(sender.sent.actions).toEqual([]);
  }, 20000);

  it("saves a stage draft once, closes only on its revision, and retains a rejected draft", async () => {
    await open();
    const card = GALLERY_SAMPLE.cards[0];
    // A pending row offers no editor and can never target a mutation.
    await trayItem(GALLERY_SAMPLE.cards.find((row) => row.status === "pending").image_id).trigger("click");
    expect(footer("stage").exists()).toBe(false);
    expect(wrapper.findComponent(GalleryStageTransformModal).exists()).toBe(false);
    expect(sender.sent.actions).toEqual([]);
    // A completed card opens the editor; save waits for the preview image.
    await trayItem(card.image_id).trigger("click");
    await footer("stage").trigger("click");
    const modal = wrapper.getComponent(GalleryStageTransformModal);
    const save = () => modal.findAll("button").find((item) => item.text() === "儲存調整");
    expect(save().element.disabled).toBe(true);
    await loadFigure(modal);
    await modal.get('input[type="range"]').setValue("0.6");
    expect(save().element.disabled).toBe(false);
    await save().trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].action_id).toBe("gallery.stage.update");
    expect(sender.sent.actions[0].payload).toEqual({
      subject_key: GALLERY_SAMPLE.selected,
      image_id: card.image_id,
      stage: { scale: 0.6, x: 0, y: 0 },
    });
    // An unrelated revision bump never closes the editor.
    await snapshot(GALLERY_SAMPLE, 2);
    expect(wrapper.findComponent(GalleryStageTransformModal).exists()).toBe(true);
    // The correlated success plus its committed revision closes it.
    store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: 2 })]);
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent(GalleryStageTransformModal).exists()).toBe(false);
    // A rejection retains the draft and offers the log link.
    await footer("stage").trigger("click");
    const retry = wrapper.getComponent(GalleryStageTransformModal);
    await loadFigure(retry);
    await retry.get('input[type="range"]').setValue("0.6");
    await retry.findAll("button").find((item) => item.text() === "儲存調整").trigger("click");
    const rejection = fx.actionResult({ request_id: "session:2", outcome: "rejected", code: "gallery_rejected", message: "暫時無法儲存比例調整。", presentation_revision: 2 });
    store.receive(1, "ui_action_result", [rejection]);
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent(GalleryStageTransformModal).exists()).toBe(true);
    expect(wrapper.getComponent(GalleryStageTransformModal).get('input[type="number"]').element.value).toBe("0.6");
    await wrapper.getComponent(GalleryStageTransformModal).findAll("button").find((item) => item.text() === "查看伺服器訊息").trigger("click");
    expect(wrapper.text()).toContain("暫時無法儲存比例調整。");
  }, 20000);
});
