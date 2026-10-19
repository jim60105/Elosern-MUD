// webclient-party-skill-tab: the party window's 技能 tab (design §6.4). The
// SkillBook browsing carries over (segment, search, the keyboard category
// tree in payload order); each active row adds the member's proficiency
// meter and level and a 新 tag; the detail shows target, cost and field
// capability, the ladder and the lineage position only while the committed
// `selected_skill` names the row on screen; the action bar's 施放 and
// 排入修煉 act for the viewed member and are disabled with their committed
// reasons in combat; opening the tab sends one `party.view_member` with tab
// `skills` when the member is unread or the selection differs.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PartySkillTab from "../../components/PartySkillTab.vue";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab, resetPartyWindowMemory } from "../../components/party-window-memory.js";
import {
  CAST_COMBAT_ONLY_REASON,
  CAST_IN_COMBAT_REASON,
  PRACTICE_IN_COMBAT_REASON,
  growthOf,
  ladderOf,
} from "../../components/party-skill-model.js";
import { SKILLS_SLICE_SAMPLE } from "../../stories/fixtures.js";
import { PARTY_WINDOW_PANEL_SAMPLE } from "../../stories/fixtures/party_panels.js";
import {
  CHARACTER_SKILL_COMPANION_SAMPLE,
  CHARACTER_SKILL_LADDER_SAMPLE,
  CHARACTER_SKILL_NO_MASTERY_SAMPLE,
} from "../../stories/fixtures/skill_tab_panels.js";

// Payload values are read from the fixtures, never restated here.
const PANEL = CHARACTER_SKILL_COMPANION_SAMPLE;
const MEMBER = PARTY_WINDOW_PANEL_SAMPLE.slots.find((row) => row.identity === PANEL.member_id);
const allRows = (panel, side = "actives") => panel[side].flatMap((c) => c.groups.flatMap((g) => g.skills));
const ROW = (key) => allRows(PANEL).find((row) => row.key === key);
const HEAL = ROW(PANEL.selected_skill.key);
const FRESH = allRows(PANEL).find((row) => row.fresh);
const CAPPED = allRows(PANEL).find((row) => row.capped);
const COMBAT_ONLY = allRows(PANEL).find((row) => row.usable_out_of_combat === false);
const UNREGISTERED = allRows(PANEL).find((row) => !("cost" in row));
const LADDER_KEY = CHARACTER_SKILL_LADDER_SAMPLE.selected_skill.key;
const LADDER = CHARACTER_SKILL_LADDER_SAMPLE.selected_skill.freeform_ladder;
const FIRST_CATEGORY = PANEL.actives[0];

