// The gallery's editors and the window's editor lifecycle (change
// webclient-gallery-ui; re-pointed to GalleryWindow by gallery-window-mount).
// The pure date helpers and the four editors are mounted on their own; the
// correlated editor closure, the official-entry geometry actions and the
// empty-page guidance are asserted through the mounted GalleryWindow with a
// fake `dispatch` and committed panels simulated through `setProps`.
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import GalleryWindow from "../../components/GalleryWindow.vue";
import GalleryGenerateDrawer from "../../components/GalleryGenerateDrawer.vue";
import GalleryBindingDrawer from "../../components/GalleryBindingDrawer.vue";
import GalleryFaceRectModal from "../../components/GalleryFaceRectModal.vue";
import GalleryStageTransformModal from "../../components/GalleryStageTransformModal.vue";
import {
  defaultFaceRect,
  editFaceRectField,
  faceCropStyle,
  moveFaceRect,
  resizeFaceRect,
} from "../../components/face-rect-edit.js";
import { GALLERY_CATEGORY_LABELS, GALLERY_DATE_UNAVAILABLE, galleryCardName, galleryDate } from "../../components/gallery-copy.js";
import Protocol from "../../../static/webclient/js/elosern/protocol.js";
import {
  GALLERY_V4_MINE as GALLERY_SAMPLE,
  GALLERY_V4_MINE_BLANK as GALLERY_EMPTY,
  GALLERY_V4_MONSTER as GALLERY_MONSTER,
  GALLERY_V4_PARTY,
} from "../../stories/gallery-fixtures-v4.js";

const PENDING_INDEX = GALLERY_SAMPLE.cards.findIndex((row) => row.status === "pending");
const TWIN = GALLERY_SAMPLE.groups[0].subjects[1].subject_key;

const wrappers = [];
function mountSurface(component, props) {
  const wrapper = mount(component, { props, attachTo: document.body });
  wrappers.push(wrapper);
  return wrapper;
}
function mountWindow(props) {
  return mountSurface(GalleryWindow, { dispatch: vi.fn(() => "request:1"), ...props });
}
function button(wrapper, text) {
  return wrapper.findAll("button").find((item) => item.text() === text);
}
const trayItem = (id) => document.querySelector(`[data-testid="gallery-tray-item"][data-item-id="${id}"]`);
const footerButton = (key) => document.querySelector(`[data-testid="gallery-page__${key}"]`);
const footerKeys = () => [...document.querySelectorAll('[data-testid="gallery-page__footer"] button')]
  .map((el) => el.dataset.testid.replace("gallery-page__", ""));
const pageSelection = () => document.querySelector('[data-testid="gallery-page"]')?.dataset.selection ?? null;
async function click(el) {
  el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  await flushPromises();
}
afterEach(() => {
  wrappers.reverse().forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  document.body.replaceChildren();
});

