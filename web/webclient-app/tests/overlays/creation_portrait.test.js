// creation-draft-portrait: the live portrait slot, the shared generation
// drawer in creation context and the overlay's request ownership over the
// REAL store (fake transport). Assertions establish behaviour — which state
// renders which kind of figure, which controls are enabled, what is sent and
// when — never copy, markup structure or shipped data. Server reasons are
// compared against the synthetic fixture they came from.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../../AppClient.vue";
import CreationPortraitSlot from "../../components/CreationPortraitSlot.vue";
import GalleryGenerateDrawer from "../../components/GalleryGenerateDrawer.vue";
import { useElosernStore } from "../../stores/elosern.js";
import { CREATION_PANEL_CUSTOM_DRAFT_SAMPLE, CREATION_PANEL_SAMPLE, CREATION_PORTRAIT_STATES } from "../../stories/fixtures.js";
import { galleryStoryModel } from "../../stories/gallery-fixtures-v4.js";
import { CREATION_DRAWER_MODEL, PORTRAIT_ACTION } from "../../composables/use-creation-portrait.js";
import * as fx from "../store/protocol_fixtures.js";

const tid = (id) => `[data-testid="${id}"]`;
const SILHOUETTE = CREATION_PANEL_SAMPLE.custom.silhouettes[0].artwork;
const STATUSES = ["empty", "pending", "ready", "failed", "unavailable"];

// -- The slot ----------------------------------------------------------------

describe("CreationPortraitSlot states", () => {
  function mountSlot(props) {
    return mount(CreationPortraitSlot, {
      props: { name: "測試者", silhouette: SILHOUETTE, canGenerate: true, ...props },
    });
  }

  it("shows the supplied silhouette in every state but ready, which shows the server artwork", () => {
    for (const status of STATUSES) {
      const wrapper = mountSlot({ portrait: CREATION_PORTRAIT_STATES[status] });
      const art = wrapper.find(tid("creation-portrait-artwork"));
      const figure = wrapper.find(tid("creation-portrait-silhouette"));
      if (status === "ready") {
        expect(art.exists(), status).toBe(true);
        expect(figure.exists(), status).toBe(false);
        const preview = wrapper.findAllComponents({ name: "ArtworkPreview" })[0];
        expect(preview.props("artwork")).toStrictEqual(CREATION_PORTRAIT_STATES.ready.artwork);
        // The ready portrait is meaningful content carrying the current name.
        expect(preview.props("alt")).toContain("測試者");
        expect(wrapper.get(".creation-portrait__frame").attributes("aria-hidden")).toBeUndefined();
      } else {
        expect(art.exists(), status).toBe(false);
        expect(figure.exists(), status).toBe(true);
        expect(wrapper.findAllComponents({ name: "ArtworkPreview" })[0].props("artwork")).toStrictEqual(SILHOUETTE);
        // The silhouette is decoration.
        expect(wrapper.get(".creation-portrait__frame").attributes("aria-hidden")).toBe("true");
      }
      wrapper.unmount();
    }
  });

  it("disables generation while pending or unavailable and permits it when empty, ready or failed", () => {
    for (const status of STATUSES) {
      const wrapper = mountSlot({ portrait: CREATION_PORTRAIT_STATES[status] });
      const generate = wrapper.get(tid("creation-portrait-generate"));
      const blocked = status === "pending" || status === "unavailable";
      expect(generate.attributes("disabled") !== undefined, status).toBe(blocked);
      expect(wrapper.find(tid("creation-portrait-refresh")).exists(), status).toBe(status === "unavailable");
      wrapper.unmount();
    }
  });

  it("the shared gate disables generation but never the status refresh", () => {
    const wrapper = mountSlot({ portrait: CREATION_PORTRAIT_STATES.unavailable, disabled: true });
    expect(wrapper.get(tid("creation-portrait-generate")).attributes("disabled")).toBeDefined();
    expect(wrapper.get(tid("creation-portrait-refresh")).attributes("disabled")).toBeUndefined();
    for (const status of ["empty", "ready", "failed"]) {
      const gated = mountSlot({ portrait: CREATION_PORTRAIT_STATES[status], disabled: true });
      expect(gated.get(tid("creation-portrait-generate")).attributes("disabled"), status).toBeDefined();
      gated.unmount();
    }
  });

  it("displays the server reason for failed and unavailable in one persistent live region", async () => {
    const wrapper = mountSlot({ portrait: CREATION_PORTRAIT_STATES.empty });
    const region = wrapper.get(tid("creation-portrait-status"));
    expect(region.attributes("role")).toBe("status");
    for (const status of STATUSES) {
      await wrapper.setProps({ portrait: CREATION_PORTRAIT_STATES[status] });
      const current = wrapper.get(tid("creation-portrait-status"));
      // The same mounted element announces every transition.
      expect(current.element).toBe(region.element);
      expect(current.attributes("data-state")).toBe(status);
      expect(current.text().trim()).not.toBe("");
      if (status === "failed" || status === "unavailable") {
        expect(current.text()).toContain(CREATION_PORTRAIT_STATES[status].reason);
      }
    }
  });

  it("only emits intents: generate and refresh-status", async () => {
    const wrapper = mountSlot({ portrait: CREATION_PORTRAIT_STATES.failed });
    await wrapper.get(tid("creation-portrait-generate")).trigger("click");
    expect(wrapper.emitted("generate")).toHaveLength(1);
    await wrapper.setProps({ portrait: CREATION_PORTRAIT_STATES.unavailable });
    await wrapper.get(tid("creation-portrait-refresh")).trigger("click");
    expect(wrapper.emitted("refresh-status")).toHaveLength(1);
    expect(Object.keys(wrapper.emitted()).filter((name) => !["click"].includes(name)).sort()).toStrictEqual(["generate", "refresh-status"]);
  });

  it("offers no control without canGenerate", () => {
    const wrapper = mountSlot({ portrait: CREATION_PORTRAIT_STATES.empty, canGenerate: false });
    expect(wrapper.findAll("button")).toHaveLength(0);
  });
});

