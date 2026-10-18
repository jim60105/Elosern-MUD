// webclient-party-window-member-tab: the party window's 成員 tab. Every
// control reads its `party_member` descriptor; 請其離隊 takes two steps and
// Escape (through the window's close guard) or 取消 cancels it; 人物卡 opens
// the NPC persona editor; 附身/解除附身 dispatch their descriptor; the
// commander edits the four persona fields; 空位 shows the committed invite
// affordance; and the tab renders state, never rule prose.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import PartyMemberTab from "../../components/PartyMemberTab.vue";
import {
  PARTY_INTERACT_TARGETS_SAMPLE,
  PARTY_MEMBER_COMPANION_SAMPLE,
  PARTY_MEMBER_ESCORT_SAMPLE,
  PARTY_MEMBER_KNOCKED_OUT_SAMPLE,
  PARTY_MEMBER_PANEL_SAMPLE,
  PARTY_MEMBER_POSSESSED_SAMPLE,
  PARTY_WINDOW_INVITE_DISABLED_TARGETS,
  PARTY_WINDOW_PANEL_SAMPLE,
} from "../../stories/fixtures/party_panels.js";
import { artworkDescriptor, artworkResource, fixtureDigest } from "../../stories/fixtures/art_panels.js";

// One companion's catalog value: the canonical descriptor plus its context.
// A null `url` models a subject with no real candidate at all.
function companionEntry(url, faceRect, identity = "101") {
  return {
    artwork: artworkDescriptor({
      subject_id: `companion:${identity}`,
      generation_subject: `companion:${identity}`,
      generation_state: url ? "done" : "pending",
      attempts: url
        ? [{
            type: "image",
            source_id: `portrait.default:${identity}`,
            rank: 30,
            resource: artworkResource({
              resource_id: url,
              version: fixtureDigest(String(url)),
              url,
              geometry: { image_size: null, face_rect: faceRect, stage: { scale: 1, x: 0, y: 0 }, aspect_ratio: "3:4" },
            }),
          }]
        : [],
      terminal: null,
    }),
    context: { name: `同伴${identity}`, role: "隊友" },
  };
}
const artWith = (entry) => ({ schema_version: 3, available: true, portrait_catalog: { "101": entry } });

const row = (id) => PARTY_WINDOW_PANEL_SAMPLE.slots.find((slot) => slot.identity === id);

// The follow, transfer, combat and legend rule prose the windows no longer
// carry (design §3.4); the help overlay owns it.
const RULE_PROSE = [
  /跟隨規則/,
  /越過出口/,
  /跟丟/,
  /自動離隊/,
  /門檻/,
  /同伴是正式 NPC/,
  /羈絆 7 階/,
  /邀請需當地自由 NPC/,
  /無法指揮同伴/,
  /護送規則/,
  /數值隱藏/,
];