describe("the window's editor lifecycle", () => {
  it("preserves raw drafts on rejection and closes only on its own committed successful revision", async () => {
    const dispatch = vi.fn().mockReturnValueOnce(null).mockReturnValueOnce("request:1").mockReturnValueOnce("request:2");
    const wrapper = mountWindow({ model: GALLERY_SAMPLE, dispatch, revision: 1 });
    await click(trayItem("generate"));
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
    expect(dispatch).toHaveBeenCalledTimes(3);
  });

  it("closes stale editors on subject replacement, missing card and unavailable panel", async () => {
    const wrapper = mountWindow({ model: GALLERY_SAMPLE });
    await click(trayItem(GALLERY_SAMPLE.cards[0].image_id));
    await click(footerButton("face"));
    expect(wrapper.findComponent(GalleryFaceRectModal).exists()).toBe(true);
    await wrapper.setProps({ model: { ...GALLERY_SAMPLE, cards: GALLERY_SAMPLE.cards.slice(1) } });
    expect(wrapper.findComponent(GalleryFaceRectModal).exists()).toBe(false);
    await click(trayItem("generate"));
    await wrapper.setProps({ model: { ...GALLERY_EMPTY, selected: TWIN } });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    await click(trayItem("generate"));
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(true);
    await wrapper.setProps({ model: { schema_version: 4, available: false, reason: { message: "資料暫時無法使用。" } } });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(false);
    expect(wrapper.text()).toContain("資料暫時無法使用。");
  });

  it("keeps an empty-gallery generation draft across unrelated empty and pending publications", async () => {
    const wrapper = mountWindow({ model: GALLERY_EMPTY, dispatch: () => "empty:1" });
    expect(pageSelection()).toBe("empty");
    await click(footerButton("generate"));
    const drawer = wrapper.getComponent(GalleryGenerateDrawer);
    await drawer.get("textarea").setValue("第一張肖像");
    await wrapper.setProps({ model: structuredClone(GALLERY_EMPTY) });
    expect(drawer.get("textarea").element.value).toBe("第一張肖像");
    await button(drawer, "開始生成").trigger("click");
    await wrapper.setProps({ model: { ...GALLERY_EMPTY, cards: [GALLERY_SAMPLE.cards[PENDING_INDEX]] }, revision: 2 });
    expect(wrapper.findComponent(GalleryGenerateDrawer).exists()).toBe(true);
    await wrapper.setProps({ result: { requestId: "empty:1", outcome: "rejected" } });
    expect(drawer.get("textarea").element.value).toBe("第一張肖像");
  });

  it("ignores a canceled request's late result after a new editor opens", async () => {
    const wrapper = mountWindow({ model: GALLERY_SAMPLE, dispatch: () => "canceled:1" });
    await click(trayItem("generate"));
    await button(wrapper.getComponent(GalleryGenerateDrawer), "開始生成").trigger("click");
    await button(wrapper.getComponent(GalleryGenerateDrawer), "取消").trigger("click");
    await click(trayItem("generate"));
    const newDrawer = wrapper.getComponent(GalleryGenerateDrawer);
    await newDrawer.get("textarea").setValue("新的草稿");
    await wrapper.setProps({ result: { requestId: "canceled:1", outcome: "rejected" } });
    expect(newDrawer.get("textarea").element.value).toBe("新的草稿");
    expect(newDrawer.find('[role="status"]').exists()).toBe(false);
  });

  it("restores focus to the rail when the edited card and its opener disappear", async () => {
    const wrapper = mountWindow({ model: GALLERY_SAMPLE });
    await click(trayItem(GALLERY_SAMPLE.cards[0].image_id));
    footerButton("face").focus();
    await click(footerButton("face"));
    expect(wrapper.findComponent(GalleryFaceRectModal).exists()).toBe(true);
    await wrapper.setProps({ model: GALLERY_EMPTY });
    await flushPromises();
    await nextTick();
    expect(wrapper.findComponent(GalleryFaceRectModal).exists()).toBe(false);
    expect(document.activeElement).toBe(document.querySelector('[data-testid="icon-tabs__tab--mine"]'));
  });

  it("refreshes the page's relative date once a minute while open and stops the clock on close", async () => {
    const NOW = Date.UTC(2026, 8, 30, 12, 0, 0);
    vi.useFakeTimers({ now: NOW });
    try {
      const created = NOW / 1000 - 30;
      const model = { ...GALLERY_SAMPLE, cards: [{ ...GALLERY_SAMPLE.cards[0], created_at: created }], binding_warnings: [] };
      const timersBefore = vi.getTimerCount();
      const wrapper = mountWindow({ model });
      const cell = () => wrapper.get('[data-testid="gallery-page__cell"][data-cell="time"]');
      expect(cell().get(".gpage__line").text()).toBe("剛剛");
      expect(cell().get("time").attributes("datetime")).toBe(new Date(created * 1000).toISOString());
      vi.advanceTimersByTime(60_000);
      await nextTick();
      expect(cell().get(".gpage__line").text()).toBe(new Intl.RelativeTimeFormat("zh-TW", { numeric: "auto" }).format(-1, "minute"));
      const clearSpy = vi.spyOn(globalThis, "clearInterval");
      wrapper.unmount();
      wrappers.splice(wrappers.indexOf(wrapper), 1);
      expect(clearSpy).toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(timersBefore);
      clearSpy.mockRestore();
    } finally {
      vi.useRealTimers();
    }
  });
});