// -- The drawer in creation context -------------------------------------------

describe("GalleryGenerateDrawer creation context", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  function mountDrawer(props) {
    return mount(GalleryGenerateDrawer, { props: { model: CREATION_DRAWER_MODEL, context: "creation", ...props }, attachTo: document.body });
  }

  it("offers only the free-text prompt: no field selection, equipment or character link", async () => {
    const wrapper = mountDrawer({});
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(0);
    expect(wrapper.find("textarea").exists()).toBe(true);
    // Even a model that carried equipment shows none in creation context.
    await wrapper.setProps({ model: { ...CREATION_DRAWER_MODEL, equipment_summary: galleryStoryModel().equipment_summary } });
    expect(wrapper.find(".gallery-equipment").exists()).toBe(false);
    expect(wrapper.find(".gallery-link").exists()).toBe(false);
    await wrapper.get("textarea").setValue("月光下");
    await wrapper.get(tid("gallery-generate__submit")).trigger("click");
    expect(wrapper.emitted("submit")).toStrictEqual([[{ fields: [], custom_prompt: "月光下" }]]);
  });

  it("server unavailability disables submit, keeps the prompt editable and offers refresh", async () => {
    const reason = CREATION_PORTRAIT_STATES.unavailable.reason;
    const wrapper = mountDrawer({ unavailableReason: reason });
    const textarea = wrapper.get("textarea");
    expect(textarea.attributes("disabled")).toBeUndefined();
    await textarea.setValue("保留的提示");
    expect(wrapper.get(tid("gallery-generate__submit")).attributes("disabled")).toBeDefined();
    await wrapper.get(tid("gallery-generate__submit")).trigger("click");
    expect(wrapper.emitted("submit")).toBeUndefined();
    expect(wrapper.get(tid("gallery-generate__unavailable")).text()).toContain(reason);
    const refresh = wrapper.get(tid("gallery-generate__refresh"));
    // Inside the drawer's own focus trap.
    expect(wrapper.get(tid("hud-drawer")).element.contains(refresh.element)).toBe(true);
    await refresh.trigger("click");
    expect(wrapper.emitted("refresh-status")).toHaveLength(1);
    expect(wrapper.emitted("submit")).toBeUndefined();
    // A refreshed healthy/unknown state re-enables explicit submission only.
    await wrapper.setProps({ unavailableReason: "" });
    expect(textarea.element.value).toBe("保留的提示");
    expect(wrapper.emitted("submit")).toBeUndefined();
    await wrapper.get(tid("gallery-generate__submit")).trigger("click");
    expect(wrapper.emitted("submit")).toStrictEqual([[{ fields: [], custom_prompt: "保留的提示" }]]);
  });

  it("without the context prop the gallery keeps its field selection, reason-free submit and payload", async () => {
    const model = galleryStoryModel();
    const wrapper = mount(GalleryGenerateDrawer, { props: { model, unavailableReason: "ignored" }, attachTo: document.body });
    const boxes = wrapper.findAll('input[type="checkbox"]');
    expect(boxes.length).toBeGreaterThan(0);
    expect(wrapper.find(tid("gallery-generate__unavailable")).exists()).toBe(false);
    expect(wrapper.get(tid("hud-drawer")).attributes("data-drawer-key")).toBe("gallery-generate");
    await boxes[0].setValue(true);
    await wrapper.get("textarea").setValue("x");
    await wrapper.get(tid("gallery-generate__submit")).trigger("click");
    expect(wrapper.emitted("submit")).toStrictEqual([[{ fields: [boxes[0].element.value], custom_prompt: "x" }]]);
  });
});