describe("PartyMemberTab (webclient-party-window-member-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountTab(props = {}) {
    wrapper = mount(PartyMemberTab, {
      attachTo: document.body,
      props: { member: row(101), partyMember: PARTY_MEMBER_COMPANION_SAMPLE, ...props },
    });
    return wrapper;
  }

  const btn = (key) => wrapper.get(`[data-testid="action-bar__btn--${key}"]`);
  const reasons = () => wrapper.findAll('[data-testid="action-bar__reason"]').map((node) => node.text());

  describe("a companion", () => {
    it("shows the nameplate gauges, the bond stage with its pips, the membership tag and intimate state", () => {
      mountTab();
      expect(wrapper.get('[data-testid="party-member-tab__name"]').text()).toBe("蕾娜");
      expect(wrapper.get('[data-testid="party-member-tab__gauge--hp"]').text()).toContain("180 / 220");
      expect(wrapper.get('[data-testid="party-member-tab__gauge--sp"]').text()).toContain("24 / 40");
      expect(wrapper.get('[data-testid="party-member-tab__bond"]').text()).toContain("親睦");
      const pips = wrapper.get('[data-testid="party-member-tab__pips"]');
      expect(pips.attributes("aria-label")).toBe("第 3 階，共 7 階");
      expect(pips.findAll("i")).toHaveLength(7);
      expect(pips.findAll("i.is-on")).toHaveLength(3);
      expect(wrapper.get('[data-testid="party-member-tab__membership"]').text()).toBe("一般同伴");
      expect(wrapper.get('[data-testid="party-member-tab__intimate"]').text()).toContain("興奮平靜");
      expect(["leave", "npc-persona", "possess"].map((key) => btn(key).text())).toEqual(["請其離隊…", "人物卡", "附身"]);
    });

    it("dispatches 附身 and 解除附身 from the possession descriptor", async () => {
      mountTab();
      await btn("possess").trigger("click");
      expect(wrapper.emitted("action")).toEqual([[{ action_id: "explore.possess", payload: { npc_id: 101 } }]]);
      await wrapper.setProps({ partyMember: PARTY_MEMBER_POSSESSED_SAMPLE });
      expect(btn("possess").text()).toBe("解除附身");
      await btn("possess").trigger("click");
      expect(wrapper.emitted("action")[1]).toEqual([{ action_id: "explore.possess_release", payload: { npc_id: 101 } }]);
    });

    it("keeps a gated control focusable with its committed reason and sends nothing", async () => {
      mountTab({ member: row(102), partyMember: PARTY_MEMBER_KNOCKED_OUT_SAMPLE });
      expect(wrapper.get('[data-testid="party-member-tab__down"]').text()).toBe("倒地");
      expect(btn("possess").attributes("aria-disabled")).toBe("true");
      expect(reasons()).toContain("對方已失去意識，無法附身。");
      await btn("possess").trigger("click");
      expect(wrapper.emitted("action")).toBeUndefined();
      expect(wrapper.find('[data-testid="party-member-tab__intimate"]').exists()).toBe(false);
    });

    it("opens the NPC persona editor from 人物卡 with the descriptor's npc_id", async () => {
      mountTab();
      await btn("npc-persona").trigger("click");
      expect(wrapper.emitted("open-npc-persona")).toEqual([[101]]);
      expect(wrapper.emitted("action")).toBeUndefined();
    });

    it("takes two steps to leave and sends exactly one explore.party_leave", async () => {
      mountTab();
      await btn("leave").trigger("click");
      expect(wrapper.emitted("action")).toBeUndefined();
      expect(wrapper.get('[data-testid="party-member-tab__leave-warning"]').text()).toBe("蕾娜會離開隊伍。");
      await nextTick();
      expect(document.activeElement).toBe(btn("leave-cancel").element);
      await btn("leave-confirm").trigger("click");
      expect(wrapper.emitted("action")).toEqual([[{ action_id: "explore.party_leave", payload: { npc_id: 101 } }]]);
      expect(wrapper.find('[data-testid="party-member-tab__leave-warning"]').exists()).toBe(false);
    });

    it("cancels the armed leave with 取消 or the window's Escape guard without sending", async () => {
      mountTab();
      await btn("leave").trigger("click");
      await btn("leave-cancel").trigger("click");
      expect(wrapper.find('[data-testid="party-member-tab__leave-warning"]').exists()).toBe(false);
      expect(wrapper.vm.cancelArmed()).toBe(false);
      await btn("leave").trigger("click");
      expect(wrapper.vm.cancelArmed()).toBe(true);
      await nextTick();
      expect(wrapper.find('[data-testid="party-member-tab__leave-warning"]').exists()).toBe(false);
      expect(wrapper.emitted("action")).toBeUndefined();
    });

    it("disarms when another member is selected", async () => {
      mountTab();
      await btn("leave").trigger("click");
      await wrapper.setProps({ member: row(102), partyMember: PARTY_MEMBER_KNOCKED_OUT_SAMPLE });
      expect(wrapper.find('[data-testid="party-member-tab__leave-warning"]').exists()).toBe(false);
      await wrapper.setProps({ member: row(101), partyMember: PARTY_MEMBER_COMPANION_SAMPLE });
      expect(wrapper.find('[data-testid="action-bar__btn--leave-confirm"]').exists()).toBe(false);
    });

    it("shows a temporary escort's commission tag and committed leave reason, and no rule prose", async () => {
      mountTab({ member: row(103), partyMember: PARTY_MEMBER_ESCORT_SAMPLE });
      expect(wrapper.get('[data-testid="party-member-tab__membership"]').text()).toBe("委託：護送商隊 ‧ 護衛");
      expect(reasons()).toEqual(["此同伴受委託護送中（escort_caravan），無法請其離隊。"]);
      await btn("leave").trigger("click");
      expect(wrapper.find('[data-testid="party-member-tab__leave-warning"]').exists()).toBe(false);
      const text = wrapper.text();
      for (const pattern of RULE_PROSE) expect(text).not.toMatch(pattern);
      // The whole visible text is state (the leading 蓋 is the avatar's
      // initial): the snapshot pins it.
      expect(text).toMatchInlineSnapshot(`"蓋蓋文HP120 / 120MP20 / 20SP30 / 30羈絆初識同行身分委託：護送商隊 ‧ 護衛此同伴受委託護送中（escort_caravan），無法請其離隊。 請其離隊… 人物卡 附身"`);
    });

    it("renders no detail for a panel that describes another member", () => {
      mountTab({ member: row(102), partyMember: PARTY_MEMBER_COMPANION_SAMPLE });
      expect(wrapper.find('[data-testid="party-member-tab__bond"]').exists()).toBe(false);
      expect(wrapper.findAll('[data-testid^="action-bar__btn--"]')).toHaveLength(0);
    });

    it("states the party_member panel's reason when it is unavailable", () => {
      mountTab({ partyMember: { schema_version: 1, available: false, reason: { code: "party_member_unavailable", message: "成員資訊目前無法顯示。" } } });
      expect(wrapper.get('[data-testid="party-member-tab__unavailable"]').text()).toBe("成員資訊目前無法顯示。");
    });
  });

  // The nameplate is the party window's companion avatar: the shared avatar
  // renderer zoom-crops the catalog face rectangle (webclient-art-panel's
  // small-avatar crop, carried over from the retired party drawer rows).
  describe("the nameplate portrait", () => {
    it("zoom-crops the companion avatar by the catalog face rect", () => {
      mountTab({ artPanel: artWith(companionEntry("/media/portraits/reina.png", { x: 0.6, y: 0.1, w: 0.2, h: 0.2 })) });
      const img = wrapper.get('[data-testid="party-member-tab__plate"] img.avatar-artwork__figure');
      expect(img.element.style.width).toBe("500%");
      expect(img.element.style.height).toBe("500%");
      expect(img.element.style.left).toBe("-300%");
      expect(img.element.style.top).toBe("-50%");
    });

    it("falls back to the centered cover crop with no face rect", () => {
      mountTab({ artPanel: artWith(companionEntry("/media/portraits/reina.png", null)) });
      const img = wrapper.get('[data-testid="party-member-tab__plate"] img.avatar-artwork__figure');
      expect(img.element.style.objectPosition).toBe("50% 50%");
      expect(img.element.style.width).toBe("");
    });

    it("keeps the initial and no failure marker for a companion with no real candidate", () => {
      mountTab({ artPanel: artWith(companionEntry(null, null)) });
      const plate = wrapper.get('[data-testid="party-member-tab__plate"]');
      expect(plate.find("img").exists()).toBe(false);
      expect(plate.get(".avatar-artwork__initial").exists()).toBe(true);
      expect(plate.find('[data-testid="artwork-failure"]').exists()).toBe(false);
    });
  });

  describe("the commander", () => {
    const commanderRow = row(42);

    it("shows the four persona fields with placeholders and no structural key", () => {
      mountTab({
        member: commanderRow,
        partyMember: {
          ...PARTY_MEMBER_PANEL_SAMPLE,
          commander: {
            ...PARTY_MEMBER_PANEL_SAMPLE.commander,
            persona: { background: "只有背景", personality: null, life_story: null, habit: null },
          },
        },
      });
      expect(wrapper.get('[data-testid="party-member-tab__persona-value--background"]').text()).toBe("只有背景");
      for (const key of ["personality", "life_story", "habit"]) {
        expect(wrapper.get(`[data-testid="party-member-tab__persona-empty--${key}"]`).text()).toBe("未設定");
      }
      const text = wrapper.text();
      for (const key of ["identity", "appearance", "social_connection"]) expect(text).not.toContain(key);
      expect(wrapper.get('[data-testid="party-member-tab__intimate"]').text()).toContain("今日2");
      expect(btn("persona-edit").text()).toBe("編輯人物設定");
      expect(wrapper.find('[data-testid="party-member-tab__bond"]').exists()).toBe(false);
    });

    it("edits one section and submits exactly one persona-edit intent, then reflects the refresh", async () => {
      mountTab({ member: commanderRow, partyMember: PARTY_MEMBER_PANEL_SAMPLE });
      expect(wrapper.find('[data-testid="party-member-tab__persona-edit--habit"]').exists()).toBe(false);
      await btn("persona-edit").trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-edit--habit"]').trigger("click");
      const input = wrapper.get('[data-testid="party-member-tab__persona-input--habit"]');
      expect(input.element.value).toBe(PARTY_MEMBER_PANEL_SAMPLE.commander.persona.habit);
      await input.setValue("  每晚寫日記。  ");
      await wrapper.get('[data-testid="party-member-tab__persona-submit--habit"]').trigger("click");
      expect(wrapper.emitted("persona-edit")).toEqual([[{ field: "habit", text: "每晚寫日記。" }]]);
      await wrapper.setProps({
        partyMember: {
          ...PARTY_MEMBER_PANEL_SAMPLE,
          commander: {
            ...PARTY_MEMBER_PANEL_SAMPLE.commander,
            persona: { ...PARTY_MEMBER_PANEL_SAMPLE.commander.persona, habit: "每晚寫日記。" },
          },
        },
      });
      expect(wrapper.get('[data-testid="party-member-tab__persona-value--habit"]').text()).toBe("每晚寫日記。");
    });

    it("submits null for a blank draft and closes on cancel", async () => {
      mountTab({ member: commanderRow, partyMember: PARTY_MEMBER_PANEL_SAMPLE });
      await btn("persona-edit").trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-edit--background"]').trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-input--background"]').setValue("   ");
      await wrapper.get('[data-testid="party-member-tab__persona-submit--background"]').trigger("click");
      expect(wrapper.emitted("persona-edit")).toEqual([[{ field: "background", text: null }]]);
      await wrapper.get('[data-testid="party-member-tab__persona-edit--personality"]').trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-cancel--personality"]').trigger("click");
      expect(wrapper.emitted("persona-edit")).toHaveLength(1);
      await btn("persona-done").trigger("click");
      expect(wrapper.find('[data-testid="party-member-tab__persona-edit--habit"]').exists()).toBe(false);
    });

    it("bounds the draft at 600 code points, counting astral characters as one", async () => {
      mountTab({ member: commanderRow, partyMember: PARTY_MEMBER_PANEL_SAMPLE });
      await btn("persona-edit").trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-edit--personality"]').trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-input--personality"]').setValue("𠀀".repeat(601));
      await wrapper.get('[data-testid="party-member-tab__persona-submit--personality"]').trigger("click");
      expect(Array.from(wrapper.emitted("persona-edit")[0][0].text)).toHaveLength(600);
    });

    const withPersona = (patch) => ({
      ...PARTY_MEMBER_PANEL_SAMPLE,
      commander: { ...PARTY_MEMBER_PANEL_SAMPLE.commander, persona: { ...PARTY_MEMBER_PANEL_SAMPLE.commander.persona, ...patch } },
    });

    it("re-seeds an open editor when a refresh changes the edited field", async () => {
      mountTab({ member: commanderRow, partyMember: PARTY_MEMBER_PANEL_SAMPLE });
      await btn("persona-edit").trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-edit--habit"]').trigger("click");
      const input = wrapper.get('[data-testid="party-member-tab__persona-input--habit"]');
      await input.setValue("我還沒提交的草稿");
      // A completion publication refreshes habit from elsewhere (e.g. Telnet):
      // the newer committed value wins over the stale draft.
      await wrapper.setProps({ partyMember: withPersona({ habit: "遠端改過的習慣" }) });
      expect(input.element.value).toBe("遠端改過的習慣");
    });

    it("keeps an untouched open editor stable when other fields refresh", async () => {
      mountTab({ member: commanderRow, partyMember: PARTY_MEMBER_PANEL_SAMPLE });
      await btn("persona-edit").trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-edit--habit"]').trigger("click");
      const input = wrapper.get('[data-testid="party-member-tab__persona-input--habit"]');
      await input.setValue("我的草稿");
      await wrapper.setProps({ partyMember: withPersona({ personality: "遠端改的個性" }) });
      expect(input.element.value).toBe("我的草稿");
    });

    it("keeps 編輯人物設定 gated by its descriptor and leaves edit mode when it closes", async () => {
      const gated = {
        ...PARTY_MEMBER_PANEL_SAMPLE,
        commander: {
          ...PARTY_MEMBER_PANEL_SAMPLE.commander,
          actions: [{ action_id: "character.persona.update", params: {}, enabled: false, reason: "你目前無法這麼做。" }],
        },
      };
      mountTab({ member: commanderRow, partyMember: PARTY_MEMBER_PANEL_SAMPLE });
      await btn("persona-edit").trigger("click");
      await wrapper.get('[data-testid="party-member-tab__persona-edit--habit"]').trigger("click");
      await wrapper.setProps({ partyMember: gated });
      expect(wrapper.find('[data-testid="party-member-tab__persona-input--habit"]').exists()).toBe(false);
      expect(btn("persona-edit").attributes("aria-disabled")).toBe("true");
      expect(reasons()).toEqual(["你目前無法這麼做。"]);
      await btn("persona-edit").trigger("click");
      expect(wrapper.find('[data-testid="party-member-tab__persona-edit--habit"]').exists()).toBe(false);
    });
  });

  describe("空位", () => {
    it("names the gated innkeeper with the committed reason and sends no invite", async () => {
      mountTab({ member: null, interactTargets: PARTY_WINDOW_INVITE_DISABLED_TARGETS });
      expect(wrapper.get('[data-testid="party-member-tab"]').attributes("data-member")).toBe("empty");
      expect(wrapper.get('[data-testid="party-member-tab__invite-target"]').text()).toContain("旅店老闆娘");
      expect(reasons()).toEqual(["羈絆不足，對方不願同行。"]);
      expect(btn("invite").attributes("aria-disabled")).toBe("true");
      await btn("invite").trigger("click");
      expect(wrapper.emitted("action")).toBeUndefined();
    });

    it("invites the first enabled target", async () => {
      mountTab({ member: null, interactTargets: PARTY_INTERACT_TARGETS_SAMPLE });
      await btn("invite").trigger("click");
      expect(wrapper.emitted("action")).toEqual([[{ action_id: "explore.party_invite", payload: { npc_id: 201, message: "" } }]]);
    });

    it("states the client's no-target line when no invite affordance is committed", () => {
      mountTab({ member: null, interactTargets: [] });
      expect(wrapper.find('[data-testid="party-member-tab__invite-target"]').exists()).toBe(false);
      expect(reasons()).toEqual(["這裡沒有可邀請的對象。"]);
      for (const pattern of RULE_PROSE) expect(wrapper.text()).not.toMatch(pattern);
    });
  });
});