describe("gallery categories", () => {
  it("labels every category key of the mirrored wire contract", () => {
    expect(Object.keys(GALLERY_CATEGORY_LABELS)).toEqual([...Protocol.GALLERY_CATEGORY_KEYS]);
  });
});

describe("gallery card dates", () => {
  const NOW = Date.UTC(2026, 8, 30, 12, 0, 0);
  const TZ = { timeZone: "Asia/Taipei" };
  const exact = (seconds) =>
    new Intl.DateTimeFormat("zh-TW", { dateStyle: "long", timeStyle: "short", timeZone: "Asia/Taipei" }).format(new Date(seconds * 1000));

  it("reads a structured created_at as local relative time with the exact local instant", () => {
    const at = NOW / 1000 - 3 * 3600;
    expect(galleryDate(at, NOW, TZ)).toEqual({
      relative: new Intl.RelativeTimeFormat("zh-TW", { numeric: "auto" }).format(-3, "hour"),
      exact: exact(at),
      iso: new Date(at * 1000).toISOString(),
    });
    // Seconds of clock skew either way read 剛剛, never "in one minute".
    expect(galleryDate(NOW / 1000 + 5, NOW, TZ).relative).toBe("剛剛");
    expect(galleryDate(NOW / 1000 - 30, NOW, TZ).relative).toBe("剛剛");
  });

  it("gives a future instant a future-relative form and an impossible one the neutral unavailable label", () => {
    expect(galleryDate(NOW / 1000 + 2 * 60, NOW, TZ).relative).toBe(
      new Intl.RelativeTimeFormat("zh-TW", { numeric: "auto" }).format(2, "minute"),
    );
    // Finite but outside the ECMAScript calendar (> 8.64e15 ms), non-finite
    // and non-numeric values: no date is invented.
    for (const value of [8.64e12 + 1, -8.64e12 - 1, Number.POSITIVE_INFINITY, Number.NaN, "1700000000", null]) {
      expect(galleryDate(value, NOW, TZ)).toEqual({ relative: GALLERY_DATE_UNAVAILABLE, exact: null, iso: null });
    }
  });

  it("tells same-label cards apart by their own created_at, never the label text", () => {
    const [first, second] = GALLERY_SAMPLE.cards;
    expect(first.label).toBe(second.label);
    expect(galleryCardName(first, TZ)).toBe(`${first.label}，${exact(first.created_at)}`);
    expect(galleryCardName(second, TZ)).not.toBe(galleryCardName(first, TZ));
    expect(galleryCardName({ label: "肖像", created_at: Number.NaN })).toBe("肖像");
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
    const live = mountSurface(GalleryGenerateDrawer, { model: GALLERY_SAMPLE });
    expect(button(live, "從角色資料檢視")).toBeDefined();
    const wrapper = mountSurface(GalleryGenerateDrawer, { model: GALLERY_MONSTER });
    expect(wrapper.find("input").exists()).toBe(false);
    expect(wrapper.find("textarea").exists()).toBe(false);
    await button(wrapper, "開始生成").trigger("click");
    expect(wrapper.emitted("submit")).toEqual([[{ fields: [], custom_prompt: "" }]]);
    await wrapper.setProps({ model: GALLERY_V4_PARTY });
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
    const dims = { width: 768, height: 1024 };
    // Default on 768x1024:
    expect(defaultFaceRect(dims)).toEqual({ x: 0.25, y: 0.06, w: 0.5, h: 0.375 });
    // Move
    const rect = { x: 0.2, y: 0.3, w: 0.4, h: 0.3 };
    expect(moveFaceRect(rect, 2, -2)).toEqual({ x: 0.6, y: 0, w: 0.4, h: 0.3 });
    // Resize with dims: width drives, h = w * width / height
    const resized = resizeFaceRect(rect, 0.1, 0.1, dims);
    expect(resized.w).toBeCloseTo(0.5);
    expect(resized.h).toBeCloseTo(0.375);
    // Edit fields
    const editW = editFaceRectField(rect, "w", 0.4, dims);
    expect(editW.h).toBeCloseTo(0.3);
    const editH = editFaceRectField(rect, "h", 0.5, dims);
    expect(editH.w).toBeCloseTo(0.6667, 3);
    // Crop style
    expect(faceCropStyle({ x: 0.25, y: 0.1, w: 0.5, h: 0.375 })).toEqual({ width: "200%", height: "266.6666666666667%", left: "-50%", top: "-26.666666666666668%" });
  });

  it("uses the displayed non-square image bounds, and submits the keyboard-adjusted rectangle without pixels", async () => {
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: GALLERY_SAMPLE, card: GALLERY_SAMPLE.cards[0] });
    const image = wrapper.get(".gallery-face__original > img");
    image.element.getBoundingClientRect = () => ({ left: 100, top: 50, width: 200, height: 400 });
    Object.defineProperty(image.element, "naturalWidth", { value: 768, configurable: true });
    Object.defineProperty(image.element, "naturalHeight", { value: 1024, configurable: true });
    // Before load: save button is disabled
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeDefined();
    await image.trigger("load");
    // After load: save button is enabled
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeUndefined();
    const target = wrapper.get(".gallery-face__rect");
    target.element.setPointerCapture = vi.fn();
    await target.trigger("pointerdown", { button: 0, pointerId: 1, clientX: 150, clientY: 100 });
    await target.trigger("pointermove", { pointerId: 1, clientX: 170, clientY: 140 });
    await target.trigger("pointerup", { pointerId: 1 });
    expect(Number(wrapper.get('input[aria-label="水平位置"]').element.value)).toBeCloseTo(.35);
    expect(Number(wrapper.get('input[aria-label="垂直位置"]').element.value)).toBeCloseTo(.16);
    await wrapper.get('input[aria-label="寬度"]').setValue(.2);
    // Height auto-adjusts to square: 0.2 * 768 / 1024 = 0.15
    expect(Number(wrapper.get('input[aria-label="高度"]').element.value)).toBeCloseTo(.15);
    await button(wrapper, "儲存框選").trigger("click");
    const payload = wrapper.emitted("submit")[0][0];
    expect(Object.keys(payload)).toEqual(["face_rect"]);
    expect(payload.face_rect.w).toBe(.2);
    expect(payload.face_rect.h).toBeCloseTo(.15);
    expect(payload.face_rect.x).toBeCloseTo(.35);
    // Pixel square check: w * 768 == h * 1024
    expect(Math.abs(payload.face_rect.w * 768 - payload.face_rect.h * 1024)).toBeLessThanOrEqual(1.0);
  });

  it("cancels without an action and restores the opener when the parent unmounts the modal", async () => {
    const opener = document.createElement("button");
    document.body.appendChild(opener);
    opener.focus();
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: GALLERY_SAMPLE, card: GALLERY_SAMPLE.cards[0] });
    await wrapper.get('[role="dialog"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("submit")).toBeUndefined();
    expect(wrapper.emitted("close")).toHaveLength(1);
    wrapper.unmount();
    await nextTick();
    expect(document.activeElement).toBe(opener);
  });
});