describe("PartySkillTab (webclient-party-skill-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountTab(props = {}) {
    wrapper = mount(PartySkillTab, {
      attachTo: document.body,
      props: { member: MEMBER, character: PANEL, requestSkill: vi.fn(() => 1), ...props },
    });
    return wrapper;
  }

  const row = (w, key) => w.get(`[data-testid="party-skill-tab__row"][data-key="${key}"]`);
  const categories = (w) => w.findAll('[data-testid="party-skill-tab__category"]');
  const castButton = (w) => w.find('[data-testid="action-bar__btn--cast"]');
  const practiceButton = (w) => w.find('[data-testid="action-bar__btn--practice"]');

  async function select(w, key) {
    for (const head of w.findAll('[data-testid="party-skill-tab__category-head"]')) {
      if (head.attributes("aria-expanded") === "false") await head.trigger("click");
    }
    await row(w, key).trigger("click");
    await nextTick();
  }

  function setQuery(w, value) {
    const input = w.get('[data-testid="party-skill-tab__search"]');
    input.element.value = value;
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // ------------------------------------------------------------ browsing

  it("keeps the payload's category, group and skill order in a keyboard tree with segment counts", () => {
    const w = mountTab();
    expect(w.get('[data-testid="party-skill-tab__tree"]').attributes("role")).toBe("tree");
    expect(categories(w).map((c) => c.attributes("data-category"))).toEqual(PANEL.actives.map((c) => c.category));
    const counts = (side) => allRows(PANEL, side).length;
    expect(w.get('[data-testid="party-skill-tab__segment--active"]').text()).toBe(`主動 ${counts("actives")}`);
    expect(w.get('[data-testid="party-skill-tab__segment--passive"]').text()).toBe(`被動 ${counts("passives")}`);
    // The committed selection is selected on open; its category is open.
    expect(row(w, HEAL.key).attributes("aria-selected")).toBe("true");
    expect(row(w, HEAL.key).attributes("tabindex")).toBe("0");
    expect(w.get('[data-testid="party-skill-tab__title"]').text()).toBe(HEAL.label);
  });

  it("keeps the payload's order within a category, the category count as a digit, and a chevron state", async () => {
    const w = mountTab({ character: { ...PANEL, selected_skill: null } });
    const first = categories(w)[0];
    expect(first.attributes("data-category")).toBe(FIRST_CATEGORY.category);
    // Every category opens on open, like the prototype's flat list.
    expect(categories(w).map((c) => c.attributes("data-open"))).toEqual(PANEL.actives.map(() => "true"));
    await categories(w)[1].get('[data-testid="party-skill-tab__category-head"]').trigger("click");
    expect(categories(w)[1].attributes("data-open")).toBe("false");
    expect(categories(w)[1].get('[data-testid="party-skill-tab__category-head"]').attributes("aria-expanded")).toBe("false");
    const labels = FIRST_CATEGORY.groups[0].skills.map((s) => s.label);
    expect(first.text().indexOf(labels[0])).toBeLessThan(first.text().indexOf(labels[1]));
    expect(first.get('[data-testid="party-skill-tab__category-count"]').text()).toBe(String(FIRST_CATEGORY.groups[0].skills.length));
    expect(first.get('[data-testid="party-skill-tab__category-head"]').attributes("aria-expanded")).toBe("true");
  });

  it("moves selection with the arrow keys and Enter goes to the actions without casting", async () => {
    const w = mountTab({ character: { ...PANEL, selected_skill: null } });
    const tree = w.get('[data-testid="party-skill-tab__tree"]');
    const [a, b] = FIRST_CATEGORY.groups[0].skills;
    expect(row(w, a.key).attributes("aria-selected")).toBe("true");
    await tree.trigger("keydown", { key: "ArrowDown" });
    await nextTick();
    expect(row(w, b.key).attributes("aria-selected")).toBe("true");
    // ← from a skill lands on its category header; ← again collapses it.
    await tree.trigger("keydown", { key: "ArrowLeft" });
    await nextTick();
    await tree.trigger("keydown", { key: "ArrowLeft" });
    await nextTick();
    expect(categories(w)[0].attributes("data-open")).toBe("false");
    await tree.trigger("keydown", { key: "ArrowRight" });
    await nextTick();
    expect(categories(w)[0].attributes("data-open")).toBe("true");
    await select(w, HEAL.key);
    await tree.trigger("keydown", { key: "Enter" });
    await nextTick();
    await nextTick();
    expect(document.activeElement?.getAttribute("data-testid")).toBe("action-bar__btn--cast");
    expect(w.emitted("use")).toBeUndefined();
    // ← from the action returns to the row.
    await w.get('[data-testid="action-bar"]').trigger("keydown", { key: "ArrowLeft" });
    await nextTick();
    expect(document.activeElement?.getAttribute("data-key")).toBe(HEAL.key);
  });

  it("filters through the search and offers a way out of an empty result", async () => {
    const w = mountTab();
    setQuery(w, HEAL.label);
    await nextTick();
    expect(w.findAll('[data-testid="party-skill-tab__row"]').map((r) => r.attributes("data-key"))).toEqual([HEAL.key]);
    setQuery(w, "不存在");
    await nextTick();
    const empty = w.get('[data-testid="party-skill-tab__empty"]');
    expect(empty.text()).toContain("沒有符合「不存在」的技能");
    await empty.get("button").trigger("click");
    expect(w.get('[data-testid="party-skill-tab__search"]').element.value).toBe("");
  });

  it("switches to the passive segment: read-only rows with a 被動 badge, no actions", async () => {
    const w = mountTab();
    await w.get('[data-testid="party-skill-tab__segment--passive"]').trigger("click");
    expect(categories(w).map((c) => c.attributes("data-category"))).toEqual(PANEL.passives.map((c) => c.category));
    expect(w.findAll('[data-testid="party-skill-tab__passive-badge"]').length).toBe(allRows(PANEL, "passives").length);
    expect(w.find('[data-testid="party-skill-tab__meter"]').exists()).toBe(false);
    expect(w.find('[data-testid="action-bar"]').exists()).toBe(false);
    expect(w.get('[data-testid="party-skill-tab__passive-note"]').text()).toContain("不需施放");
    // No conventions legend on either segment.
    expect(w.text()).not.toMatch(/圖例|說明：/);
  });

  // ------------------------------------------------------------ growth

  it("adds the member's proficiency meter, level, 新 and booked tags to each active row", async () => {
    const w = mountTab();
    await select(w, FRESH.key);
    expect(row(w, FRESH.key).find('[data-testid="party-skill-tab__new"]').text()).toBe("新");
    expect(row(w, HEAL.key).find('[data-testid="party-skill-tab__new"]').exists()).toBe(false);
    expect(row(w, HEAL.key).find('[data-testid="party-skill-tab__booked"]').text()).toBe("修煉中");
    const heal = growthOf(HEAL);
    expect(row(w, HEAL.key).get('[data-testid="party-skill-tab__level"]').text()).toBe(`Lv ${HEAL.level}`);
    expect(row(w, HEAL.key).get('[data-testid="party-skill-tab__meter"] i').attributes("style")).toContain(`width: ${heal.percent}%`);
    await select(w, CAPPED.key);
    expect(row(w, CAPPED.key).get('[data-testid="party-skill-tab__level"]').text()).toBe("見頂");
    expect(w.get('[data-testid="party-skill-tab__proficiency"]').text()).toContain("見頂");
  });

  it("formats the stored XP pair without evaluating a rule", () => {
    expect(growthOf({ level: 2, xp_into_level: 4.5, xp_to_next_level: 35.5, capped: false })).toMatchObject({
      percent: 11,
      xpText: "4.5 / 40",
      levelText: "Lv 2",
    });
    expect(growthOf({ level: 9, xp_into_level: 0, xp_to_next_level: 0, capped: true })).toMatchObject({ percent: 100, levelText: "見頂" });
  });

  // ------------------------------------------------------------ detail

  it("shows target, cost and the field capability in words, never a combat badge", async () => {
    const w = mountTab();
    expect(w.get('[data-testid="party-skill-tab__fact--cost"]').text()).toBe(`MP ${HEAL.cost.mp}`);
    expect(w.get('[data-testid="party-skill-tab__fact--field"]').text()).toBe("可於戰鬥外使用");
    await select(w, COMBAT_ONLY.key);
    expect(w.get('[data-testid="party-skill-tab__fact--field"]').text()).toBe("僅能在戰鬥中使用");
    expect(w.text()).not.toMatch(/\bcombat\b/);
  });

  it("renders detail cells only when the payload provides them", async () => {
    const w = mountTab();
    await select(w, UNREGISTERED.key);
    expect(w.find('[data-testid="party-skill-tab__facts"]').exists()).toBe(false);
    // An undescribed row offers no 施放 (nothing is invented) but keeps 排入修煉.
    expect(castButton(w).exists()).toBe(false);
    expect(practiceButton(w).exists()).toBe(true);
  });

  it("shows the lineage position from selected_skill and links into the 系譜 tab", async () => {
    const w = mountTab();
    const lineage = PANEL.selected_skill.lineage;
    expect(w.findAll('[data-testid="party-skill-tab__prerequisite"]').map((n) => n.text())).toEqual(
      lineage.prerequisites.map((e) => `${e.label}Lv ${e.level}`),
    );
    expect(w.get('[data-testid="party-skill-tab__current"]').text()).toBe(HEAL.label);
    expect(w.findAll('[data-testid="party-skill-tab__next"]').map((n) => n.text())).toEqual(
      lineage.next.map((e) => `${e.label}Lv ${e.min_level}`),
    );
    await w.get('[data-testid="party-skill-tab__lineage-link"]').trigger("click");
    expect(w.emitted("lineage")).toHaveLength(1);
    // Another row has no committed section: no lineage, no ladder.
    await select(w, FRESH.key);
    expect(w.find('[data-testid="party-skill-tab__lineage"]').exists()).toBe(false);
  });

  it("renders the master's ladder verbatim: MP for unlocked rungs, 需 Lv for locked ones", async () => {
    const w = mountTab({ character: CHARACTER_SKILL_LADDER_SAMPLE });
    expect(w.get('[data-testid="party-skill-tab__title"]').text()).toBe(ROW(LADDER_KEY).label);
    const rungs = w.findAll('[data-testid="party-skill-tab__rung"]');
    expect(rungs.map((r) => r.text())).toEqual(
      LADDER.map((e) => `威力×${e.label}${e.mp_cost != null ? `MP ${e.mp_cost}` : `需 Lv ${e.unlock_level}`}`),
    );
    expect(rungs.map((r) => r.attributes("data-locked"))).toEqual(LADDER.map((e) => String(e.unlock_level != null)));
    expect(ladderOf(CHARACTER_SKILL_LADDER_SAMPLE.selected_skill).map((r) => r.valueText)).toEqual(
      LADDER.map((e) => (e.mp_cost != null ? `MP ${e.mp_cost}` : `需 Lv ${e.unlock_level}`)),
    );
    expect(w.get('[data-testid="party-skill-tab__fact--cost"]').text()).toContain("威力 ×1");
  });

  it("shows no ladder without the mastery or for a row the selection does not name", async () => {
    const w = mountTab({ character: CHARACTER_SKILL_NO_MASTERY_SAMPLE });
    expect(w.get('[data-testid="party-skill-tab__title"]').text()).toBe(ROW(LADDER_KEY).label);
    expect(w.find('[data-testid="party-skill-tab__scales"]').exists()).toBe(false);
    expect(w.find('[data-testid="party-skill-tab__lineage"]').exists()).toBe(true);
    await w.setProps({ character: CHARACTER_SKILL_LADDER_SAMPLE });
    await select(w, HEAL.key);
    expect(w.find('[data-testid="party-skill-tab__scales"]').exists()).toBe(false);
  });

  it("renders the payload only for the member it describes", () => {
    const other = PARTY_WINDOW_PANEL_SAMPLE.slots.find((r) => r.identity !== PANEL.member_id);
    const request = vi.fn(() => 1);
    const w = mountTab({ member: other, requestSkill: request });
    expect(w.find('[data-testid="party-skill-tab__tree"]').exists()).toBe(false);
    expect(w.find('[data-testid="action-bar"]').exists()).toBe(false);
    expect(request).not.toHaveBeenCalled();
  });

  it("states the unavailable panel's committed reason and invents nothing", () => {
    const w = mountTab({ character: { schema_version: 9, available: false, reason: { code: "character_missing", message: "角色資料目前無法顯示" } } });
    expect(w.get('[data-testid="party-window__tab-unavailable"]').text()).toBe("角色資料目前無法顯示");
    expect(w.find('[data-testid="party-skill-tab__segment"]').exists()).toBe(false);
  });

  // ------------------------------------------------------------ selection sync

  it("opening the tab on an unread member sends one selection with tab skills", async () => {
    const request = vi.fn(() => 7);
    mountTab({ member: { ...MEMBER, unread: true }, requestSkill: request });
    await nextTick();
    expect(request).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledWith({ member_id: PANEL.member_id, skill_key: HEAL.key });
  });

  it("opening the tab sends nothing when the member is read and the selection is committed", async () => {
    const request = vi.fn(() => 7);
    mountTab({ requestSkill: request });
    await nextTick();
    expect(request).not.toHaveBeenCalled();
  });

  it("asks once per selected registered row and never for an unregistered one", async () => {
    const request = vi.fn(() => 7);
    const w = mountTab({ requestSkill: request });
    await select(w, FRESH.key);
    expect(request).toHaveBeenLastCalledWith({ member_id: PANEL.member_id, skill_key: FRESH.key });
    const calls = request.mock.calls.length;
    await select(w, UNREGISTERED.key);
    expect(request).toHaveBeenCalledTimes(calls);
    // Search filtering alone sends nothing.
    setQuery(w, FRESH.label);
    await nextTick();
    expect(request).toHaveBeenCalledTimes(calls);
  });

  it("holds a request while the dispatch gate is closed and retries a refused one when it opens", async () => {
    const request = vi.fn(() => null);
    const w = mountTab({ member: { ...MEMBER, unread: true }, requestSkill: request, useLocked: true });
    await nextTick();
    expect(request).not.toHaveBeenCalled();
    await w.setProps({ useLocked: false });
    await nextTick();
    expect(request).toHaveBeenCalledTimes(1);
    // Refused (null): still owed; the next gate opening asks again.
    request.mockImplementation(() => 9);
    await w.setProps({ useLocked: true });
    await w.setProps({ useLocked: false });
    await nextTick();
    expect(request).toHaveBeenCalledTimes(2);
    await w.setProps({ useLocked: true });
    await w.setProps({ useLocked: false });
    await nextTick();
    expect(request).toHaveBeenCalledTimes(2);
  });

  // ------------------------------------------------------------ actions

  it("emits one use intent for a field skill and nothing while locked", async () => {
    const w = mountTab();
    await castButton(w).trigger("click");
    expect(w.emitted("use")).toEqual([[HEAL.key]]);
    await w.setProps({ useLocked: true });
    await castButton(w).trigger("click");
    expect(w.emitted("use")).toHaveLength(1);
  });

  it("books the viewed member's practice in one intent and shows the server's line", async () => {
    const w = mountTab({ practiceFeedback: "蕾娜將在下次休息時修煉。" });
    await practiceButton(w).trigger("click");
    expect(w.emitted("practice")).toEqual([[{ actor_id: PANEL.member_id, skill: HEAL.key }]]);
    expect(w.get('[data-testid="party-skill-tab__practice-feedback"]').text()).toBe("蕾娜將在下次休息時修煉。");
    expect(w.find("form").exists()).toBe(false);
    await w.setProps({ practiceDisabled: true });
    await practiceButton(w).trigger("click");
    expect(w.emitted("practice")).toHaveLength(1);
  });

  it("disables both actions in combat with their committed reasons and emits nothing", async () => {
    const w = mountTab({ combat: true, mode: "combat" });
    expect(castButton(w).attributes("aria-disabled")).toBe("true");
    expect(practiceButton(w).attributes("aria-disabled")).toBe("true");
    const reasons = w.findAll('[data-testid="action-bar__reason"]').map((r) => r.text());
    expect(reasons).toEqual([PRACTICE_IN_COMBAT_REASON, CAST_IN_COMBAT_REASON]);
    expect(castButton(w).attributes("aria-describedby")).toBeTruthy();
    await castButton(w).trigger("click");
    await practiceButton(w).trigger("click");
    expect(w.emitted("use")).toBeUndefined();
    expect(w.emitted("practice")).toBeUndefined();
  });

  it("never offers an enabled field confirmation for a combat-only skill", async () => {
    const w = mountTab();
    await select(w, COMBAT_ONLY.key);
    expect(castButton(w).attributes("aria-disabled")).toBe("true");
    expect(w.text()).toContain(CAST_COMBAT_ONLY_REASON);
    await w.setProps({ mode: "dialogue" });
    expect(w.text()).toContain("對話中無法施放。");
  });

  it("shows the pending state and a refused preview's message only for that caster", async () => {
    const w = mountTab({ usePending: { actorId: PANEL.member_id, skillKey: HEAL.key } });
    expect(castButton(w).text()).toBe("準備中…");
    expect(castButton(w).attributes("aria-busy")).toBe("true");
    await w.setProps({ usePending: null, useNotice: { actorId: PANEL.member_id, skillKey: HEAL.key, message: "你的資源不足。" } });
    const alert = w.get('[data-testid="party-skill-tab__notice"]');
    expect(alert.attributes("role")).toBe("alert");
    expect(alert.text()).toBe("無法施放：你的資源不足。");
    await w.setProps({ useNotice: { actorId: PANEL.member_id + 1000, skillKey: HEAL.key, message: "你的資源不足。" } });
    expect(w.find('[data-testid="party-skill-tab__notice"]').exists()).toBe(false);
  });

  it("returns focus to the caster's skill's 施放 when reopened from the dock", async () => {
    const w = mountTab({ returnTarget: { actorId: PANEL.member_id, skillKey: COMBAT_ONLY.key, seq: 1 } });
    await nextTick();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(row(w, COMBAT_ONLY.key).attributes("aria-selected")).toBe("true");
    // Its 施放 is disabled, so focus lands on its row.
    expect(document.activeElement?.getAttribute("data-key")).toBe(COMBAT_ONLY.key);
    await w.setProps({ returnTarget: { actorId: PANEL.member_id, skillKey: HEAL.key, seq: 2 } });
    await nextTick();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.activeElement?.getAttribute("data-testid")).toBe("action-bar__btn--cast");
    // Another member's return target changes nothing.
    await w.setProps({ returnTarget: { actorId: PANEL.member_id + 1000, skillKey: COMBAT_ONLY.key, seq: 3 } });
    await nextTick();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(row(w, HEAL.key).attributes("aria-selected")).toBe("true");
  });
});

