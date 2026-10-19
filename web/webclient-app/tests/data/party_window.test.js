// webclient-party-window-member-tab: the party window shell. The rail lists
// the committed `party` v3 rows plus 空位 while the general quota has room,
// a selection sends one `view-member` with the open tab, the rail adopts only
// the server's `viewed_member_id` (pending meanwhile), a changed viewed member
// resets the local item and quantity, the window remembers its tab for the
// session, and it renders identically whether or not the player possesses.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab, resetPartyWindowMemory } from "../../components/party-window-memory.js";
import {
  PARTY_INVENTORY_PURSE_SAMPLE,
  PARTY_MEMBER_COMPANION_SAMPLE,
  PARTY_MEMBER_PANEL_SAMPLE,
  PARTY_MEMBER_POSSESSED_SAMPLE,
  PARTY_PANEL_FULL_SAMPLE,
  PARTY_WINDOW_PANEL_SAMPLE,
  PARTY_BAG_HOLDINGS_CONSUMABLE,
  PARTY_BAG_HOLDINGS_NONE,
  PARTY_BAG_INVENTORY_SAMPLE,
} from "../../stories/fixtures/party_panels.js";

const SCOPE = "1|1";

describe("PartyWindow (webclient-party-window-member-tab)", () => {
  let wrapper;

  beforeEach(() => {
    resetPartyWindowMemory();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountWindow(props = {}, slots = {}) {
    wrapper = mount(PartyWindow, {
      attachTo: document.body,
      props: {
        party: PARTY_WINDOW_PANEL_SAMPLE,
        partyMember: PARTY_MEMBER_COMPANION_SAMPLE,
        partyInventory: PARTY_INVENTORY_PURSE_SAMPLE,
        memoryScope: SCOPE,
        ...props,
      },
      slots,
    });
    return wrapper;
  }

  const entry = (id) => wrapper.get(`[data-testid="member-rail__entry--${id}"]`);
  const KEYS = { 成員: "member", 背包: "bag", 狀態: "status", 技能: "skills", 系譜: "lineage" };
  const tab = (label) => wrapper.get(`[data-testid="icon-tabs__tab--${KEYS[label]}"]`);

  it("frames the window with the five tabs in order, the purse and the quota", () => {
    mountWindow();
    const labels = wrapper.findAll('[data-testid="window-frame__tabs"] [role="tab"]').map((node) => node.attributes("aria-label"));
    expect(labels).toEqual(["成員", "背包", "狀態", "技能", "系譜"]);
    expect(wrapper.get(".drawer-header__title").text()).toBe("隊伍");
    expect(wrapper.get('[data-testid="hud-drawer"]').attributes("data-drawer-key")).toBe("party");
    expect(wrapper.get('[data-testid="party-window__purse"]').text()).toBe("1,240 銅");
    expect(wrapper.get('[data-testid="party-window__quota"]').text()).toBe("同伴 2 / 4");
  });

  it("lists the committed rows commander first, then 空位 while the quota has room", () => {
    mountWindow();
    const entries = wrapper.findAll('[data-testid^="member-rail__entry--"]').map((node) => node.attributes("data-testid"));
    expect(entries).toEqual([
      "member-rail__entry--42",
      "member-rail__entry--101",
      "member-rail__entry--102",
      "member-rail__entry--103",
      "member-rail__entry--empty",
    ]);
    expect(entry(101).attributes("aria-current")).toBe("true");
    expect(entry(102).text()).toContain("倒地");
    wrapper.unmount();
    mountWindow({ party: PARTY_PANEL_FULL_SAMPLE });
    expect(wrapper.find('[data-testid="member-rail__entry--empty"]').exists()).toBe(false);
  });

  it("dispatches one selection with the open tab and keeps that tab", async () => {
    mountWindow();
    await tab("狀態").trigger("click");
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("status");
    await entry(42).trigger("click");
    expect(wrapper.emitted("view-member")).toEqual([[{ memberId: 42, tab: "status" }]]);
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("status");
    // Activating the already viewed member sends nothing.
    await entry(101).trigger("click");
    expect(wrapper.emitted("view-member")).toHaveLength(1);
  });

  it("marks the requested entry pending and adopts only the server's selection", async () => {
    mountWindow();
    await entry(42).trigger("click");
    await wrapper.setProps({ pendingMemberId: 42 });
    // No optimistic switch: 蕾娜 stays selected while 影行者 is pending.
    expect(entry(101).attributes("aria-current")).toBe("true");
    expect(entry(42).attributes("aria-current")).toBeUndefined();
    expect(entry(42).attributes("aria-busy")).toBe("true");
    await wrapper.setProps({
      pendingMemberId: null,
      party: { ...PARTY_WINDOW_PANEL_SAMPLE, viewed_member_id: 42 },
      partyMember: PARTY_MEMBER_PANEL_SAMPLE,
    });
    expect(entry(42).attributes("aria-current")).toBe("true");
    expect(entry(42).attributes("aria-busy")).toBeUndefined();
    expect(wrapper.get('[data-testid="party-member-tab"]').attributes("data-member")).toBe("42");
  });

  it("keeps the selection when a request ends without a server change", async () => {
    mountWindow({ pendingMemberId: 42 });
    await wrapper.setProps({ pendingMemberId: null });
    expect(entry(101).attributes("aria-current")).toBe("true");
    expect(entry(42).attributes("aria-busy")).toBeUndefined();
  });

  it("resets the local item and quantity when the server falls back to the commander", async () => {
    rememberPartyWindowTab(SCOPE, "bag");
    mountWindow({ partyInventory: PARTY_BAG_INVENTORY_SAMPLE, itemHoldings: PARTY_BAG_HOLDINGS_CONSUMABLE });
    // 苦艾藥水 is the committed selection; raise the give quantity to 3.
    expect(wrapper.get('[data-testid="party-bag-tab__title"]').text()).toBe("苦艾藥水");
    await wrapper.get('[data-testid="party-bag-tab__stepper-up"]').trigger("click");
    await wrapper.get('[data-testid="party-bag-tab__stepper-up"]').trigger("click");
    expect(wrapper.get('[data-testid="party-bag-tab__quantity"]').text()).toBe("3");
    // A row selection sends one view-item for the viewed member.
    await wrapper.get('[data-testid="party-bag-tab__row--rye_bread"]').trigger("click");
    expect(wrapper.emitted("view-item")).toEqual([[{ memberId: 101, itemKey: "rye_bread" }]]);
    // 蕾娜 left the party: the server's next payload names the commander and
    // the commander's bag with no selected item.
    await wrapper.setProps({
      party: {
        ...PARTY_WINDOW_PANEL_SAMPLE,
        viewed_member_id: 42,
        slots: PARTY_WINDOW_PANEL_SAMPLE.slots.filter((row) => row.identity !== 101),
      },
      partyInventory: { ...PARTY_BAG_INVENTORY_SAMPLE, member_id: 42 },
      itemHoldings: { ...PARTY_BAG_HOLDINGS_NONE, giver_id: 42 },
      pendingItemKey: "rye_bread",
    });
    expect(entry(42).attributes("aria-current")).toBe("true");
    expect(wrapper.get('[data-testid="party-bag-tab"]').attributes("data-member")).toBe("42");
    // The requested key was reset with the member, so the in-flight key no
    // longer shows and nothing stays selected.
    expect(wrapper.find('[data-testid="party-bag-tab__title"]').exists()).toBe(false);
    expect(wrapper.findAll('[role="option"][aria-selected="true"]')).toHaveLength(0);
  });

  it("cancels the bag's open use confirmation on a close attempt before closing", async () => {
    rememberPartyWindowTab(SCOPE, "bag");
    mountWindow({ partyInventory: PARTY_BAG_INVENTORY_SAMPLE, itemHoldings: PARTY_BAG_HOLDINGS_CONSUMABLE });
    await wrapper.get('[data-testid="action-bar__btn--use"]').trigger("click");
    expect(wrapper.find('[data-testid="party-bag-tab__confirm-dialog"]').exists()).toBe(true);
    // ✕ while confirming cancels the confirmation and keeps the window.
    await wrapper.get('[data-testid="hud-drawer-close"]').trigger("click");
    expect(wrapper.emitted("close")).toBeUndefined();
    expect(wrapper.find('[data-testid="party-bag-tab__confirm-dialog"]').exists()).toBe(false);
    expect(wrapper.emitted("bag-action")).toBeUndefined();
  });

  it("selects 空位 locally, opening 成員, and sends nothing", async () => {
    rememberPartyWindowTab(SCOPE, "status");
    mountWindow();
    await wrapper.get('[data-testid="member-rail__entry--empty"]').trigger("click");
    expect(wrapper.emitted("view-member")).toBeUndefined();
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("member");
    expect(wrapper.get('[data-testid="member-rail__entry--empty"]').attributes("aria-current")).toBe("true");
    expect(wrapper.get('[data-testid="party-member-tab"]').attributes("data-member")).toBe("empty");
    // Back to the viewed member: a local switch, still no dispatch.
    await entry(101).trigger("click");
    expect(wrapper.emitted("view-member")).toBeUndefined();
    expect(entry(101).attributes("aria-current")).toBe("true");
  });

  it("keeps 空位 selected while a requested member is pending, then adopts it", async () => {
    mountWindow();
    await wrapper.get('[data-testid="member-rail__entry--empty"]').trigger("click");
    await entry(102).trigger("click");
    expect(wrapper.emitted("view-member")).toEqual([[{ memberId: 102, tab: "member" }]]);
    await wrapper.setProps({ pendingMemberId: 102 });
    expect(wrapper.get('[data-testid="member-rail__entry--empty"]').attributes("aria-current")).toBe("true");
    expect(entry(102).attributes("aria-busy")).toBe("true");
    await wrapper.setProps({ pendingMemberId: null, party: { ...PARTY_WINDOW_PANEL_SAMPLE, viewed_member_id: 102 } });
    expect(entry(102).attributes("aria-current")).toBe("true");
  });

  it("refuses one close while a persona draft is unsaved, then closes", async () => {
    mountWindow({ party: { ...PARTY_WINDOW_PANEL_SAMPLE, viewed_member_id: 42 }, partyMember: PARTY_MEMBER_PANEL_SAMPLE });
    await wrapper.get('[data-testid="action-bar__btn--persona-edit"]').trigger("click");
    await wrapper.get('[data-testid="party-member-tab__persona-edit--habit"]').trigger("click");
    await wrapper.get('[data-testid="party-member-tab__persona-input--habit"]').setValue("新的習慣");
    expect(wrapper.get('[data-testid="action-bar__btn--persona-done"]').attributes("aria-disabled")).toBe("true");
    await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toBeUndefined();
    expect(wrapper.get('[data-testid="party-member-tab__unsaved-warning"]').text()).toBe("尚有未儲存的人物設定。");
    expect(wrapper.get('[data-testid="party-member-tab__persona-input--habit"]').element.value).toBe("新的習慣");
    await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(wrapper.emitted("persona-edit")).toBeUndefined();
  });

  it("reopens on its last tab for the session and forgets it on a new scope", async () => {
    mountWindow();
    await tab("技能").trigger("click");
    wrapper.unmount();
    mountWindow();
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("skills");
    wrapper.unmount();
    mountWindow({ memoryScope: "2|1" });
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("member");
  });

  it("shows an unbuilt tab's backing reason and invents no rows", async () => {
    rememberPartyWindowTab(SCOPE, "lineage");
    mountWindow({ lineage: { schema_version: 2, available: false, reason: { code: "lineage_unavailable", message: "系譜目前無法顯示。" } } });
    expect(wrapper.get('[data-testid="party-window__tab-unavailable"]').text()).toBe("系譜目前無法顯示。");
    wrapper.unmount();
    mountWindow();
    expect(wrapper.get('[data-testid="list-detail__list"]').text()).toBe("");
  });

  it("states the party panel's reason when it is unavailable", () => {
    mountWindow({ party: { schema_version: 3, available: false, reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" } } });
    expect(wrapper.get('[data-testid="party-window__unavailable"]').text()).toBe("隊伍資訊目前無法顯示");
    expect(wrapper.find('[data-testid="member-rail"]').exists()).toBe(false);
  });

  it("renders the rail, the tabs and the content identically with and without possession", () => {
    // The window has no possession input: the same committed panels render
    // the same markup, with no "you" marker, whatever the player controls.
    expect(Object.keys(PartyWindow.props)).not.toContain("possessing");
    mountWindow({ partyMember: PARTY_MEMBER_COMPANION_SAMPLE });
    const free = wrapper.get('[data-testid="member-rail"]').html();
    const tabs = wrapper.get('[data-testid="window-frame__tabs"]').html();
    wrapper.unmount();
    mountWindow({ partyMember: PARTY_MEMBER_COMPANION_SAMPLE });
    expect(wrapper.get('[data-testid="member-rail"]').html()).toBe(free);
    expect(wrapper.get('[data-testid="window-frame__tabs"]').html()).toBe(tabs);
    expect(wrapper.text()).not.toMatch(/你|自己|操控中/);
    // While possessing, only the possession descriptor itself changes.
    wrapper.unmount();
    mountWindow({ partyMember: PARTY_MEMBER_POSSESSED_SAMPLE });
    expect(wrapper.get('[data-testid="member-rail"]').html()).toBe(free);
    expect(wrapper.get('[data-testid="action-bar__btn--possess"]').text()).toBe("解除附身");
  });

  it("cancels an armed leave on Escape instead of closing, and sends nothing", async () => {
    mountWindow();
    await wrapper.get('[data-testid="action-bar__btn--leave"]').trigger("click");
    expect(wrapper.find('[data-testid="party-member-tab__leave-warning"]').exists()).toBe(true);
    await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toBeUndefined();
    expect(wrapper.emitted("action")).toBeUndefined();
    expect(wrapper.find('[data-testid="party-member-tab__leave-warning"]').exists()).toBe(false);
    await wrapper.get('[data-testid="hud-drawer"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
  });
});
