import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import GalleryPanel from "../../components/GalleryPanel.vue";
import GalleryDetailRail from "../../components/GalleryDetailRail.vue";
import GalleryGenerateDrawer from "../../components/GalleryGenerateDrawer.vue";
import GalleryBindingDrawer from "../../components/GalleryBindingDrawer.vue";
import GalleryFaceRectModal from "../../components/GalleryFaceRectModal.vue";
import { faceCropStyle, moveFaceRect, resizeFaceRect } from "../../components/face-rect-edit.js";
import { GALLERY_EMPTY, GALLERY_MONSTER, GALLERY_SAMPLE } from "../../stories/gallery-fixtures.js";

const wrappers = [];
function mountSurface(component, props) {
  const wrapper = mount(component, { props, attachTo: document.body });
  wrappers.push(wrapper);
  return wrapper;
}
function button(wrapper, text) {
  return wrapper.findAll("button").find((item) => item.text() === text);
}
afterEach(() => {
  wrappers.reverse().forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  document.body.replaceChildren();
});

describe("gallery panel facts and request settlement", () => {
  it("filters committed rows without replacing counts or order, and keeps failure text intact", async () => {
    const wrapper = mountSurface(GalleryPanel, { model: { ...GALLERY_SAMPLE, filters: { ...GALLERY_SAMPLE.filters, all: 41 } } });
    expect(button(wrapper, "全部（41）")).toBeDefined();
    await button(wrapper, "已綁定（3）").trigger("click");
    expect(wrapper.findAll(".gallery-card").map((row) => row.attributes("data-image-id"))).toEqual(GALLERY_SAMPLE.cards.slice(0, 3).map((row) => row.image_id));
    await button(wrapper, "失敗（1）").trigger("click");
    expect(wrapper.get(".gallery-card").text()).toContain(GALLERY_SAMPLE.cards[7].label);
    expect(wrapper.get(".gallery-card").find("img").exists()).toBe(false);
    await wrapper.setProps({ model: GALLERY_EMPTY });
    expect(wrapper.find(".gallery-card").exists()).toBe(false);
  });

  it("waits for subject publication rather than optimistically switching cards", async () => {
    const dispatch = vi.fn(() => "request:1");
    const wrapper = mountSurface(GalleryPanel, { model: GALLERY_SAMPLE, dispatch });
    await button(wrapper, "旅伴").trigger("click");
    expect(dispatch).toHaveBeenCalledExactlyOnceWith("gallery.subject.select", { subject_key: "portrait:character:7002" });
    expect(wrapper.findAll(".gallery-card")).toHaveLength(8);
    expect(button(wrapper, "夜行者").attributes("aria-pressed")).toBe("true");
  });

  it("preserves raw drafts on rejection and closes only on its own committed successful revision", async () => {
    const dispatch = vi.fn().mockReturnValueOnce(null).mockReturnValueOnce("request:1").mockReturnValueOnce("request:2");
    const wrapper = mountSurface(GalleryPanel, { model: GALLERY_SAMPLE, dispatch, revision: 1 });
    await button(wrapper, "生成新圖").trigger("click");
    const drawer = wrapper.getComponent(GalleryGenerateDrawer);
    await drawer.get("textarea").setValue("raw input");
    await button(drawer, "開始生成").trigger("click");
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(true);
    await button(drawer, "開始生成").trigger("click");
    await wrapper.setProps({ model: structuredClone(GALLERY_SAMPLE), revision: 2, result: { requestId: "foreign", outcome: "success", presentationRevision: 2 } });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(true);
    await wrapper.setProps({ result: { requestId: "request:1", outcome: "rejected", message: "伺服器拒絕" } });
    expect(drawer.get("textarea").element.value).toBe("raw input");
    expect(button(drawer, "查看伺服器訊息")).toBeDefined();
    await button(drawer, "開始生成").trigger("click");
    await wrapper.setProps({ result: { requestId: "request:2", outcome: "success", presentationRevision: 3 } });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(true);
    await wrapper.setProps({ revision: 3 });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
  });

  it("closes stale editors on subject replacement, missing card and unavailable panel", async () => {
    const wrapper = mountSurface(GalleryPanel, { model: GALLERY_SAMPLE });
    await button(wrapper, "臉部框選").trigger("click");
    await wrapper.setProps({ model: { ...GALLERY_SAMPLE, cards: GALLERY_SAMPLE.cards.slice(1) } });
    expect(wrapper.findComponent(GalleryFaceRectModal).exists()).toBe(false);
    await button(wrapper, "生成新圖").trigger("click");
    await wrapper.setProps({ model: { ...GALLERY_EMPTY, selected: "portrait:character:7002" } });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    await button(wrapper, "生成新圖").trigger("click");
    await wrapper.setProps({ model: { available: false, reason: { message: "資料暫時無法使用。" } } });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    expect(wrapper.text()).toContain("資料暫時無法使用。");
  });

  it("keeps an empty-gallery generation draft across unrelated empty and pending publications", async () => {
    const wrapper = mountSurface(GalleryPanel, { model: GALLERY_EMPTY, dispatch: () => "empty:1" });
    await button(wrapper, "生成新圖").trigger("click");
    const drawer = wrapper.getComponent(GalleryGenerateDrawer);
    await drawer.get("textarea").setValue("第一張肖像");
    await wrapper.setProps({ model: structuredClone(GALLERY_EMPTY) });
    expect(drawer.get("textarea").element.value).toBe("第一張肖像");
    await button(drawer, "開始生成").trigger("click");
    await wrapper.setProps({ model: { ...GALLERY_EMPTY, cards: [GALLERY_SAMPLE.cards[6]] }, revision: 2 });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(true);
    await wrapper.setProps({ result: { requestId: "empty:1", outcome: "rejected" } });
    expect(drawer.get("textarea").element.value).toBe("第一張肖像");
  });

  it("ignores a canceled request's late result after a new editor opens", async () => {
    const wrapper = mountSurface(GalleryPanel, { model: GALLERY_SAMPLE, dispatch: () => "canceled:1" });
    await button(wrapper, "生成新圖").trigger("click");
    await button(wrapper.getComponent(GalleryGenerateDrawer), "開始生成").trigger("click");
    await button(wrapper.getComponent(GalleryGenerateDrawer), "取消").trigger("click");
    await button(wrapper, "生成新圖").trigger("click");
    const newDrawer = wrapper.getComponent(GalleryGenerateDrawer);
    await newDrawer.get("textarea").setValue("新的草稿");
    await wrapper.setProps({ result: { requestId: "canceled:1", outcome: "rejected" } });
    expect(newDrawer.get("textarea").element.value).toBe("新的草稿");
    expect(newDrawer.find('[role="status"]').exists()).toBe(false);
  });

  it("restores a remaining gallery control when the edited card and opener disappear", async () => {
    const wrapper = mountSurface(GalleryPanel, { model: GALLERY_SAMPLE });
    button(wrapper, "臉部框選").element.focus();
    await button(wrapper, "臉部框選").trigger("click");
    await wrapper.setProps({ model: GALLERY_EMPTY });
    await nextTick();
    expect(wrapper.findComponent(GalleryFaceRectModal).exists()).toBe(false);
    expect(document.activeElement).toBe(button(wrapper, "生成新圖").element);
  });
});

