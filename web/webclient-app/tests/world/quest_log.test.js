import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import QuestLog from "../../components/QuestLog.vue";
import {
  QUEST_LOG_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_SAMPLE,
  QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

describe("QuestLog (quest-drawer-split merge rules)", () => {
  let wrapper;

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
      wrapper = undefined;
    }
  });

  function mountBook(props = {}) {
    wrapper = mount(QuestLog, {
      props: {
        questLog: QUEST_LOG_PANEL_SAMPLE,
        services: SERVICES_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  // A services variant whose counter side turns in q_0301 (completed,
  // unclaimed): the canonical completed-row turn-in descriptor.
  function servicesWithTurnin(questId) {
    const services = structuredClone(SERVICES_PANEL_SAMPLE);
    services.guild.quests = [
      {
        quest_id: questId,
        definition_key: "quest_mill_grain",
        display_name: "磨坊糧運",
        state: "completed",
        stage_index: 3,
        stage_progress: 10,
        objective_summary: "將十袋糧食運往磨坊",
        deadline_line: null,
        detail: "糧食已送達磨坊，等著回去回報。",
        abandon: { action_id: "guild.quest_abandon", label: "放棄任務", enabled: false, disabled_reason: { code: "quest_not_active", message: "任務已完成或失敗" }, quantity: null },
        turnin: { action_id: "guild.quest_turnin", label: "交派任務", enabled: true, disabled_reason: null, quantity: null },
        tracked: false,
      },
    ];
    return services;
  }

  it("groups rows by state in panel order and renders the book fields from the panel", () => {
    const w = mountBook();
    // Groups render in the bounded state order; panel order within a group.
    const groupTitles = w.findAll(".quest-log__section-title").map((n) => n.text());
    expect(groupTitles).toEqual(["進行中", "已完成", "失敗"]);
    const inProgress = w.get('section[aria-label="進行中"]');
    const ids = inProgress.findAll('[data-testid^="quest-log__row--"]').map((n) => n.attributes("data-testid"));
    expect(ids).toEqual(["quest-log__row--q_1042", "quest-log__row--q_2077"]);
    const row = w.get('[data-testid="quest-log__row--q_1042"]');
    expect(row.get('[data-testid="quest-log__quest-state"]').text()).toBe("進行中");
    expect(row.get('[data-testid="quest-log__quest-stage"]').text()).toContain("3");
    expect(row.get('[data-testid="quest-log__quest-deadline"]').text()).toBe("剩餘 2 日");
    expect(row.get('[data-testid="quest-log__quest-detail"]').text()).toBe(
      "老周把三袋糧食交給你，要求天亮前送到磨坊。",
    );
    expect(row.text()).toContain("將十袋糧食運往磨坊（3／10）");
    expect(row.text()).toContain("獎勵：400 銅＋公會功績 25");
  });

  it("discloses the issuer and the settlement form on every row", () => {
    const w = mountBook();
    const guildRow = w.get('[data-testid="quest-log__row--q_1042"]');
    expect(guildRow.get('[data-testid="quest-log__issuer"]').text()).toContain("南門公會");
    expect(guildRow.get('[data-testid="quest-log__settlement"]').text()).toContain("櫃台");
    const npcRow = w.get('[data-testid="quest-log__row--q_2077"]');
    expect(npcRow.get('[data-testid="quest-log__issuer"]').text()).toContain("守塔人");
    expect(npcRow.get('[data-testid="quest-log__settlement"]').text()).toContain("完成即結算");
  });

  it("renders nothing in the reward line's place when the panel carries null", () => {
    const questLog = structuredClone(QUEST_LOG_PANEL_SAMPLE);
    // The unresolvable-issuance form: settlement and reward_line are null
    // together (the strict reader's coherence rule).
    questLog.rows[1] = {
      ...questLog.rows[1],
      settlement: null,
      reward_line: null,
    };
    const w = mountBook({ questLog });
    const npcRow = w.get('[data-testid="quest-log__row--q_2077"]');
    expect(npcRow.find('[data-testid="quest-log__settlement"]').exists()).toBe(false);
    expect(npcRow.find('[data-testid="quest-log__reward"]').exists()).toBe(false);
  });

  it("renders the empty book and the unavailable and absent panel forms honestly", () => {
    const empty = mountBook({ questLog: QUEST_LOG_PANEL_EMPTY_SAMPLE });
    expect(empty.get('[data-testid="quest-log__empty"]').exists()).toBe(true);
    expect(empty.findAll('[data-testid^="quest-log__row--"]')).toHaveLength(0);
    empty.unmount();

    const unavailable = mountBook({ questLog: QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE });
    expect(unavailable.get('[data-testid="quest-log__unavailable"]').text()).toContain(
      "任務簿目前無法顯示",
    );
    expect(unavailable.findAll('[data-testid^="quest-log__row--"]')).toHaveLength(0);
    unavailable.unmount();

    const absent = mountBook({ questLog: null });
    expect(absent.get('[data-testid="quest-log__absent"]').exists()).toBe(true);
    expect(absent.findAll('[data-testid^="quest-log__row--"]')).toHaveLength(0);
  });

  it("renders a tracking control on every row with no guild section available (task 1.3)", () => {
    const w = mountBook({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    // Away from any clerk: tracking still renders — host-independent by contract.
    const trackedRow = w.get('[data-testid="quest-log__row--q_1042"]');
    expect(trackedRow.get('[data-testid="quest-log__untrack"]').exists()).toBe(true);
    expect(trackedRow.find('[data-testid="quest-log__abandon"]').exists()).toBe(false);
    expect(trackedRow.find('[data-testid="quest-log__turnin"]').exists()).toBe(false);
    // No counter-side match renders no counter actions on any row.
    for (const questId of ["q_2077", "q_0301", "q_0099"]) {
      const row = w.get(`[data-testid="quest-log__row--${questId}"]`);
      expect(row.find('[data-testid="quest-log__abandon"]').exists(), questId).toBe(false);
      expect(row.find('[data-testid="quest-log__turnin"]').exists(), questId).toBe(false);
      expect(row.find('[data-testid="quest-log__track"]').exists(), questId).toBe(true);
    }
  });

  it("dispatches the row's own track descriptor exactly once per activation", async () => {
    const w = mountBook({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    await w.get('[data-testid="quest-log__row--q_2077"]').get('[data-testid="quest-log__track"]').trigger("click");
    expect(w.emitted("quest_track")).toEqual([
      [{ action_id: "guild.quest_track", payload: { quest_id: "q_2077", tracked: true } }],
    ]);
    // The tracked row dispatches untracking through the same descriptor.
    await w.get('[data-testid="quest-log__row--q_1042"]').get('[data-testid="quest-log__untrack"]').trigger("click");
    expect(w.emitted("quest_track")[1]).toEqual([
      { action_id: "guild.quest_track", payload: { quest_id: "q_1042", tracked: false } },
    ]);
  });

  it("renders non-in-progress tracking disabled with the stable reason and dispatches nothing", async () => {
    const w = mountBook({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    const completedRow = w.get('[data-testid="quest-log__row--q_0301"]');
    const track = completedRow.get('[data-testid="quest-log__track"]');
    expect(track.attributes("disabled")).toBeDefined();
    expect(completedRow.get('[data-testid="quest-log__track-reason"]').text()).toContain(
      "非進行中任務無法追蹤",
    );
    await track.trigger("click");
    expect(w.emitted("quest_track")).toBeUndefined();
  });

  it("gains the counter's abandon and turn-in only on a quest_id match (task 1.4)", () => {
    const w = mountBook();
    // q_1042 matches the services sample's guild.quests row: abandon enabled,
    // turn-in disabled with the counter's own reason mirrored verbatim.
    const matched = w.get('[data-testid="quest-log__row--q_1042"]');
    expect(matched.get('[data-testid="quest-log__abandon"]').text()).toBe("放棄任務");
    expect(matched.find('[data-testid="quest-log__turnin"]').exists()).toBe(false);
    expect(matched.get('[data-testid="quest-log__turnin-reason"]').text()).toContain(
      "任務目標尚未完成",
    );
    // The private commission matches nothing: tracking only, even with a clerk
    // present (the private-commission rule).
    const privateRow = w.get('[data-testid="quest-log__row--q_2077"]');
    expect(privateRow.find('[data-testid="quest-log__abandon"]').exists()).toBe(false);
    expect(privateRow.find('[data-testid="quest-log__turnin"]').exists()).toBe(false);
  });

  it("renders a completed unclaimed row's enabled turn-in and dispatches its exact payload", async () => {
    const w = mountBook({ services: servicesWithTurnin("q_0301") });
    const row = w.get('[data-testid="quest-log__row--q_0301"]');
    const turnin = row.get('[data-testid="quest-log__turnin"]');
    expect(turnin.text()).toBe("交派任務");
    await turnin.trigger("click");
    expect(w.emitted("quest_turnin")).toEqual([
      [{ action_id: "guild.quest_turnin", payload: { quest_id: "q_0301" } }],
    ]);
  });

  it("never enables a counter-side descriptor the counter disabled", () => {
    const services = structuredClone(SERVICES_PANEL_SAMPLE);
    // The counter disabled the abandon descriptor: the book mirrors the
    // reason instead of rendering an enabled control.
    services.guild.quests[0].abandon = {
      action_id: "guild.quest_abandon",
      label: "放棄任務",
      enabled: false,
      disabled_reason: { code: "quest_abandon_locked", message: "目前無法放棄任務" },
      quantity: null,
    };
    const w = mountBook({ services });
    const row = w.get('[data-testid="quest-log__row--q_1042"]');
    expect(row.find('[data-testid="quest-log__abandon"]').exists()).toBe(false);
    expect(row.get('[data-testid="quest-log__abandon-reason"]').text()).toContain("目前無法放棄任務");
  });

  it("keeps the two-step abandon confirmation before any dispatch", async () => {
    const w = mountBook();
    await w.get('[data-testid="quest-log__row--q_1042"]').get('[data-testid="quest-log__abandon"]').trigger("click");
    const confirmBar = w.get('[data-testid="quest-log__abandon-confirm"]');
    expect(confirmBar.exists()).toBe(true);
    expect(w.emitted("quest_abandon")).toBeUndefined();
    await confirmBar.get('[data-testid="quest-log__abandon-confirm-yes"]').trigger("click");
    expect(w.emitted("quest_abandon")).toEqual([
      [{ action_id: "guild.quest_abandon", payload: { quest_id: "q_1042" } }],
    ]);
    expect(w.find('[data-testid="quest-log__abandon-confirm"]').exists()).toBe(false);
  });

  it("cancelling the abandon confirmation emits nothing", async () => {
    const w = mountBook();
    await w.get('[data-testid="quest-log__row--q_1042"]').get('[data-testid="quest-log__abandon"]').trigger("click");
    await w.get('[data-testid="quest-log__abandon-confirm-no"]').trigger("click");
    expect(w.emitted("quest_abandon")).toBeUndefined();
    expect(w.find('[data-testid="quest-log__abandon-confirm"]').exists()).toBe(false);
  });
});