const OFFICIAL_ROWS = GALLERY_SAMPLE.official_entries;
const OFFICIAL_CURRENT = OFFICIAL_ROWS.find((row) => row.is_current);

async function loadImage(img) {
  Object.defineProperty(img.element, "naturalWidth", { value: 768, configurable: true });
  Object.defineProperty(img.element, "naturalHeight", { value: 1024, configurable: true });
  await img.trigger("load");
}

describe("official read-only entries in the window", () => {
  it("previews a selected official entry with only its read-only affordances", async () => {
    mountWindow({ model: GALLERY_SAMPLE });
    await click(trayItem(OFFICIAL_CURRENT.identity));
    expect(pageSelection()).toBe("official");
    expect(footerKeys()).toEqual(["official-geometry-clear", "official-face", "official-stage", "official-clear-selection"]);
    const other = OFFICIAL_ROWS.find((row) => !row.is_current);
    await click(trayItem(other.identity));
    expect(footerKeys()).toEqual(["official-geometry-clear", "official-face", "official-stage", "official-select"]);
  });

  it("dispatches the selection with only the subject key and the committed identity", async () => {
    const wrapper = mountWindow({ model: GALLERY_SAMPLE });
    const target = OFFICIAL_ROWS.find((row) => !row.is_current);
    await click(trayItem(target.identity));
    await click(footerButton("official-select"));
    expect(wrapper.props("dispatch")).toHaveBeenCalledExactlyOnceWith("gallery.official.select", {
      subject_key: GALLERY_SAMPLE.selected,
      identity: target.identity,
    });
  });

  it("clears the personal geometry through its own action", async () => {
    const wrapper = mountWindow({ model: GALLERY_SAMPLE });
    await click(trayItem(OFFICIAL_CURRENT.identity));
    await click(footerButton("official-geometry-clear"));
    expect(wrapper.props("dispatch")).toHaveBeenCalledExactlyOnceWith("gallery.official.geometry.clear", {
      subject_key: GALLERY_SAMPLE.selected,
      identity: OFFICIAL_CURRENT.identity,
    });
  });

  it("sends only the edited face rectangle for an official identity", async () => {
    const wrapper = mountWindow({ model: GALLERY_SAMPLE });
    const dispatch = wrapper.props("dispatch");
    await click(trayItem(OFFICIAL_CURRENT.identity));
    await click(footerButton("official-face"));
    const modal = wrapper.getComponent(GalleryFaceRectModal);
    await loadImage(modal.get(".gallery-face__original > img"));
    // A real edit: the modal seeds from the committed rectangle, so only a
    // changed value may cross the wire (an untouched save would overwrite a
    // stored personal override with the catalog seed).
    await modal.findAll('input[type="number"]')[2].setValue("0.4");
    await button(modal, "儲存框選").trigger("click");
    expect(dispatch).toHaveBeenCalledTimes(1);
    const [actionId, sent] = dispatch.mock.calls[0];
    expect(actionId).toBe("gallery.official.geometry.set");
    expect(Object.keys(sent).sort()).toEqual(["face_rect", "identity", "subject_key"]);
    expect(sent.subject_key).toBe(GALLERY_SAMPLE.selected);
    expect(sent.identity).toBe(OFFICIAL_CURRENT.identity);
    expect(sent.face_rect.w).toBeCloseTo(0.4, 6);
    // The editor re-squares the edited rectangle on the real image size.
    expect(Math.abs(sent.face_rect.w * 768 - sent.face_rect.h * 1024)).toBeLessThanOrEqual(1);
    // The untouched component is never smuggled along.
    expect(sent).not.toHaveProperty("stage");
  });

  it("sends only the edited stage triple for an official identity", async () => {
    const wrapper = mountWindow({ model: GALLERY_SAMPLE });
    const dispatch = wrapper.props("dispatch");
    await click(trayItem(OFFICIAL_CURRENT.identity));
    await click(footerButton("official-stage"));
    const modal = wrapper.getComponent(GalleryStageTransformModal);
    await loadImage(modal.get(".stage-transform__figure"));
    await modal.get('input[type="range"]').setValue("0.6");
    await button(modal, "儲存調整").trigger("click");
    expect(dispatch).toHaveBeenCalledExactlyOnceWith("gallery.official.geometry.set", {
      subject_key: GALLERY_SAMPLE.selected,
      identity: OFFICIAL_CURRENT.identity,
      stage: { scale: 0.6, x: 0, y: 0 },
    });
    expect(dispatch.mock.calls[0][1]).not.toHaveProperty("face_rect");
  });

  it("never dispatches an untouched official geometry save", async () => {
    // The committed row carries no personal override, so an untouched save
    // would silently overwrite one with the seed. It closes instead.
    const wrapper = mountWindow({ model: GALLERY_SAMPLE });
    const dispatch = wrapper.props("dispatch");
    await click(trayItem(OFFICIAL_CURRENT.identity));
    await click(footerButton("official-stage"));
    const modal = wrapper.getComponent(GalleryStageTransformModal);
    await loadImage(modal.get(".stage-transform__figure"));
    await button(modal, "儲存調整").trigger("click");
    await flushPromises();
    expect(dispatch).not.toHaveBeenCalled();
    expect(wrapper.findComponent(GalleryStageTransformModal).exists()).toBe(false);
    // The face editor is seeded from the committed rectangle: saving it as-is
    // dispatches nothing either.
    await click(footerButton("official-face"));
    const face = wrapper.getComponent(GalleryFaceRectModal);
    await loadImage(face.get(".gallery-face__original > img"));
    await button(face, "儲存框選").trigger("click");
    await flushPromises();
    expect(dispatch).not.toHaveBeenCalled();
    expect(wrapper.findComponent(GalleryFaceRectModal).exists()).toBe(false);
  });
});