// -- Overlay request ownership over the real store ------------------------------

const SUBRACED = CREATION_PANEL_SAMPLE.custom.races.find((race) => (race.subraces ?? []).length > 0);
const SAVED_PANEL = {
  ...CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  draft: {
    ...CREATION_PANEL_CUSTOM_DRAFT_SAMPLE.draft,
    race: SUBRACED.key,
    subrace: SUBRACED.subraces[0],
    affinity_elements: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE.draft.affinity_elements.slice(0, 1),
  },
};
const OTHER_SEX = CREATION_PANEL_SAMPLE.custom.sex.find((option) => option.key !== SAVED_PANEL.draft.sex)?.key
  ?? CREATION_PANEL_SAMPLE.custom.sex[0].key;

describe("creation portrait request ownership (real store)", () => {
  let store;
  let sender;
  let host;
  let app;
  let revision;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    revision = 1;
  });

  afterEach(() => {
    app?.unmount();
    document.body.innerHTML = "";
    host = null;
    app = null;
    store.$dispose();
  });

  async function flush() {
    await nextTick();
    await nextTick();
    await nextTick();
  }

  async function mountWith(panel = SAVED_PANEL) {
    store.beginTransport(1);
    store.setConnected(true);
    store.setLoggedIn(true);
    expect(
      store.receive(1, "ui_snapshot", [fx.snapshot({ mode: "creation", revision, panels: { creation: structuredClone(panel) } })], {}).accepted,
    ).toBe(true);
    host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    app = mount(AppClient, { attachTo: host });
    await flush();
    expect(q("creation-overlay").getAttribute("data-mode")).toBe("custom");
  }

  async function publish(portrait, { panel = SAVED_PANEL, generation = 1 } = {}) {
    revision += 1;
    expect(
      store.receive(generation, "ui_update", [fx.update({ mode: "creation", revision, panels: { creation: structuredClone({ ...panel, portrait }) } })], {}).accepted,
    ).toBe(true);
    await flush();
  }

  async function result(request, overrides = {}) {
    expect(
      store.receive(1, "ui_action_result", [fx.actionResult({ request_id: request.request_id, presentation_revision: revision + 1, ...overrides })], {}).accepted,
    ).toBe(true);
    await flush();
  }

  const q = (id) => document.querySelector(tid(id));
  const drawer = () => document.querySelector('[data-drawer-key="creation-portrait"]');
  const portraitActions = () => sender.sent.actions.filter((action) => action.action_id === PORTRAIT_ACTION);
  const otherMutations = () => sender.sent.actions.filter((action) => action.action_id !== PORTRAIT_ACTION);

  async function edit(id, value) {
    await app.find(tid(id)).setValue(value);
  }

  async function openDrawer() {
    const button = q("creation-portrait-generate");
    button.focus();
    button.click();
    await flush();
    expect(drawer()).not.toBeNull();
    return button;
  }

  async function typePrompt(text) {
    const textarea = drawer().querySelector("textarea");
    textarea.value = text;
    textarea.dispatchEvent(new Event("input"));
    await flush();
  }

  async function submitDrawer() {
    drawer().querySelector(tid("gallery-generate__submit")).click();
    await flush();
  }

  it("opening the drawer receives the free-text-only model in creation context and sends nothing", async () => {
    await mountWith();
    await openDrawer();
    const component = app.findComponent(GalleryGenerateDrawer);
    expect(component.props("context")).toBe("creation");
    expect(component.props("model").capabilities).toStrictEqual({ supports_field_selection: false, supports_free_text: true, max_cards: 1 });
    expect(component.props("model").equipment_summary).toBeNull();
    expect(drawer().querySelectorAll('input[type="checkbox"]')).toHaveLength(0);
    expect(sender.sent.actions).toHaveLength(0);
    expect(sender.sent.syncs).toBe(0);
  });

  it("submit sends exactly one generate with the current identity and only the drawer prompt", async () => {
    await mountWith();
    await app.find(tid("creation-mode-concept")).trigger("click");
    await edit("creation-field-concept", "不得外洩的概念");
    await app.find(tid("creation-mode-custom")).trigger("click");
    await edit("creation-field-displayName", "不得送出的名字");
    await edit("creation-field-age", "60");
    await edit("creation-field-apparentAge", "37");
    await edit("creation-sex", OTHER_SEX);
    await openDrawer();
    await typePrompt("回頭凝視");
    await submitDrawer();
    expect(portraitActions()).toHaveLength(1);
    const { payload } = portraitActions()[0];
    expect(payload).toStrictEqual({
      race: SAVED_PANEL.draft.race,
      subrace: SAVED_PANEL.draft.subrace,
      sex: OTHER_SEX,
      apparent_age: 37,
      custom_prompt: "回頭凝視",
    });
    expect(otherMutations()).toHaveLength(0);
  });

  it("a gate-held submit keeps the drawer and prompt with rejection feedback and sends nothing", async () => {
    await mountWith();
    await openDrawer();
    await typePrompt("保留");
    // Another mutation holds the single-dispatch gate.
    store.dispatchAction("creation.roll_name", { race: SAVED_PANEL.draft.race, subrace: SAVED_PANEL.draft.subrace, sex: SAVED_PANEL.draft.sex });
    await flush();
    const before = sender.sent.actions.length;
    app.findComponent(GalleryGenerateDrawer).vm.$emit("submit", { fields: [], custom_prompt: "保留" });
    await flush();
    expect(sender.sent.actions.length).toBe(before);
    expect(drawer()).not.toBeNull();
    expect(app.findComponent(GalleryGenerateDrawer).props("rejected")).toBe(true);
    expect(drawer().querySelector("textarea").value).toBe("保留");
  });

  for (const outcome of ["rejected", "stale"]) {
    it(`a correlated ${outcome} result keeps the editable prompt and never resubmits`, async () => {
      await mountWith();
      await openDrawer();
      await typePrompt("再一次");
      await submitDrawer();
      expect(portraitActions()).toHaveLength(1);
      expect(drawer().querySelector("textarea").disabled).toBe(true);
      await result(portraitActions()[0], { outcome, code: outcome === "stale" ? "stale_revision" : "portrait_in_flight", message: "未完成。" });
      expect(drawer()).not.toBeNull();
      expect(app.findComponent(GalleryGenerateDrawer).props("rejected")).toBe(true);
      const textarea = drawer().querySelector("textarea");
      expect(textarea.value).toBe("再一次");
      // The shared gate releases with the result's declared revision.
      await publish(CREATION_PORTRAIT_STATES.empty);
      expect(drawer()).not.toBeNull();
      expect(textarea.disabled).toBe(false);
      expect(textarea.value).toBe("再一次");
      expect(portraitActions()).toHaveLength(1);
    });
  }

  it("a foreign result never settles the request", async () => {
    await mountWith();
    await openDrawer();
    await submitDrawer();
    expect(
      store.receive(1, "ui_action_result", [fx.actionResult({ request_id: "foreign:9", outcome: "success", presentation_revision: revision })], {}).accepted !== undefined,
    ).toBe(true);
    await flush();
    expect(drawer()).not.toBeNull();
    expect(app.findComponent(GalleryGenerateDrawer).props("disabled")).toBe(true);
  });

  it("success closes the drawer only after its pending publication, returning focus to the slot", async () => {
    await mountWith();
    const opener = await openDrawer();
    await submitDrawer();
    const request = portraitActions()[0];
    // Result first: the gate still waits for the declared revision.
    await result(request, { code: "portrait_requested" });
    expect(drawer()).not.toBeNull();
    await publish(CREATION_PORTRAIT_STATES.pending);
    expect(drawer()).toBeNull();
    expect(q("creation-portrait-status").getAttribute("data-state")).toBe("pending");
    expect(document.activeElement === opener || q("creation-portrait-slot").contains(document.activeElement)).toBe(true);
  });

  it("the pending publication arriving before the result still closes on the correlated success", async () => {
    await mountWith();
    await openDrawer();
    await submitDrawer();
    const request = portraitActions()[0];
    await publish(CREATION_PORTRAIT_STATES.pending);
    expect(drawer()).not.toBeNull();
    expect(
      store.receive(1, "ui_action_result", [fx.actionResult({ request_id: request.request_id, presentation_revision: revision })], {}).accepted,
    ).toBe(true);
    await flush();
    expect(drawer()).toBeNull();
    expect(portraitActions()).toHaveLength(1);
  });

  it("a synchronous send failure clears the submitting state without resending", async () => {
    await mountWith();
    await openDrawer();
    sender.sendAction = () => {
      throw new Error("socket closed");
    };
    await typePrompt("仍在");
    await submitDrawer();
    expect(drawer()).not.toBeNull();
    const textarea = drawer().querySelector("textarea");
    expect(textarea.disabled).toBe(false);
    expect(textarea.value).toBe("仍在");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("form values and the step survive pending to ready, and completion saves or activates nothing", async () => {
    await mountWith();
    await edit("creation-field-displayName", "本地名字");
    await openDrawer();
    await submitDrawer();
    await result(portraitActions()[0]);
    await publish(CREATION_PORTRAIT_STATES.pending);
    await app.find(tid("creation-steps-tab-story")).trigger("click");
    await edit("creation-background", "本地背景");
    await publish(CREATION_PORTRAIT_STATES.ready);
    expect(q("creation-field-displayName").value).toBe("本地名字");
    expect(q("creation-background").value).toBe("本地背景");
    expect(document.querySelector('[aria-current="step"]').getAttribute("data-testid")).toBe("creation-steps-tab-story");
    expect(q("creation-portrait-artwork")).not.toBeNull();
    expect(q("creation-confirm")).toBeNull();
    expect(otherMutations()).toHaveLength(0);
    expect(portraitActions()).toHaveLength(1);
  });

  it("Escape closes only the drawer, restoring focus, and the creation stage stays put", async () => {
    await mountWith();
    const opener = await openDrawer();
    const stageBefore = store.view.creationView?.stage ?? null;
    const textarea = drawer().querySelector("textarea");
    textarea.focus();
    textarea.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
    await flush();
    expect(drawer()).toBeNull();
    expect(document.activeElement).toBe(opener);
    expect(store.view.creationView?.stage ?? null).toBe(stageBefore);
    expect(q("creation-overlay").getAttribute("data-mode")).toBe("custom");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("unavailability while the drawer is open disables submit, keeps the prompt and refreshes through manual sync only", async () => {
    await mountWith();
    await openDrawer();
    await typePrompt("等服務回來");
    await publish(CREATION_PORTRAIT_STATES.unavailable);
    expect(drawer()).not.toBeNull();
    expect(drawer().querySelector(tid("gallery-generate__submit")).disabled).toBe(true);
    expect(drawer().querySelector("textarea").value).toBe("等服務回來");
    expect(drawer().textContent).toContain(CREATION_PORTRAIT_STATES.unavailable.reason);
    drawer().querySelector(tid("gallery-generate__refresh")).click();
    await flush();
    expect(sender.sent.syncs).toBe(1);
    expect(sender.sent.actions).toHaveLength(0);
    // A refreshed unknown/healthy panel re-enables only explicit submission.
    await publish(CREATION_PORTRAIT_STATES.empty);
    expect(drawer().querySelector(tid("gallery-generate__submit")).disabled).toBe(false);
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("the slot refresh reaches manual sync and generates nothing; the rest of creation stays usable", async () => {
    await mountWith({ ...SAVED_PANEL, portrait: CREATION_PORTRAIT_STATES.unavailable });
    expect(q("creation-portrait-generate").disabled).toBe(true);
    expect(q("creation-portrait-status").textContent).toContain(CREATION_PORTRAIT_STATES.unavailable.reason);
    q("creation-portrait-refresh").click();
    await flush();
    expect(sender.sent.syncs).toBe(1);
    expect(sender.sent.actions).toHaveLength(0);
    // The rest of creation is untouched by the art outage: fields edit and
    // other creation actions still dispatch.
    await edit("creation-field-displayName", "照常填寫");
    expect(q("creation-field-displayName").value).toBe("照常填寫");
    await app.find(tid("creation-roll-name")).trigger("click");
    expect(sender.sent.actions.map((action) => action.action_id)).toStrictEqual(["creation.roll_name"]);
  });

  it("a new presentation context closes the drawer and forgets the request without retrying", async () => {
    await mountWith();
    await openDrawer();
    await submitDrawer();
    expect(portraitActions()).toHaveLength(1);
    // A reconnect: a fresh transport generation reads the server state anew.
    store.beginTransport(2);
    store.setConnected(true);
    revision = 1;
    expect(
      store.receive(2, "ui_snapshot", [fx.snapshot({ mode: "creation", revision, presentation_epoch: fx.EPOCH_B, panels: { creation: structuredClone({ ...SAVED_PANEL, portrait: CREATION_PORTRAIT_STATES.pending }) } })], {}).accepted,
    ).toBe(true);
    await flush();
    expect(drawer()).toBeNull();
    expect(q("creation-portrait-status").getAttribute("data-state")).toBe("pending");
    expect(portraitActions()).toHaveLength(1);
  });
});
