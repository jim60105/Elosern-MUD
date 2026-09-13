import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../AppClient.vue";
import GalleryGenerateDrawer from "../components/GalleryGenerateDrawer.vue";
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
  it("offers a real opener only with committed availability and shows a degradation reason", async () => {
    await snapshot(null);
    expect(wrapper.find('[data-testid="gallery-opener"]').exists()).toBe(false);
    await snapshot(GALLERY_SAMPLE, 2);
    await wrapper.get('[data-testid="gallery-opener"]').trigger("click");
    expect(wrapper.find('[data-testid="gallery-panel"]').exists()).toBe(true);
    await snapshot({ schema_version: 1, available: false, reason: { code: "gallery_unavailable", message: "圖庫資料暫時無法使用。" } }, 3);
    expect(wrapper.find('[data-testid="gallery-opener"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="gallery-panel"]').text()).toContain("圖庫資料暫時無法使用。");
  });
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
  });
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
  });
  it("tears down an editor on transport loss and cannot dispatch from the stale surface", async () => {
    await open();
    await button(wrapper.get('[data-testid="gallery-panel"]'), "生成新圖").trigger("click");
    store.setConnected(false);
    await wrapper.vm.$nextTick();
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    expect(store.dispatchAction("gallery.generate", { subject_key: "portrait:character:7001", fields: [], custom_prompt: "" })).toBeNull();
    expect(sender.sent.actions).toEqual([]);
  });
});