// The no-image page. Official entries are committed read-only artwork of the
// selected subject: the page may only claim missing artwork when there is no
// official artwork either, decided from the committed list alone.
const OFFICIAL_ONLY = { ...GALLERY_EMPTY, official_entries: GALLERY_SAMPLE.official_entries };
const officialTrayItems = () => document.querySelectorAll('[data-testid="gallery-tray-official"] [data-testid="gallery-tray-item"]');

describe("official-only artwork and the no-image page", () => {
  it("shows an official entry, not the no-image page, when official rows replace every card", () => {
    mountWindow({ model: OFFICIAL_ONLY });
    expect(pageSelection()).toBe("official");
    expect(officialTrayItems()).toHaveLength(OFFICIAL_ROWS.length);
    expect(footerButton("generate")).toBeNull();
  });

  it("shows the no-image page with 生成新圖 for a subject with no cards and no official rows", () => {
    mountWindow({ model: GALLERY_EMPTY });
    expect(pageSelection()).toBe("empty");
    expect(officialTrayItems()).toHaveLength(0);
    expect(footerButton("generate").textContent.trim()).toBe("生成新圖");
  });

  it("keeps the official entries in the tray while one card and official rows exist", () => {
    mountWindow({ model: { ...OFFICIAL_ONLY, cards: [GALLERY_SAMPLE.cards[3]] } });
    expect(pageSelection()).toBe("card");
    expect(officialTrayItems()).toHaveLength(OFFICIAL_ROWS.length);
  });

  it("follows a committed official-entry replacement in both directions without a dispatch", async () => {
    const dispatch = vi.fn();
    const wrapper = mountWindow({ model: OFFICIAL_ONLY, dispatch });
    expect(pageSelection()).toBe("official");
    await wrapper.setProps({ model: GALLERY_EMPTY });
    await flushPromises();
    expect(pageSelection()).toBe("empty");
    expect(officialTrayItems()).toHaveLength(0);
    await wrapper.setProps({ model: OFFICIAL_ONLY });
    await flushPromises();
    expect(pageSelection()).toBe("official");
    expect(officialTrayItems()).toHaveLength(OFFICIAL_ROWS.length);
    expect(dispatch).not.toHaveBeenCalled();
  });
});
