import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import DetailFooter from "../../components/DetailFooter.vue";
import QuestDetail from "../../components/QuestDetail.vue";
import { bookActions, bookDetail } from "../../components/quest-drawer-model.js";

// Synthetic descriptors: every label and key here is a fixture, not shipped copy.
const plain = (key, extra = {}) => ({ key, label: `label-${key}`, tone: "plain", testid: `btn-${key}`, ...extra });

describe("DetailFooter (handbook-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountFooter(props) {
    wrapper = mount(DetailFooter, { attachTo: document.body, props });
    return wrapper;
  }

  const btn = (key) => wrapper.get(`[data-testid="btn-${key}"]`);

  it("renders the buttons in order with their tone classes and testids", () => {
    mountFooter({
      testid: "footer-root",
      buttons: [plain("a"), plain("b", { tone: "ghost" }), plain("c", { tone: "primary" }), plain("d", { tone: "danger" })],
    });
    expect(wrapper.get('[data-testid="footer-root"]').element.tagName).toBe("FOOTER");
    const buttons = wrapper.findAll("button");
    expect(buttons.map((b) => b.attributes("data-testid"))).toEqual(["btn-a", "btn-b", "btn-c", "btn-d"]);
    expect(btn("a").classes()).toEqual(["detail-footer__btn"]);
    expect(btn("b").classes()).toContain("detail-footer__btn--ghost");
    expect(btn("c").classes()).toContain("detail-footer__btn--primary");
    expect(btn("d").classes()).toContain("detail-footer__btn--danger");
  });

  it("keeps a disabled button focusable with aria-disabled and emits nothing", async () => {
    mountFooter({
      reason: "why-text",
      reasonTestid: "why",
      buttons: [plain("x", { enabled: false, describedByReason: true }), plain("y", { enabled: false })],
    });
    const x = btn("x");
    expect(x.attributes("aria-disabled")).toBe("true");
    expect(x.attributes("disabled")).toBeUndefined();
    expect(x.classes()).toContain("is-disabled");
    const reason = wrapper.get('[data-testid="why"]');
    expect(x.attributes("aria-describedby")).toBe(reason.attributes("id"));
    expect(btn("y").attributes("aria-describedby")).toBeUndefined();
    x.element.focus();
    expect(document.activeElement).toBe(x.element);
    await x.trigger("click");
    expect(wrapper.emitted("press")).toBeUndefined();
  });

  it("gives a toggle aria-pressed and the native disabled attribute", () => {
    mountFooter({
      buttons: [plain("off", { pressed: false, enabled: false }), plain("on", { pressed: true })],
    });
    const off = btn("off");
    expect(off.attributes("disabled")).toBeDefined();
    expect(off.attributes("aria-disabled")).toBeUndefined();
    expect(off.attributes("aria-pressed")).toBe("false");
    expect(off.classes()).not.toContain("is-on");
    const on = btn("on");
    expect(on.attributes("disabled")).toBeUndefined();
    expect(on.attributes("aria-pressed")).toBe("true");
    expect(on.classes()).toContain("is-on");
    expect(wrapper.findAll("button").every((b) => b.attributes("aria-pressed") !== undefined)).toBe(true);
  });

  it("omits aria-pressed on a non-toggle button", () => {
    mountFooter({ buttons: [plain("a")] });
    expect(btn("a").attributes("aria-pressed")).toBeUndefined();
  });

  it("emits press once per activation with the button key", async () => {
    mountFooter({ buttons: [plain("a"), plain("t", { pressed: false })] });
    await btn("a").trigger("click");
    expect(wrapper.emitted("press")).toEqual([["a"]]);
    await btn("t").trigger("click");
    await btn("a").trigger("click");
    expect(wrapper.emitted("press")).toEqual([["a"], ["t"], ["a"]]);
  });

  it("focuses the button named by focus(key), also after the list changes", async () => {
    mountFooter({ buttons: [plain("a"), plain("b")] });
    wrapper.vm.focus("b");
    expect(document.activeElement).toBe(btn("b").element);
    await wrapper.setProps({ buttons: [plain("c"), plain("d")] });
    wrapper.vm.focus("c");
    expect(document.activeElement).toBe(btn("c").element);
    // A key that left the list focuses nothing new.
    wrapper.vm.focus("a");
    expect(document.activeElement).toBe(btn("c").element);
  });

  it("renders an armed reason with role alert and the danger tone", () => {
    mountFooter({ reason: "warn", reasonTone: "danger", reasonRole: "alert", reasonTestid: "why", buttons: [] });
    const reason = wrapper.get('[data-testid="why"]');
    expect(reason.attributes("role")).toBe("alert");
    expect(reason.classes()).toContain("detail-footer__why--danger");
    expect(reason.text()).toBe("warn");
  });

  it("renders a plain reason with no role, and no reason line when null", async () => {
    mountFooter({ reason: "plain", reasonTestid: "why" });
    const reason = wrapper.get('[data-testid="why"]');
    expect(reason.attributes("role")).toBeUndefined();
    expect(reason.classes()).not.toContain("detail-footer__why--danger");
    await wrapper.setProps({ reason: null });
    expect(wrapper.find('[data-testid="why"]').exists()).toBe(false);
  });

  it("inserts a spacer before a spacerBefore button and draws its glyph", () => {
    mountFooter({ buttons: [plain("a"), plain("b", { spacerBefore: true, glyph: "track_flag" })] });
    const children = [...wrapper.get("footer").element.children];
    expect(children.map((el) => el.tagName)).toEqual(["BUTTON", "SPAN", "BUTTON"]);
    expect(children[1].classList.contains("detail-footer__spacer")).toBe(true);
    expect(btn("b").find("svg path").attributes("d")).toBeTruthy();
    expect(btn("a").find("svg").exists()).toBe(false);
  });

  describe("the quest footer through DetailFooter", () => {
    const row = {
      quest_id: "q_syn",
      state: "in_progress",
      name: "synthetic quest",
      tracked: false,
      track: { action_id: "guild.quest_track", label: "track-label", enabled: true, disabled_reason: null, quantity: null },
      abandon: { action_id: "guild.quest_abandon", label: "abandon-label", enabled: true, disabled_reason: null, quantity: null },
    };

    it("keeps every footer testid, focuses cancel on arming and emits the descriptor actions", async () => {
      wrapper = mount(QuestDetail, {
        attachTo: document.body,
        props: { detail: bookDetail(row), actions: bookActions(row, null) },
      });
      const get = (id) => wrapper.get(`[data-testid="quest-drawer__${id}"]`);
      expect(wrapper.findComponent(DetailFooter).attributes("data-testid")).toBe("quest-drawer__actions");
      expect(get("abandon").exists()).toBe(true);
      expect(get("track").attributes("aria-pressed")).toBe("false");
      await get("track").trigger("click");
      expect(wrapper.emitted("action")).toEqual([
        [{ action_id: "guild.quest_track", payload: { quest_id: "q_syn", tracked: true } }],
      ]);
      await get("abandon").trigger("click");
      await wrapper.vm.$nextTick();
      expect(get("abandon-confirm").attributes("role")).toBe("alert");
      expect(document.activeElement).toBe(get("abandon-confirm-no").element);
      await get("abandon-confirm-yes").trigger("click");
      expect(wrapper.emitted("action")[1]).toEqual([
        { action_id: "guild.quest_abandon", payload: { quest_id: "q_syn" } },
      ]);
    });
  });
});