describe("gallery detail rail", () => {
  it("cancels deletion, confirms once, and never invents missing binding conditions", async () => {
    const wrapper = mountSurface(GalleryDetailRail, { card: GALLERY_SAMPLE.cards[2], capabilities: GALLERY_SAMPLE.capabilities, warnings: GALLERY_SAMPLE.binding_warnings });
    expect(wrapper.text()).not.toContain("暗影劍刃");
    await button(wrapper, "刪除").trigger("click");
    await button(wrapper, "取消").trigger("click");
    expect(wrapper.emitted("delete")).toBeUndefined();
    await button(wrapper, "刪除").trigger("click");
    await button(wrapper, "確認刪除").trigger("click");
    expect(wrapper.emitted("delete")).toHaveLength(1);
    await wrapper.setProps({ capabilities: GALLERY_MONSTER.capabilities });
    expect(button(wrapper, "編輯設定")).toBeUndefined();
  });
});

describe("gallery generation drawer", () => {
  it("submits raw code-point-counted oversized input with only selected field ids", async () => {
    const wrapper = mountSurface(GalleryGenerateDrawer, { model: GALLERY_SAMPLE });
    const raw = "𠮷".repeat(513);
    await wrapper.get('input[value="appearance"]').setValue(true);
    await wrapper.get('input[value="armor"]').setValue(true);
    await wrapper.get("textarea").setValue(raw);
    expect(wrapper.text()).toContain("513 / 512");
    await button(wrapper, "開始生成").trigger("click");
    expect(wrapper.emitted("submit")).toEqual([[{ fields: ["appearance", "armor"], custom_prompt: raw }]]);
  });

  it("respects monster capabilities and does not link a companion to the puppet's character data", async () => {
    const wrapper = mountSurface(GalleryGenerateDrawer, { model: GALLERY_MONSTER });
    expect(wrapper.find("input").exists()).toBe(false);
    expect(wrapper.find("textarea").exists()).toBe(false);
    await button(wrapper, "開始生成").trigger("click");
    expect(wrapper.emitted("submit")).toEqual([[{ fields: [], custom_prompt: "" }]]);
    await wrapper.setProps({ model: { ...GALLERY_SAMPLE, selected: "portrait:character:7002" } });
    expect(button(wrapper, "從角色資料檢視")).toBeUndefined();
  });

  it("traps keyboard focus and restores the opener on Escape", async () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const wrapper = mountSurface(GalleryGenerateDrawer, { model: GALLERY_SAMPLE });
    const cancel = button(wrapper, "開始生成");
    cancel.element.focus();
    await cancel.trigger("keydown", { key: "Tab" });
    expect(document.activeElement).toBe(wrapper.get('[data-testid="hud-drawer-close"]').element);
    await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(document.activeElement).toBe(opener);
  });
});