describe("PartyWindow 技能 tab wiring", () => {
  let wrapper;
  beforeEach(() => {
    resetPartyWindowMemory();
    rememberPartyWindowTab("test|skills", "skills");
  });
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders the tab, re-emits its intents, and the lineage link selects 系譜", async () => {
    wrapper = mount(PartyWindow, {
      attachTo: document.body,
      props: { party: PARTY_WINDOW_PANEL_SAMPLE, character: PANEL, memoryScope: "test|skills", requestSkill: () => 1 },
    });
    await nextTick();
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("skills");
    await wrapper.get('[data-testid="action-bar__btn--cast"]').trigger("click");
    expect(wrapper.emitted("use-skill")).toEqual([[HEAL.key]]);
    await wrapper.get('[data-testid="action-bar__btn--practice"]').trigger("click");
    expect(wrapper.emitted("practice")).toEqual([[{ actor_id: PANEL.member_id, skill: HEAL.key }]]);
    await wrapper.get('[data-testid="party-skill-tab__lineage-link"]').trigger("click");
    await nextTick();
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("lineage");
  });

  it("a rail selection on 技能 names the open tab", async () => {
    wrapper = mount(PartyWindow, {
      attachTo: document.body,
      props: { party: PARTY_WINDOW_PANEL_SAMPLE, character: PANEL, memoryScope: "test|skills" },
    });
    await nextTick();
    const other = PARTY_WINDOW_PANEL_SAMPLE.slots[0];
    await wrapper.get(`[data-testid="member-rail__entry--${other.identity}"]`).trigger("click");
    expect(wrapper.emitted("view-member")).toEqual([[{ memberId: other.identity, tab: "skills" }]]);
  });

  it("the SkillBook-era fixture still validates as a tab payload", () => {
    // The shared skill slice keeps working for the commander's tab.
    wrapper = mount(PartySkillTab, {
      attachTo: document.body,
      props: {
        member: { identity: SKILLS_SLICE_SAMPLE.member_id, display_name: "x", unread: false },
        character: { ...SKILLS_SLICE_SAMPLE, available: true },
      },
    });
    expect(wrapper.findAll('[data-testid="party-skill-tab__row"]').length).toBeGreaterThan(0);
  });
});
