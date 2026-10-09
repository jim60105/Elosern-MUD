import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import QuestDrawer from "../../components/QuestDrawer.vue";
import { resetQuestDrawerMemory } from "../../components/quest-drawer-memory.js";
import {
  QUEST_LOG_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_SAMPLE,
  QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_GUILD_BOARD_SAMPLE,
  SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE,
  SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

const enabled = (action_id, label) => ({ action_id, label, enabled: true, disabled_reason: null, quantity: null });
const servicesWithQuests = (quests) => ({
  ...SERVICES_PANEL_SAMPLE,
  guild: { ...SERVICES_PANEL_SAMPLE.guild, quests },
});
const bookWith = (rows) => ({ schema_version: 2, available: true, rows });
const extraInProgress = {
  ...QUEST_LOG_PANEL_SAMPLE.rows[1],
  quest_id: "q_3000",
  display_name: "第三份委託",
};

describe("QuestDrawer (quest-drawer-book-tab)", () => {
  let wrapper;

  beforeEach(() => resetQuestDrawerMemory());

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountDrawer(props = {}) {
    wrapper = mount(QuestDrawer, {
      attachTo: document.body,
      props: {
        questLog: QUEST_LOG_PANEL_SAMPLE,
        services: SERVICES_PANEL_SAMPLE,
        memoryScope: "1|1",
        ...props,
      },
    });
    return wrapper;
  }

  // Close and reopen: the drawer unmounts and mounts again in one session.
  function reopen(props = {}) {
    wrapper.unmount();
    return mountDrawer(props);
  }

  const topTab = (key) => wrapper.get(`[data-testid="quest-drawer__top-tabs"] [data-tab-key="${key}"]`);
  const stateTab = (key) => wrapper.get(`[data-testid="quest-drawer__state-rail"] [data-tab-key="${key}"]`);
  const rowIds = () =>
    wrapper.findAll('[data-testid^="quest-drawer__row--"]').map((row) => row.attributes("data-quest-id"));
  const selectedId = () => wrapper.find('[role="option"][aria-selected="true"]')?.attributes("data-quest-id");
  const detailId = () => wrapper.find('[data-testid="quest-drawer__detail"]').attributes("data-quest-id");
  const find = (id) => wrapper.find(`[data-testid="quest-drawer__${id}"]`);

  async function press(key) {
    document.activeElement.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
    await nextTick();
    await nextTick();
  }

  describe("two-level icon tabs", () => {
    it("lands on the quest book, in progress, keeping the drawer root test id", () => {
      mountDrawer();
      expect(wrapper.get('[data-testid="quest-drawer"]').attributes("data-tab")).toBe("book");
      expect(topTab("book").attributes("aria-selected")).toBe("true");
      expect(stateTab("in_progress").attributes("aria-selected")).toBe("true");
      expect(wrapper.get('[data-testid="quest-drawer__top-tabs"]').attributes("aria-orientation")).toBe("horizontal");
      expect(wrapper.get('[data-testid="quest-drawer__state-rail"]').attributes("aria-orientation")).toBe("vertical");
      expect(topTab("book").attributes("aria-label")).toBe("任務簿");
      expect(topTab("counter").attributes("data-tip")).toBe("公會櫃檯");
    });

    it("remembers the counter tab across a close and reopen", async () => {
      mountDrawer();
      await topTab("counter").trigger("click");
      expect(find("counter").exists()).toBe(true);
      reopen();
      expect(topTab("counter").attributes("aria-selected")).toBe("true");
      expect(find("counter").exists()).toBe(true);
    });

    it("falls back to the book when the remembered counter is gone", async () => {
      mountDrawer();
      await topTab("counter").trigger("click");
      reopen({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
      expect(topTab("book").attributes("aria-selected")).toBe("true");
      expect(topTab("counter").attributes("aria-disabled")).toBe("true");
      expect(find("book").exists()).toBe(true);
    });

    it("explains a counter disabled by an unavailable services panel", async () => {
      mountDrawer({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
      const counter = topTab("counter");
      expect(counter.attributes("aria-disabled")).toBe("true");
      expect(counter.attributes("disabled")).toBeUndefined();
      expect(counter.attributes("data-tip")).toBe("公會櫃檯 · 服務選單目前無法顯示");
      const reason = wrapper.get('[data-testid="quest-drawer__counter-unavailable"]');
      expect(reason.text()).toBe("服務選單目前無法顯示");
      expect(reason.attributes("data-reason-code")).toBe("services_unavailable");
      expect(counter.attributes("aria-describedby")).toBe(reason.attributes("id"));
      await counter.trigger("click");
      expect(topTab("book").attributes("aria-selected")).toBe("true");
      expect(find("counter").exists()).toBe(false);
    });

    it("names the missing clerk when no guild section resolves", () => {
      mountDrawer({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
      expect(wrapper.get('[data-testid="quest-drawer__counter-absent"]').text()).toBe("需在公會職員面前才能辦理");
      expect(find("counter-unavailable").exists()).toBe(false);
    });

    it("moves focus by arrow and selects on Enter only", async () => {
      mountDrawer();
      topTab("book").element.focus();
      await press("ArrowRight");
      expect(document.activeElement).toBe(topTab("counter").element);
      expect(topTab("book").attributes("aria-selected")).toBe("true");
      await press("Enter");
      expect(topTab("counter").attributes("aria-selected")).toBe("true");
      expect(find("counter").exists()).toBe(true);
    });
  });

  describe("one quest state at a time", () => {
    it("lists only in-progress rows first, and switching replaces the list", async () => {
      mountDrawer();
      expect(rowIds()).toEqual(["q_1042", "q_2077"]);
      await stateTab("failed").trigger("click");
      expect(rowIds()).toEqual(["q_0099"]);
      expect(wrapper.get(".quest-list__kicker").text()).toBe("失敗");
      // No expand or collapse controls anywhere in the book.
      expect(wrapper.find("[aria-expanded]").exists()).toBe(false);
    });

    it("reports the stored counts in the state tabs' accessible names", () => {
      const rows = [
        ...QUEST_LOG_PANEL_SAMPLE.rows,
        extraInProgress,
        { ...QUEST_LOG_PANEL_SAMPLE.rows[2], quest_id: "q_0302" },
      ];
      mountDrawer({ questLog: bookWith(rows) });
      expect(stateTab("in_progress").attributes("aria-label")).toBe("進行中（3）");
      expect(stateTab("completed").attributes("aria-label")).toBe("已完成（2）");
      expect(stateTab("failed").attributes("aria-label")).toBe("失敗（1）");
    });

    it("emphasizes the completed count only for an enabled turn-in", async () => {
      const hotServices = servicesWithQuests([
        { quest_id: "q_0301", abandon: null, turnin: enabled("guild.quest_turnin", "交派任務") },
      ]);
      mountDrawer({ services: hotServices });
      const hot = () => stateTab("completed").get('[data-testid="icon-tabs__count"]').classes();
      expect(hot()).toContain("icon-tabs__count--hot");
      await wrapper.setProps({ services: SERVICES_PANEL_SAMPLE });
      expect(hot()).not.toContain("icon-tabs__count--hot");
    });

    it("shows the empty guidance and an empty detail for an empty state", () => {
      mountDrawer({ questLog: QUEST_LOG_PANEL_EMPTY_SAMPLE });
      expect(wrapper.get('[data-testid="quest-drawer__empty"]').classes()).toContain("empty-state");
      expect(find("detail-empty").exists()).toBe(true);
      expect(find("detail").exists()).toBe(false);
    });
  });

  describe("master and detail", () => {
    it("selects the first row by default and shows its detail", () => {
      mountDrawer();
      expect(selectedId()).toBe("q_1042");
      expect(detailId()).toBe("q_1042");
    });

    it("remembers the selection per state tab", async () => {
      mountDrawer();
      await wrapper.get('[data-testid="quest-drawer__row--q_2077"]').trigger("click");
      await stateTab("completed").trigger("click");
      expect(detailId()).toBe("q_0301");
      await stateTab("in_progress").trigger("click");
      expect(selectedId()).toBe("q_2077");
      expect(detailId()).toBe("q_2077");
    });

    it("falls back to the first remaining row, then to an empty detail", async () => {
      mountDrawer({ questLog: bookWith([...QUEST_LOG_PANEL_SAMPLE.rows, extraInProgress]) });
      await wrapper.get('[data-testid="quest-drawer__row--q_2077"]').trigger("click");
      const without2077 = QUEST_LOG_PANEL_SAMPLE.rows.filter((row) => row.quest_id !== "q_2077");
      await wrapper.setProps({ questLog: bookWith([...without2077, extraInProgress]) });
      expect(detailId()).toBe("q_1042");
      await wrapper.setProps({ questLog: bookWith(without2077.filter((row) => row.state !== "in_progress")) });
      expect(find("detail").exists()).toBe(false);
      expect(find("detail-empty").exists()).toBe(true);
    });

    it("selects the next row from the keyboard", async () => {
      mountDrawer();
      wrapper.get('[data-testid="quest-drawer__row--q_1042"]').element.focus();
      await press("ArrowDown");
      await press("Enter");
      expect(selectedId()).toBe("q_2077");
      expect(detailId()).toBe("q_2077");
    });

    it("forgets every remembered key when the memory scope changes", async () => {
      mountDrawer();
      await topTab("counter").trigger("click");
      reopen({ memoryScope: "2|1" });
      expect(topTab("book").attributes("aria-selected")).toBe("true");
      await stateTab("failed").trigger("click");
      await wrapper.setProps({ memoryScope: "2|2" });
      expect(stateTab("in_progress").attributes("aria-selected")).toBe("true");
    });
  });

  describe("the action bar", () => {
    it("forwards tracking with the exact payload away from any clerk", async () => {
      mountDrawer({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
      await wrapper.get('[data-testid="quest-drawer__row--q_2077"]').trigger("click");
      await wrapper.get('[data-testid="quest-drawer__track"]').trigger("click");
      expect(wrapper.emitted("action")).toEqual([
        [{ action_id: "guild.quest_track", payload: { quest_id: "q_2077", tracked: true } }],
      ]);
    });

    it("renders no counter action on any row away from a clerk", async () => {
      mountDrawer({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
      for (const state of ["in_progress", "completed", "failed"]) {
        await stateTab(state).trigger("click");
        expect(find("abandon").exists()).toBe(false);
        expect(find("turnin").exists()).toBe(false);
      }
    });

    it("mirrors the matched counter abandon and forwards it after confirmation", async () => {
      mountDrawer();
      await wrapper.get('[data-testid="quest-drawer__abandon"]').trigger("click");
      await wrapper.get('[data-testid="quest-drawer__abandon-confirm-yes"]').trigger("click");
      expect(wrapper.emitted("action")).toEqual([
        [{ action_id: "guild.quest_abandon", payload: { quest_id: "q_1042" } }],
      ]);
    });

    it("disarms an armed abandon when the row leaves the list", async () => {
      mountDrawer();
      await wrapper.get('[data-testid="quest-drawer__abandon"]').trigger("click");
      expect(find("abandon-confirm").exists()).toBe(true);
      const rest = QUEST_LOG_PANEL_SAMPLE.rows.filter((row) => row.quest_id !== "q_1042");
      await wrapper.setProps({ questLog: bookWith(rest) });
      expect(find("abandon-confirm").exists()).toBe(false);
      expect(wrapper.emitted("action")).toBeUndefined();
    });

    it("offers only tracking on a private commission in front of a clerk", async () => {
      mountDrawer();
      await wrapper.get('[data-testid="quest-drawer__row--q_2077"]').trigger("click");
      expect(find("track").exists()).toBe(true);
      expect(find("abandon").exists()).toBe(false);
    });

    it("turns in a completed quest from the detail", async () => {
      mountDrawer({
        services: servicesWithQuests([{ quest_id: "q_0301", abandon: null, turnin: enabled("guild.quest_turnin", "交派任務") }]),
      });
      await stateTab("completed").trigger("click");
      await wrapper.get('[data-testid="quest-drawer__turnin"]').trigger("click");
      expect(wrapper.emitted("action")).toEqual([
        [{ action_id: "guild.quest_turnin", payload: { quest_id: "q_0301" } }],
      ]);
    });

    it("states a claimed reward away from the counter", async () => {
      const rows = QUEST_LOG_PANEL_SAMPLE.rows.map((row) =>
        row.quest_id === "q_0301" ? { ...row, reward_claimed: true } : row,
      );
      mountDrawer({ questLog: bookWith(rows), services: SERVICES_PANEL_MINIMAL_SAMPLE });
      await stateTab("completed").trigger("click");
      expect(wrapper.get('[data-testid="quest-drawer__action-reason"]').text()).toBe("報酬已領取");
    });

    it("points a pending counter reward back to the counter", async () => {
      mountDrawer({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
      await stateTab("completed").trigger("click");
      expect(wrapper.get('[data-testid="quest-drawer__action-reason"]').text()).toBe("回到公會櫃檯即可交付並領取報酬。");
    });
  });

  describe("honest degradation", () => {
    it("shows the fixed absent line before the first commit", () => {
      mountDrawer({ questLog: null });
      expect(wrapper.get('[data-testid="quest-drawer__absent"]').text()).toBe("尚未取得任務簿資料");
      expect(rowIds()).toEqual([]);
      expect(find("detail").exists()).toBe(false);
    });

    it("shows an unavailable book's reason with its code", () => {
      mountDrawer({ questLog: QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE });
      const reason = wrapper.get('[data-testid="quest-drawer__unavailable"]');
      expect(reason.text()).toBe("任務簿目前無法顯示");
      expect(reason.attributes("data-reason-code")).toBe("quest_log_unavailable");
      expect(rowIds()).toEqual([]);
    });
  });

  describe("the guild counter tab", () => {
    const BOARD = SERVICES_PANEL_GUILD_BOARD_SAMPLE;
    const LADDER = BOARD.guild.rank_ladder;
    const offersOf = (grade) => BOARD.guild.board.filter((row) => row.rank === grade);
    const gradeTab = (key) => wrapper.get(`[data-testid="quest-drawer__grade-rail"] [data-tab-key="${key}"]`);
    const withBoard = (board, extra = {}) => ({ ...BOARD, guild: { ...BOARD.guild, board, ...extra } });

    async function openCounter(props = {}) {
      mountDrawer({ services: BOARD, ...props });
      await topTab("counter").trigger("click");
    }

    it("renders one fixed grade tab per ladder key, in ladder order", async () => {
      await openCounter();
      const keys = () => wrapper.findAll('[data-testid="quest-drawer__grade-rail"] [role="tab"]').map((tab) => tab.attributes("data-tab-key"));
      expect(keys()).toEqual(LADDER);
      expect(wrapper.findAll('[data-testid="quest-drawer__grade-rail"] .grade-gem').map((gem) => gem.attributes("data-grade"))).toEqual(LADDER);
      await wrapper.setProps({ services: withBoard(offersOf("F")) });
      expect(keys()).toEqual(LADDER);
    });

    it("lists only the selected grade's offers", async () => {
      await openCounter();
      await gradeTab("F").trigger("click");
      expect(rowIds()).toEqual(offersOf("F").map((row) => row.definition_key));
      expect(gradeTab("F").attributes("aria-label")).toBe(`F 級（${offersOf("F").length}）`);
      expect(find("list-count").text()).toBe(String(offersOf("F").length));
    });

    it("defaults to the highest eligible grade that has offers", async () => {
      await openCounter({ services: withBoard(offersOf("F")) });
      expect(gradeTab("F").attributes("aria-selected")).toBe("true");
    });

    it("defaults to the holder's own grade when no eligible grade has offers", async () => {
      await openCounter({ services: withBoard([]) });
      expect(gradeTab("E").attributes("aria-selected")).toBe("true");
      expect(find("empty").text()).toContain("目前沒有 E 級委託。");
    });

    it("keeps the shown grade when a commit empties it", async () => {
      await openCounter({ services: withBoard(offersOf("F")) });
      expect(gradeTab("F").attributes("aria-selected")).toBe("true");
      await wrapper.setProps({ services: withBoard([...offersOf("E")]) });
      expect(gradeTab("F").attributes("aria-selected")).toBe("true");
      expect(rowIds()).toEqual([]);
    });

    it("keeps an explicitly chosen empty grade across a reopen", async () => {
      await openCounter({ services: withBoard(offersOf("E")) });
      await gradeTab("F").trigger("click");
      reopen({ services: withBoard(offersOf("E")) });
      expect(gradeTab("F").attributes("aria-selected")).toBe("true");
    });

    it("drops the remembered grade when the holder is promoted", async () => {
      await openCounter();
      await gradeTab("F").trigger("click");
      const promoted = { ...BOARD, player: { ...BOARD.player, guild_rank: "D" } };
      await wrapper.setProps({ services: promoted });
      expect(gradeTab("E").attributes("aria-selected")).toBe("true");
      expect(gradeTab("D").classes()).not.toContain("is-locked");
    });

    it("locks grades above the holder's rank with the promotion line and no rows", async () => {
      await openCounter();
      expect(gradeTab("D").classes()).toContain("is-locked");
      expect(gradeTab("D").attributes("aria-disabled")).toBeUndefined();
      await gradeTab("D").trigger("click");
      expect(gradeTab("D").attributes("aria-selected")).toBe("true");
      expect(find("empty").text()).toContain("D 級委託要等你的公會等級提升後才會開放。");
      expect(rowIds()).toEqual([]);
    });

    it("never implies hidden offers behind a locked grade", async () => {
      await openCounter();
      await gradeTab("D").trigger("click");
      expect(find("detail").exists()).toBe(false);
      expect(find("accept").exists()).toBe(false);
      expect(gradeTab("D").find('[data-testid="icon-tabs__count"]').exists()).toBe(false);
      expect(gradeTab("D").attributes("aria-label")).toBe("D 級");
      expect(gradeTab("D").classes()).not.toContain("is-dim");
    });

    it("dims an eligible empty grade and says so", async () => {
      await openCounter({ services: withBoard(offersOf("F")) });
      expect(gradeTab("E").classes()).toContain("is-dim");
      await gradeTab("E").trigger("click");
      expect(find("empty").text()).toContain("目前沒有 E 級委託。");
    });

    it("marks the holder's own grade and names it in the tooltip", async () => {
      await openCounter();
      expect(gradeTab("E").classes()).toContain("is-mark");
      expect(gradeTab("E").attributes("data-tip")).toBe("E 級 · 你的等級");
      expect(gradeTab("F").classes()).not.toContain("is-mark");
    });

    it("shows the rank card above the offer list, in every grade state", async () => {
      await openCounter();
      const list = find("list");
      const card = list.get('[data-testid="guild-rank-card"]');
      expect(card.element.compareDocumentPosition(list.get('[role="listbox"]').element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      expect(card.find('[data-testid="guild-counter__merit-meter"]').exists()).toBe(true);
      await gradeTab("D").trigger("click");
      expect(find("list").find('[data-testid="guild-rank-card"]').exists()).toBe(true);
    });

    it("submits the examination request unchanged", async () => {
      await openCounter();
      await wrapper.get('[data-testid="guild-counter__exam"]').trigger("click");
      expect(wrapper.emitted("action")).toEqual([
        [{ action_id: "guild.exam_request", payload: { target_rank: BOARD.guild.rank.next_rank } }],
      ]);
    });

    it("renders no rank card when the guild section carries none", async () => {
      await openCounter({ services: withBoard(BOARD.guild.board, { rank: null }) });
      expect(wrapper.find('[data-testid="guild-rank-card"]').exists()).toBe(false);
      expect(rowIds().length).toBeGreaterThan(0);
    });

    it("shows what accepting an offer commits to", async () => {
      await openCounter();
      await gradeTab("F").trigger("click");
      const offer = offersOf("F").find((row) => row.deadline_line && row.reward.items.length > 0);
      await wrapper.get(`[data-testid="quest-drawer__row--${offer.definition_key}"]`).trigger("click");
      expect(detailId()).toBe(offer.definition_key);
      const detail = find("detail").text();
      expect(detail).toContain(offer.objective_summary);
      expect(find("deadline").text()).toContain(offer.deadline_line);
      expect(find("issuer").text()).toContain(BOARD.guild.branch_label);
      expect(find("condition").text()).toContain(`公會等級 ${offer.rank} 級以上`);
      const item = offer.reward.items[0];
      expect(find("reward").text()).toContain(item.display_name);
      expect(find("reward").text()).toContain(`× ${item.quantity}`);
      expect(find("settlement").text()).toBe("回公會櫃檯領取");
      expect(find("progress").exists()).toBe(false);
    });

    it("shows the offer's note and flavor", async () => {
      await openCounter();
      const offer = offersOf("E").find((row) => row.flavor && row.accept.enabled);
      await wrapper.get(`[data-testid="quest-drawer__row--${offer.definition_key}"]`).trigger("click");
      expect(find("detail").text()).toContain(offer.objective_note);
      expect(find("issuer").text()).toContain(offer.flavor);
    });

    it("dispatches the accept descriptor exactly once", async () => {
      await openCounter();
      const offer = offersOf("E").find((row) => row.accept.enabled);
      await wrapper.get(`[data-testid="quest-drawer__row--${offer.definition_key}"]`).trigger("click");
      await find("accept").trigger("click");
      expect(wrapper.emitted("action")).toEqual([
        [{ action_id: offer.accept.action_id, payload: { definition_key: offer.definition_key } }],
      ]);
    });

    it("shows a disabled accept's reason and no enabled accept control", async () => {
      await openCounter();
      const offer = offersOf("E").find((row) => !row.accept.enabled);
      await wrapper.get(`[data-testid="quest-drawer__row--${offer.definition_key}"]`).trigger("click");
      expect(find("action-reason").text()).toBe(offer.accept.disabled_reason.message);
      expect(find("accept").attributes("aria-disabled")).toBe("true");
      expect(find("accept").attributes("aria-describedby")).toBe(find("action-reason").attributes("id"));
      await find("accept").trigger("click");
      expect(wrapper.emitted("action")).toBeUndefined();
    });

    it("lists no held quest in the counter tab", async () => {
      await openCounter({ services: SERVICES_PANEL_SAMPLE });
      const held = new Set(QUEST_LOG_PANEL_SAMPLE.rows.map((row) => row.quest_id));
      expect(rowIds().length).toBeGreaterThan(0);
      expect(rowIds().some((id) => held.has(id))).toBe(false);
      expect(find("grade-rail").exists()).toBe(true);
      expect(wrapper.find('[data-testid="guild-rank-card"]').exists()).toBe(true);
      expect(find("registration").exists()).toBe(false);
      expect(find("state-rail").exists()).toBe(false);
    });

    it("shows an accepted offer in the book once the commit lands", async () => {
      const offer = offersOf("F")[0];
      const accepted = {
        ...QUEST_LOG_PANEL_SAMPLE.rows[0],
        quest_id: `${offer.definition_key}:1`,
        display_name: offer.display_name,
      };
      await openCounter();
      await wrapper.setProps({ questLog: bookWith([...QUEST_LOG_PANEL_SAMPLE.rows, accepted]) });
      expect(rowIds()).not.toContain(accepted.quest_id);
      await topTab("book").trigger("click");
      expect(rowIds().filter((id) => id === accepted.quest_id)).toHaveLength(1);
    });

    it("replaces the board with the registration card for an unregistered holder", async () => {
      await openCounter({ services: SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE });
      const card = find("registration");
      expect(card.text()).toContain("未加入公會");
      expect(find("register").text()).toBe(SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE.guild.registration.register.label);
      expect(find("grade-rail").exists()).toBe(false);
      expect(rowIds()).toEqual([]);
      expect(wrapper.find('[data-testid="guild-rank-card"]').exists()).toBe(false);
    });

    it("dispatches registration once and shows the board only after the commit", async () => {
      await openCounter({ services: SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE });
      find("register").element.focus();
      await find("register").trigger("click");
      expect(wrapper.emitted("action")).toEqual([[{ action_id: "guild.register", payload: {} }]]);
      expect(find("grade-rail").exists()).toBe(false);
      await wrapper.setProps({ services: BOARD });
      await nextTick();
      expect(find("grade-rail").exists()).toBe(true);
      // The register button left the DOM; focus returns to the grade rail.
      expect(wrapper.get('[data-testid="quest-drawer__grade-rail"]').element.contains(document.activeElement)).toBe(true);
    });

    it("never pulls focus into the drawer from outside on a commit", async () => {
      const outside = document.createElement("button");
      document.body.appendChild(outside);
      await openCounter({ services: SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE });
      outside.focus();
      await wrapper.setProps({ services: BOARD });
      await nextTick();
      expect(document.activeElement).toBe(outside);
    });

    it("states a disabled registration's reason", async () => {
      const guild = SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE.guild;
      const reason = { code: "x", message: "暫停受理" };
      const services = {
        ...SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE,
        guild: { ...guild, registration: { registered: false, register: { ...guild.registration.register, enabled: false, disabled_reason: reason } } },
      };
      await openCounter({ services });
      expect(find("register").exists()).toBe(false);
      expect(find("register-reason").text()).toBe(reason.message);
    });

    it("renders the top rank's board with nothing locked above it", async () => {
      await openCounter({ services: { ...SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE, player: { ...SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE.player, guild_rank: "S" } } });
      expect(wrapper.findAll('[data-testid="quest-drawer__grade-rail"] .is-locked')).toHaveLength(0);
      expect(gradeTab("S").classes()).toContain("is-mark");
      expect(wrapper.find('[data-testid="guild-counter__rank-top"]').exists()).toBe(true);
    });

    it("keeps the book working while services are unavailable", () => {
      mountDrawer({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
      expect(rowIds()).toEqual(["q_1042", "q_2077"]);
      expect(topTab("counter").attributes("aria-disabled")).toBe("true");
    });
  });
});
