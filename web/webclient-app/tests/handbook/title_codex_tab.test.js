import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import TitleCodexTab from "../../components/handbook/TitleCodexTab.vue";
import { resetQuestDrawerMemory } from "../../components/quest-drawer-memory.js";
import { BALLOT, UNAVAILABLE_CODEX, epithetRow, titleCodex } from "../../stories/fixtures/title_codex_panels.js";

describe("TitleCodexTab (handbook-titles-tab)", () => {
  let wrapper;

  beforeEach(() => resetQuestDrawerMemory());

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountTab(codex = titleCodex(), props = {}) {
    wrapper = mount(TitleCodexTab, {
      attachTo: document.body,
      props: { codex, memoryScope: "1|1", ...props },
    });
    return wrapper;
  }

  const find = (id) => wrapper.find(`[data-testid="handbook__${id}"]`);
  const railTab = (key) => wrapper.get(`[data-testid="handbook__titles-rail"] [data-tab-key="${key}"]`);
  const railKeys = () =>
    wrapper.findAll('[data-testid="handbook__titles-rail"] [role="tab"]').map((tab) => tab.attributes("data-tab-key"));
  const selectedRail = () =>
    wrapper.get('[data-testid="handbook__titles-rail"] [role="tab"][aria-selected="true"]').attributes("data-tab-key");
  const detailId = () => find("detail").attributes("data-detail-id");
  const actions = () => wrapper.emitted("action") ?? [];
  const row = (id) => wrapper.get(`[data-quest-id="${id}"]`);

  async function openRail(key) {
    await railTab(key).trigger("click");
  }

  async function arm(display = "合成異名甲") {
    await openRail("epithet");
    await row(display).trigger("click");
    await find("remove").trigger("click");
    await nextTick();
  }

  describe("the rail", () => {
    it("lists the six categories and the epithet entry without a ballot", () => {
      mountTab();
      expect(railKeys()).toEqual(["combat", "spell", "explore", "guild", "clergy", "romance", "epithet"]);
    });

    it("ends with a hot ballot entry carrying the ballot's length", () => {
      mountTab(titleCodex({ pending_ballot: BALLOT }));
      expect(railKeys().at(-1)).toBe("ballot");
      expect(railTab("ballot").attributes("aria-label")).toBe("提名（2）");
    });

    it("counts a category's unlocked rows", () => {
      mountTab();
      // combat holds three rows of which one is unlocked.
      expect(railTab("combat").attributes("aria-label")).toBe("戰鬥（1）");
    });

    it("falls back to the epithet entry when a commit empties the ballot", async () => {
      mountTab(titleCodex({ pending_ballot: BALLOT }));
      await openRail("ballot");
      expect(find("ballot-accept").exists()).toBe(true);
      await wrapper.setProps({ codex: titleCodex() });
      expect(selectedRail()).toBe("epithet");
      expect(wrapper.find('[data-quest-id="合成提名甲"]').exists()).toBe(false);
      expect(find("ballot-accept").exists()).toBe(false);
    });

    it("keeps a locked medal's name and shows its hint in the detail", async () => {
      mountTab();
      await wrapper.get('[data-tile="t_beta"]').trigger("click");
      expect(find("medal--t_beta").attributes("data-locked")).toBe("true");
      expect(detailId()).toBe("t_beta");
      expect(find("detail").text()).toContain("乙稱號");
      expect(find("section").text()).toContain("完成合成條件乙。");
    });
  });

  describe("equip", () => {
    it("emits one fixed equip for an unlocked, unequipped row", async () => {
      mountTab();
      await openRail("guild");
      await find("equip").trigger("click");
      expect(actions()).toEqual([[{ action_id: "title.equip", payload: { kind: "fixed", identifier: "g_x_rank" } }]]);
    });

    it("emits one epithet equip for an unequipped epithet", async () => {
      mountTab();
      await openRail("epithet");
      await find("equip").trigger("click");
      expect(actions()).toEqual([[{ action_id: "title.equip", payload: { kind: "epithet", identifier: "合成異名甲" } }]]);
    });

    it("disables equip with a reason for locked and equipped entries", async () => {
      mountTab();
      // The equipped fixed row is the default selection.
      expect(find("equip").attributes("aria-disabled")).toBe("true");
      expect(find("action-reason").exists()).toBe(true);
      await find("equip").trigger("click");
      await wrapper.get('[data-tile="t_beta"]').trigger("click");
      expect(find("equip").attributes("aria-disabled")).toBe("true");
      await find("equip").trigger("click");
      await openRail("epithet");
      await row("合成異名乙").trigger("click");
      expect(find("equip").attributes("aria-disabled")).toBe("true");
      await find("equip").trigger("click");
      expect(actions()).toEqual([]);
    });
  });

  describe("two-step removal", () => {
    it("renders the remove control only where can_remove is true", async () => {
      mountTab();
      await openRail("epithet");
      expect(find("remove").exists()).toBe(true);
      await row("合成異名乙").trigger("click");
      expect(find("remove").exists()).toBe(false);
    });

    it("moves focus to cancel on arming and emits one remove on confirm", async () => {
      mountTab();
      await arm();
      expect(document.activeElement).toBe(find("remove-cancel").element);
      expect(find("action-reason").attributes("role")).toBe("alert");
      expect(actions()).toEqual([]);
      await find("remove-confirm").trigger("click");
      expect(actions()).toEqual([[{ action_id: "title.remove", payload: { display: "合成異名甲" } }]]);
      expect(find("remove-confirm").exists()).toBe(false);
    });

    it("cancel disarms without emitting and returns focus to remove", async () => {
      mountTab();
      await arm();
      await find("remove-cancel").trigger("click");
      await nextTick();
      expect(find("remove-confirm").exists()).toBe(false);
      expect(document.activeElement).toBe(find("remove").element);
      expect(actions()).toEqual([]);
    });

    it("disarms on a selection change and on a rail change", async () => {
      mountTab();
      await arm();
      await row("合成異名乙").trigger("click");
      await row("合成異名甲").trigger("click");
      expect(find("remove-confirm").exists()).toBe(false);
      await find("remove").trigger("click");
      await nextTick();
      await openRail("combat");
      await openRail("epithet");
      expect(find("remove-confirm").exists()).toBe(false);
      expect(actions()).toEqual([]);
    });

    it("guardClose cancels an armed removal once, then allows the close", async () => {
      mountTab();
      expect(wrapper.vm.guardClose()).toBe(true);
      await arm();
      expect(wrapper.vm.guardClose()).toBe(false);
      await nextTick();
      expect(find("remove-confirm").exists()).toBe(false);
      expect(wrapper.vm.guardClose()).toBe(true);
      expect(actions()).toEqual([]);
    });

    it("does not stay armed when the armed epithet vanishes", async () => {
      mountTab();
      await arm();
      await wrapper.setProps({ codex: titleCodex({ epithet_rows: [epithetRow({ display: "合成異名乙", equipped: true, can_remove: false })] }) });
      expect(find("remove-confirm").exists()).toBe(false);
      expect(wrapper.vm.guardClose()).toBe(true);
    });
  });

  describe("the ballot", () => {
    it("accepts the second nominee with its one-based index", async () => {
      mountTab(titleCodex({ pending_ballot: BALLOT }));
      await openRail("ballot");
      await row("合成提名乙").trigger("click");
      expect(find("detail").text()).toContain("合成提名事蹟乙。");
      await find("ballot-accept").trigger("click");
      expect(actions()).toEqual([[{ action_id: "title.accept", payload: { index: 2 } }]]);
    });

    it("declines with an empty payload", async () => {
      mountTab(titleCodex({ pending_ballot: BALLOT }));
      await openRail("ballot");
      await find("ballot-decline").trigger("click");
      expect(actions()).toEqual([[{ action_id: "title.decline", payload: {} }]]);
    });
  });

  describe("focus ownership", () => {
    const railFocused = () => document.activeElement?.closest?.('[data-testid="handbook__titles-rail"]') != null;

    it("returns focus to the rail when a confirmed removal unmounts the footer control", async () => {
      mountTab();
      await arm();
      find("remove-confirm").element.focus();
      await find("remove-confirm").trigger("click");
      await nextTick();
      await nextTick();
      expect(railFocused()).toBe(true);
    });

    it("returns focus to the rail when an answered ballot leaves with its row", async () => {
      mountTab(titleCodex({ pending_ballot: BALLOT }));
      await openRail("ballot");
      find("ballot-accept").element.focus();
      await find("ballot-accept").trigger("click");
      await wrapper.setProps({ codex: titleCodex() });
      await nextTick();
      await nextTick();
      expect(railFocused()).toBe(true);
    });

    it("never pulls focus in from outside on a commit", async () => {
      const outside = document.createElement("button");
      document.body.appendChild(outside);
      mountTab(titleCodex({ pending_ballot: BALLOT }));
      await openRail("ballot");
      outside.focus();
      await wrapper.setProps({ codex: titleCodex() });
      await nextTick();
      await nextTick();
      expect(document.activeElement).toBe(outside);
    });
  });

  describe("honest degradation", () => {
    it("shows the shared empty state and no medal or row before the first commit", () => {
      mountTab(null);
      expect(find("titles-absent").exists()).toBe(true);
      expect(wrapper.find('[data-testid^="handbook__medal--"]').exists()).toBe(false);
      expect(wrapper.find('[role="option"]').exists()).toBe(false);
    });

    it("states an unavailable panel's reason", () => {
      mountTab(UNAVAILABLE_CODEX, { combat: true });
      expect(find("titles-unavailable").text()).toContain("合成的稱號冊不可用原因");
      expect(wrapper.find('[role="option"]').exists()).toBe(false);
    });

    it("falls back to the first row when the selected epithet is gone, then to the empty detail", async () => {
      mountTab();
      await openRail("epithet");
      await row("合成異名乙").trigger("click");
      expect(detailId()).toBe("合成異名乙");
      await wrapper.setProps({ codex: titleCodex({ epithet_rows: [epithetRow()] }) });
      expect(detailId()).toBe("合成異名甲");
      await wrapper.setProps({ codex: titleCodex({ epithet_rows: [] }) });
      expect(find("detail").exists()).toBe(false);
      expect(find("detail-empty").exists()).toBe(true);
    });
  });
});
