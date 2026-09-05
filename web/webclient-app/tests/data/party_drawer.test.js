import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import PartyDrawer from "../../components/PartyDrawer.vue";
import {
  PARTY_PANEL_SAMPLE,
  PARTY_PANEL_EMPTY_SAMPLE,
  PARTY_PANEL_FULL_SAMPLE,
  PARTY_COMBAT_PARTICIPANTS_SAMPLE,
  PARTY_INTERACT_TARGETS_SAMPLE,
  ART_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// webclient-align-05-party-hud: the 同伴 · 隊伍 drawer body.
// Renders compbig rows, bond stages, joined combat tokens,
// 請其離隊 confirmation contract, empty slot with invite preconditions,
// and verbatim follow rules.

describe("PartyDrawer (同伴 · 隊伍 drawer)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountDrawer(props = {}) {
    wrapper = mount(PartyDrawer, {
      props: {
        slots: PARTY_PANEL_SAMPLE.slots,
        combatParticipants: PARTY_COMBAT_PARTICIPANTS_SAMPLE,
        artPanel: ART_PANEL_SAMPLE,
        interactTargets: PARTY_INTERACT_TARGETS_SAMPLE,
        mode: "exploration",
        ...props,
      },
    });
    return wrapper;
  }

  it("renders compbig rows following the committed party slots", () => {
    const w = mountDrawer();

    const rows = w.findAll('[data-testid^="party-drawer__row-"]');
    expect(rows).toHaveLength(2);

    // Verify first row (蕾娜)
    const r1 = w.get('[data-testid="party-drawer__row-101"]');
    expect(r1.get('[data-testid="party-drawer__name"]').text()).toBe("蕾娜");
    expect(r1.get('[data-testid="party-drawer__bond"]').text()).toContain("親睦");
    expect(r1.get('[data-testid="party-drawer__meta"]').text()).toContain("HP 180/220");
    expect(r1.get('[data-testid="party-drawer__combat-token"]').text()).toContain("參戰 a2");

    // Verify second row (幽)
    const r2 = w.get('[data-testid="party-drawer__row-102"]');
    expect(r2.get('[data-testid="party-drawer__name"]').text()).toBe("幽");
    expect(r2.get('[data-testid="party-drawer__bond"]').text()).toContain("信賴");
    expect(r2.get('[data-testid="party-drawer__meta"]').text()).toContain("HP 144/160");
    expect(r2.get('[data-testid="party-drawer__combat-token"]').text()).toContain("參戰 a3");

    // No raw numeric affinity appears on companion rows (stage name only, no threshold numbers)
    expect(r1.text()).not.toContain("70");
    expect(r2.text()).not.toContain("70");
  });

  it("leaving dispatches explore.party_leave through the two-step confirmation contract", async () => {
    const w = mountDrawer();

    const r1 = w.get('[data-testid="party-drawer__row-101"]');
    const leaveBtn = r1.get('[data-testid="party-drawer__leave-btn"]');
    expect(leaveBtn.text()).toBe("請其離隊");

    // Step 1: Click 請其離隊 arms confirmation
    await leaveBtn.trigger("click");
    expect(w.emitted("action")).toBeUndefined();

    // 確認離隊 and 取消 appear
    const confirmBtn = r1.get('[data-testid="party-drawer__leave-confirm"]');
    const cancelBtn = r1.get('[data-testid="party-drawer__leave-cancel"]');
    expect(confirmBtn.text()).toBe("確認離隊");
    expect(cancelBtn.text()).toBe("取消");

    // Step 2a: Clicking 取消 resets confirmation without dispatching
    await cancelBtn.trigger("click");
    expect(w.emitted("action")).toBeUndefined();
    expect(r1.find('[data-testid="party-drawer__leave-confirm"]').exists()).toBe(false);
    expect(r1.find('[data-testid="party-drawer__leave-btn"]').exists()).toBe(true);

    // Step 2b: Re-arm and click 確認離隊 dispatches action
    await r1.get('[data-testid="party-drawer__leave-btn"]').trigger("click");
    await r1.get('[data-testid="party-drawer__leave-confirm"]').trigger("click");

    expect(w.emitted("action")).toHaveLength(1);
    expect(w.emitted("action")[0]).toEqual([
      {
        action_id: "explore.party_leave",
        payload: { npc_id: 101 },
      },
    ]);
  });

  it("resets confirmingLeaveId when slots change on commit", async () => {
    const w = mountDrawer();

    const r1 = w.get('[data-testid="party-drawer__row-101"]');
    await r1.get('[data-testid="party-drawer__leave-btn"]').trigger("click");
    expect(r1.find('[data-testid="party-drawer__leave-confirm"]').exists()).toBe(true);

    // Simulate commit removing companion 101
    await w.setProps({
      slots: [PARTY_PANEL_SAMPLE.slots[1]], // only 幽 remains
    });

    expect(w.findAll('[data-testid^="party-drawer__row-"]')).toHaveLength(1);
    const remainingRow = w.get('[data-testid="party-drawer__row-102"]');
    expect(remainingRow.find('[data-testid="party-drawer__leave-confirm"]').exists()).toBe(false);
  });

  it("resets confirmingLeaveId unconditionally when slots change (even when same companion remains)", async () => {
    const w = mountDrawer();

    const r1 = w.get('[data-testid="party-drawer__row-101"]');
    await r1.get('[data-testid="party-drawer__leave-btn"]').trigger("click");
    expect(r1.find('[data-testid="party-drawer__leave-confirm"]').exists()).toBe(true);

    // Commit updating companion 101's HP but retaining companion 101
    await w.setProps({
      slots: [
        {
          ...PARTY_PANEL_SAMPLE.slots[0],
          hp_current: 200,
        },
        PARTY_PANEL_SAMPLE.slots[1],
      ],
    });

    // Confirmation must be reset back to the unconfirmed "請其離隊" button
    const refreshedR1 = w.get('[data-testid="party-drawer__row-101"]');
    expect(refreshedR1.find('[data-testid="party-drawer__leave-confirm"]').exists()).toBe(false);
    expect(refreshedR1.find('[data-testid="party-drawer__leave-btn"]').exists()).toBe(true);
  });

  it("resets confirmingLeaveId and disables leave button when mode transitions to combat after arming", async () => {
    const w = mountDrawer();

    const r1 = w.get('[data-testid="party-drawer__row-101"]');
    await r1.get('[data-testid="party-drawer__leave-btn"]').trigger("click");
    expect(r1.find('[data-testid="party-drawer__leave-confirm"]').exists()).toBe(true);

    // Transition mode to combat
    await w.setProps({ mode: "combat" });

    // Confirmation must be cancelled and button disabled with combat reason
    const refreshedR1 = w.get('[data-testid="party-drawer__row-101"]');
    expect(refreshedR1.find('[data-testid="party-drawer__leave-confirm"]').exists()).toBe(false);
    const leaveBtn = refreshedR1.get('[data-testid="party-drawer__leave-btn"]');
    expect(leaveBtn.attributes("disabled")).toBeDefined();
    expect(leaveBtn.attributes("title")).toBe("戰鬥中無法調整隊伍");
  });

  it("empty slot states the invite rule in stage-name words and dispatches invite when enabled", async () => {
    const w = mountDrawer();

    const emptyRow = w.get('[data-testid="party-drawer__empty-row"]');
    expect(emptyRow.get('[data-testid="party-drawer__invite-rule"]').text()).toContain(
      "邀請需當地自由 NPC，且羈絆達「親睦」階段",
    );
    // Never displays raw threshold numeral 70
    expect(emptyRow.text()).not.toContain("70");

    const inviteBtn = emptyRow.get('[data-testid="party-drawer__invite-btn"]');
    expect(inviteBtn.attributes("disabled")).toBeUndefined();

    await inviteBtn.trigger("click");
    expect(w.emitted("action")).toHaveLength(1);
    expect(w.emitted("action")[0]).toEqual([
      {
        action_id: "explore.party_invite",
        payload: { npc_id: 201, message: "" },
      },
    ]);
  });

  it("disables invite button with reason when exploration context has no invite-capable target", () => {
    const w = mountDrawer({
      interactTargets: [], // no interact targets
    });

    const emptyRow = w.get('[data-testid="party-drawer__empty-row"]');
    const inviteBtn = emptyRow.get('[data-testid="party-drawer__invite-btn"]');
    expect(inviteBtn.attributes("disabled")).toBeDefined();
    expect(inviteBtn.attributes("title")).toBe("邀請需當地自由 NPC，且羈絆達「親睦」階段");
  });

  it("disables invite button with server disabled reason when target is disabled", () => {
    const w = mountDrawer({
      interactTargets: [
        {
          identity: 301,
          display_name: "衛兵",
          affordances: [
            {
              kind: "action",
              action_id: "explore.party_invite",
              label: "邀請",
              enabled: false,
              disabled_reason: { code: "full", message: "你的隊伍已經滿了（最多 4 人）。" },
            },
          ],
        },
      ],
    });

    const emptyRow = w.get('[data-testid="party-drawer__empty-row"]');
    const inviteBtn = emptyRow.get('[data-testid="party-drawer__invite-btn"]');
    expect(inviteBtn.attributes("disabled")).toBeDefined();
    expect(inviteBtn.attributes("title")).toBe("你的隊伍已經滿了（最多 4 人）。");
  });

  it("disables leave and invite actions in combat mode", () => {
    const w = mountDrawer({
      mode: "combat",
    });

    // Leave buttons disabled
    for (const row of w.findAll('[data-testid^="party-drawer__row-"]')) {
      const leaveBtn = row.get('[data-testid="party-drawer__leave-btn"]');
      expect(leaveBtn.attributes("disabled")).toBeDefined();
      expect(leaveBtn.attributes("title")).toBe("戰鬥中無法調整隊伍");
    }

    // Invite button disabled
    const inviteBtn = w.get('[data-testid="party-drawer__invite-btn"]');
    expect(inviteBtn.attributes("disabled")).toBeDefined();
    expect(inviteBtn.attributes("title")).toBe("戰鬥中無法調整隊伍");
  });

  it("renders the three verbatim follow rules from reference draft", () => {
    const w = mountDrawer();
    const rules = w.get('[data-testid="party-drawer__follow-rules"]');

    expect(rules.get(".qh").text()).toBe("跟隨規則");
    const lines = rules.findAll(".o").map((el) => el.text());
    expect(lines).toEqual([
      "玩家越過出口時自動帶走同室同伴，無時鐘成本、靜音。",
      "跟丟時顯示「你跟丟了…。」，同伴保留羈絆。",
      "affinity 低於門檻會自動離隊。",
    ]);
  });

  it("renders no detail control with unbacked read model (詳情 dropped)", () => {
    const w = mountDrawer();
    expect(w.text()).not.toContain("詳情");
  });

  it("hides the empty slot row when party is full (4 / 4)", () => {
    const w = mountDrawer({
      slots: PARTY_PANEL_FULL_SAMPLE.slots,
    });
    expect(w.find('[data-testid="party-drawer__empty-row"]').exists()).toBe(false);
  });

  it("companion row renders possess button and clicking it dispatches explore.possess", async () => {
    const w = mountDrawer({
      affordances: [
        {
          action_id: "explore.possess",
          label: "附身",
          params: { npc_id: 101 },
          enabled: true,
          disabled_reason: null,
        },
      ],
    });
    const r1 = w.get('[data-testid="party-drawer__row-101"]');
    const possessBtn = r1.get('[data-testid="party-drawer__possess-btn"]');
    expect(possessBtn.text()).toBe("附身");
    expect(possessBtn.attributes("disabled")).toBeUndefined();

    await possessBtn.trigger("click");
    expect(w.emitted("action")).toHaveLength(1);
    expect(w.emitted("action")[0][0]).toEqual({
      action_id: "explore.possess",
      payload: { npc_id: 101 },
    });
  });

  it("disabled possess button carries disabled reason and blocks dispatch", async () => {
    const w = mountDrawer({
      affordances: [
        {
          action_id: "explore.possess",
          label: "附身",
          params: { npc_id: 101 },
          enabled: false,
          disabled_reason: { code: "in_combat", message: "戰鬥中無法附身。" },
        },
      ],
    });
    const r1 = w.get('[data-testid="party-drawer__row-101"]');
    const possessBtn = r1.get('[data-testid="party-drawer__possess-btn"]');
    expect(possessBtn.attributes("disabled")).toBeDefined();
    expect(possessBtn.attributes("title")).toBe("戰鬥中無法附身。");

    await possessBtn.trigger("click");
    expect(w.emitted("action")).toBeUndefined();
  });

  it("release banner renders when releaseAffordance is present and clicking it dispatches explore.possess_release", async () => {
    const w = mountDrawer({
      releaseAffordance: {
        action_id: "explore.possess_release",
        label: "歸位",
        params: { npc_id: 101 },
        enabled: true,
      },
    });
    const banner = w.find('[data-testid="party-drawer__release-banner"]');
    expect(banner.exists()).toBe(true);
    expect(banner.text()).toContain("目前正處於附身狀態");

    const releaseBtn = w.get('[data-testid="party-drawer__release-btn"]');
    expect(releaseBtn.text()).toBe("歸位");
    await releaseBtn.trigger("click");
    expect(w.emitted("action")).toHaveLength(1);
    expect(w.emitted("action")[0][0]).toEqual({
      action_id: "explore.possess_release",
      payload: { npc_id: 101 },
    });
  });
});
