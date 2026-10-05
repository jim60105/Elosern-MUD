import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../AppClient.vue";
import GalleryGenerateDrawer from "../components/GalleryGenerateDrawer.vue";
import GalleryStageTransformModal from "../components/GalleryStageTransformModal.vue";
import { useElosernStore } from "../stores/elosern.js";
import { GALLERY_SAMPLE } from "../stories/gallery-fixtures.js";
import * as fx from "./store/protocol_fixtures.js";

describe("gallery application integration", () => {
  let store, sender, wrapper;
  const button = (surface, text) => surface.findAll("button").find((item) => item.text() === text);
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
  }
  // Every test in this file pays the mount cost of the whole AppClient on a
  // loaded CI runner (measured 5.3–12.8s per test against vitest's 5s
  // default, with the same tests completing in well under a second locally),
  // so each one carries this file's explicit budget.
  it("offers a real opener only with committed availability and shows a degradation reason", async () => {
    await snapshot(null);
    expect(wrapper.find('[data-testid="gallery-opener"]').exists()).toBe(false);
    await snapshot(GALLERY_SAMPLE, 2);
    const opener = wrapper.get('[data-testid="gallery-opener"]');
    expect(opener.element.closest('[data-testid="nav-tools"]')).not.toBeNull();
    expect(opener.element.closest('[data-testid="command-line"]')).toBeNull();
    opener.element.focus();
    await opener.trigger("click");
    expect(wrapper.find('[data-testid="gallery-panel"]').exists()).toBe(true);
    await wrapper.get('[data-testid="overlay-host-close"]').trigger("click");
    expect(wrapper.find('[data-testid="gallery-panel"]').exists()).toBe(false);
    expect(document.activeElement).toBe(opener.element);

    opener.element.focus();
    await opener.trigger("click");
    await snapshot({ schema_version: 1, available: false, reason: { code: "gallery_unavailable", message: "圖庫資料暫時無法使用。" } }, 3);
    expect(wrapper.find('[data-testid="gallery-opener"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="gallery-panel"]').text()).toContain("圖庫資料暫時無法使用。");
  }, 20000);
  it("confirms deletion through the shared entry and blocks concurrent mutation", async () => {
    await open();
    const rail = wrapper.get('[data-testid="gallery-detail"]');
    await button(rail, "刪除").trigger("click");
    await button(rail, "取消").trigger("click");
    expect(sender.sent.actions).toEqual([]);
    await button(rail, "刪除").trigger("click");
    await button(rail, "確認刪除").trigger("click");
    expect(sender.sent.actions[0].action_id).toBe("gallery.card.delete");
    expect(sender.sent.actions[0].payload).toEqual({ subject_key: "portrait:character:7001", image_id: GALLERY_SAMPLE.cards[0].image_id });
    await button(wrapper.get('[data-testid="gallery-panel"]'), "生成新圖").trigger("click");
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    expect(sender.sent.actions).toHaveLength(1);
  }, 20000);
  it("keeps a rejected generation draft and exposes exactly one server error through the log", async () => {
    await open();
    await button(wrapper.get('[data-testid="gallery-panel"]'), "生成新圖").trigger("click");
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
    await button(wrapper.get('[data-testid="gallery-panel"]'), "生成新圖").trigger("click");
    store.setConnected(false);
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    expect(store.dispatchAction("gallery.generate", { subject_key: "portrait:character:7001", fields: [], custom_prompt: "" })).toBeNull();
    expect(sender.sent.actions).toEqual([]);
  }, 20000);
  it("saves a stage draft once, closes only on its revision, and retains a rejected draft", async () => {
    await open();
    const panel = () => wrapper.get('[data-testid="gallery-panel"]');
    // A pending row can never open the editor or target a mutation.
    await panel().get(`[data-image-id="${GALLERY_SAMPLE.cards[6].image_id}"]`).trigger("click");
    expect(button(wrapper.get('[data-testid="gallery-detail"]'), "比例調整")).toBeUndefined();
    expect(wrapper.findComponent(GalleryStageTransformModal).exists()).toBe(false);
    expect(sender.sent.actions).toEqual([]);
    // A completed card opens the editor; save waits for the preview image.
    await panel().get(`[data-image-id="${GALLERY_SAMPLE.cards[0].image_id}"]`).trigger("click");
    await button(wrapper.get('[data-testid="gallery-detail"]'), "比例調整").trigger("click");
    const modal = wrapper.getComponent(GalleryStageTransformModal);
    const save = () => modal.findAll("button").find((item) => item.text() === "儲存調整");
    expect(save().element.disabled).toBe(true);
    await modal.get(".stage-transform__figure").trigger("load");
    await modal.get('input[type="range"]').setValue("0.6");
    expect(save().element.disabled).toBe(false);
    await save().trigger("click");
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0].action_id).toBe("gallery.stage.update");
    expect(sender.sent.actions[0].payload).toEqual({
      subject_key: "portrait:character:7001",
      image_id: GALLERY_SAMPLE.cards[0].image_id,
      stage: { scale: 0.6, x: 0, y: 0 },
    });
    // An unrelated revision bump never closes the editor.
    await snapshot(GALLERY_SAMPLE, 2);
    expect(wrapper.getComponent(GalleryStageTransformModal).exists()).toBe(true);
    // The correlated success plus its committed revision closes it.
    store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: 2 })]);
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent(GalleryStageTransformModal).exists()).toBe(false);
    // A rejection retains the draft and offers the log link.
    await panel().get(`[data-image-id="${GALLERY_SAMPLE.cards[0].image_id}"]`).trigger("click");
    await button(wrapper.get('[data-testid="gallery-detail"]'), "比例調整").trigger("click");
    const retry = wrapper.getComponent(GalleryStageTransformModal);
    await retry.get(".stage-transform__figure").trigger("load");
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