describe("gallery binding drawer", () => {
  it("requires a slot, preserves empty-slot intent, and renders warning lines verbatim", async () => {
    const wrapper = mountSurface(GalleryBindingDrawer, { model: GALLERY_SAMPLE, card: GALLERY_SAMPLE.cards[0] });
    expect(button(wrapper, "儲存綁定").element.disabled).toBe(true);
    await wrapper.get('input[value="weapon_off"]').setValue(true);
    expect(wrapper.find("select").exists()).toBe(false);
    await button(wrapper, "儲存綁定").trigger("click");
    expect(wrapper.emitted("submit")).toEqual([[{ slots: ["weapon_off"] }]]);
    expect(wrapper.text()).toContain("飾品：銀月髮飾、暮光耳環（任一）");
    await button(wrapper, "查看").trigger("click");
    expect(wrapper.emitted("select-card")[0]).toEqual([GALLERY_SAMPLE.cards[0].image_id]);
  });
});

describe("face geometry", () => {
  it("moves without resizing and clamps positive area at image boundaries", () => {
    const rect = { x: .2, y: .3, w: .4, h: .2 };
    expect(moveFaceRect(rect, 2, -2)).toEqual({ x: .6, y: 0, w: .4, h: .2 });
    expect(resizeFaceRect(rect, 2, 2)).toEqual({ x: .2, y: .3, w: .8, h: .7 });
    const small = resizeFaceRect(rect, -2, -2);
    expect(small.w).toBeGreaterThan(0);
    expect(small.h).toBeGreaterThan(0);
    expect(faceCropStyle({ x: .25, y: .1, w: .5, h: .25 })).toEqual({ width: "200%", height: "400%", left: "-50%", top: "-40%" });
  });

  it("uses the displayed non-square image bounds, and submits the keyboard-adjusted rectangle without pixels", async () => {
    const wrapper = mountSurface(GalleryFaceRectModal, { card: GALLERY_SAMPLE.cards[0] });
    const image = wrapper.get(".gallery-face__original > img");
    image.element.getBoundingClientRect = () => ({ left: 100, top: 50, width: 200, height: 400 });
    await image.trigger("load");
    const target = wrapper.get(".gallery-face__rect");
    target.element.setPointerCapture = vi.fn();
    await target.trigger("pointerdown", { button: 0, pointerId: 1, clientX: 150, clientY: 100 });
    await target.trigger("pointermove", { pointerId: 1, clientX: 170, clientY: 140 });
    await target.trigger("pointerup", { pointerId: 1 });
    expect(Number(wrapper.get('input[aria-label="水平位置"]').element.value)).toBeCloseTo(.35);
    expect(Number(wrapper.get('input[aria-label="垂直位置"]').element.value)).toBeCloseTo(.16);
    await wrapper.get('input[aria-label="寬度"]').setValue(.2);
    await button(wrapper, "儲存框選").trigger("click");
    const payload = wrapper.emitted("submit")[0][0];
    expect(Object.keys(payload)).toEqual(["face_rect"]);
    expect(payload.face_rect.w).toBe(.2);
    expect(payload.face_rect.x).toBeCloseTo(.35);
  });

  it("cancels without an action and restores the opener when the parent unmounts the modal", async () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const wrapper = mountSurface(GalleryFaceRectModal, { card: GALLERY_SAMPLE.cards[0] });
    await wrapper.get('[role="dialog"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("submit")).toBeUndefined();
    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
    await nextTick();
    expect(document.activeElement).toBe(opener);
  });
});
