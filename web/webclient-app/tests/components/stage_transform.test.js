import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import Modal from "../../components/GalleryStageTransformModal.vue";
import ReferenceArtwork from "../../components/ReferenceArtwork.vue";
import { clampStage, editStageField, moveStage } from "../../components/stage-transform-edit.js";
const card = { url: "/art/defaults/man.webp", label: "肖像", stage: { scale: 0.6, x: 0, y: 0 } };
describe("stage transform", () => {
  it("clamps only finite numbers and retains invalid field drafts", () => {
    expect(clampStage(null)).toEqual({ scale: 1, x: 0, y: 0 });
    expect(clampStage({ scale: 3, x: -2, y: 2 })).toEqual({ scale: 2, x: -0.5, y: 0.5 });
    for (const value of [NaN, Infinity, true, null, ""]) expect(editStageField(card.stage, "scale", value)).toEqual(card.stage);
    expect(moveStage(card.stage, 30 / 300, -40 / 400)).toEqual({ scale: 0.6, x: 0.1, y: -0.1 });
    expect(moveStage(card.stage, 2, -2)).toEqual({ scale: 0.6, x: 0.5, y: -0.5 });
  });
  it("binds stage only, retaining the source and cover placement", async () => {
    const wrapper = mount(ReferenceArtwork, { props: { portrait: card, stage: true } });
    const image = wrapper.get("img").element;
    expect(image.style.getPropertyValue("--stage-scale")).toBe("0.6");
    await wrapper.setProps({ portrait: { ...card, stage: { scale: 2, x: 0.1, y: -0.2 } } });
    expect(wrapper.get("img").element).toBe(image);
    expect(image.style.getPropertyValue("--stage-x")).toBe("0.1");
    await wrapper.setProps({ portrait: { ...card, stage: null } });
    expect(image.style.getPropertyValue("--stage-scale")).toBe("1");
    wrapper.unmount();
  });
  it("keeps edits local, waits for load, resets and submits once", async () => {
    const wrapper = mount(Modal, { props: { card }, attachTo: document.body });
    const save = wrapper.findAll("button").find(button => button.text() === "儲存調整");
    expect(save.element.disabled).toBe(true);
    await wrapper.get("img").trigger("load");
    await wrapper.get('input[type="range"]').setValue("0.8");
    expect(wrapper.get('input[type="number"]').element.value).toBe("0.8");
    expect(wrapper.emitted("submit")).toBeUndefined();
    await wrapper.findAll("button").find(button => button.text() === "重設").trigger("click");
    await save.trigger("click");
    await save.trigger("click");
    expect(wrapper.emitted("submit")).toEqual([[{ stage: { scale: 1, x: 0, y: 0 } }]]);
    wrapper.unmount();
  });
  it("failed image keeps reference and refuses save", async () => {
    const wrapper = mount(Modal, { props: { card } });
    await wrapper.get("img").trigger("error");
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".stage-transform__adult").attributes("aria-hidden")).toBe("true");
    expect(wrapper.text()).toContain("圖片載入失敗");
    wrapper.unmount();
  });
  it("drag moves the figure in frame fractions while the adult stays static", async () => {
    const wrapper = mount(Modal, { props: { card }, attachTo: document.body });
    await wrapper.get("img").trigger("load");
    const frame = wrapper.get(".stage-transform__frame").element;
    frame.getBoundingClientRect = () => ({ width: 300, height: 400, top: 0, left: 0, right: 300, bottom: 400, x: 0, y: 0 });
    frame.setPointerCapture = () => {};
    frame.releasePointerCapture = () => {};
    await wrapper.get(".stage-transform__frame").trigger("pointerdown", { pointerId: 1, button: 0, clientX: 100, clientY: 100 });
    await wrapper.get(".stage-transform__frame").trigger("pointermove", { pointerId: 1, clientX: 130, clientY: 60 });
    const figure = wrapper.get(".stage-transform__figure").element.style;
    expect(figure.getPropertyValue("--stage-x")).toBe("0.1");
    expect(figure.getPropertyValue("--stage-y")).toBe("-0.1");
    expect(figure.getPropertyValue("--stage-scale")).toBe("0.6");
    expect(wrapper.findAll('input[type="number"]').map((input) => input.element.value)).toEqual(["0.6", "0.1", "-0.1"]);
    // Repeated movement clamps at the bounds and never crosses them.
    await wrapper.get(".stage-transform__frame").trigger("pointermove", { pointerId: 1, clientX: 400, clientY: -100 });
    expect(figure.getPropertyValue("--stage-x")).toBe("0.5");
    expect(figure.getPropertyValue("--stage-y")).toBe("-0.5");
    // The adult reference is a static layer: no inline transform variables.
    expect(wrapper.get(".stage-transform__adult").attributes("style") ?? "").toBe("");
    await wrapper.get(".stage-transform__frame").trigger("pointerup", { pointerId: 1 });
    expect(wrapper.emitted("submit")).toBeUndefined();
    wrapper.unmount();
  });
  it("traps focus, edits numbers by keyboard, and Escape closes with focus restored and no dispatch", async () => {
    const opener = document.createElement("button");
    document.body.append(opener);
    opener.focus();
    const wrapper = mount(Modal, { props: { card }, attachTo: document.body });
    await wrapper.get("img").trigger("load");
    const number = wrapper.findAll('input[type="number"]')[0];
    await number.setValue("0.7");
    expect(wrapper.get(".stage-transform__figure").element.style.getPropertyValue("--stage-scale")).toBe("0.7");
    await wrapper.get(".stage-transform").trigger("keydown", { key: "Tab" });
    expect(wrapper.emitted("close")).toBeUndefined();
    await wrapper.get(".stage-transform").trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(wrapper.emitted("submit")).toBeUndefined();
    wrapper.unmount();
    expect(document.activeElement).toBe(opener);
    opener.remove();
  });
  it("cover avatars never receive the stage transform", () => {
    const wrapper = mount(ReferenceArtwork, { props: { portrait: { ...card, stage: { scale: 0.6, x: 0.3, y: 0.2 } } } });
    const image = wrapper.get("img").element;
    expect(image.style.getPropertyValue("--stage-scale")).toBe("");
    expect(image.style.getPropertyValue("--stage-x")).toBe("");
    // Cover placement stays face-rect driven (no face_rect here -> default centering).
    expect(image.getAttribute("style")).toBe("object-position: 50% 50%;");
    wrapper.unmount();
  });
});
