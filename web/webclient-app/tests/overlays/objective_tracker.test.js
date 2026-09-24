import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ObjectiveTracker from "../../components/ObjectiveTracker.vue";
import {
  OBJECTIVES_PANEL_SAMPLE,
  OBJECTIVES_PANEL_EMPTY_SAMPLE,
} from "../../stories/fixtures.js";

describe("ObjectiveTracker (webclient-align-09-objective-tracker-ui)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountTracker(props = {}) {
    wrapper = mount(ObjectiveTracker, {
      props: {
        rows: OBJECTIVES_PANEL_SAMPLE.rows,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the 目標 label and a +N count for further rows", () => {
    const w = mountTracker();
    expect(w.get(".obj__label").text()).toBe("目標");
    expect(w.get('[data-testid="objective-tracker__more"]').text()).toBe("+2");
    expect(w.find('[data-testid="objective-tracker__count"]').exists()).toBe(false);

    const single = mountTracker({ rows: [OBJECTIVES_PANEL_SAMPLE.rows[0]] });
    expect(single.find('[data-testid="objective-tracker__more"]').exists()).toBe(false);
  });

  it("renders only the first row", () => {
    const w = mountTracker();
    expect(w.get('[data-testid="objective-tracker__text--q_1042"]').text()).toBe("抵達霧骨渡口");
    expect(w.find('[data-testid="objective-tracker__box--q_1042"]').exists()).toBe(true);
    for (const id of ["q_1043", "q_1044"]) {
      expect(w.find(`[data-testid="objective-tracker__text--${id}"]`).exists()).toBe(false);
      expect(w.find(`[data-testid="objective-tracker__box--${id}"]`).exists()).toBe(false);
    }
    expect(w.findAll('[data-testid^="objective-tracker__row--"]')).toHaveLength(0);
    expect(w.text()).not.toContain("與灰婆婆議價過河");
  });

  it("keeps a long objective line's full text as its text and tooltip", () => {
    const line = "在第三個滿月之前，把灰婆婆託付的封蠟信件交給北岸燈塔的守望人";
    const w = mountTracker({
      rows: [{ ...OBJECTIVES_PANEL_SAMPLE.rows[0], quest_id: "q_long", objective_line: line }],
    });
    const text = w.get('[data-testid="objective-tracker__text--q_long"]');
    expect(text.text()).toBe(line);
    expect(text.attributes("title")).toBe(line);
    expect(text.classes()).toContain("txt");
  });

  it("renders a completion checkmark when stage_progress >= objective_quantity and empty box otherwise", () => {
    const rows = [
      {
        quest_id: "q_done",
        display_name: "完成任務",
        objective_line: "完成的事項",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 1,
        objective_quantity: 1,
        reward_copper: null,
        deadline_line: null,
      },
      {
        quest_id: "q_not_done",
        display_name: "進行中任務",
        objective_line: "未完成的事項",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 0,
        objective_quantity: 1,
        reward_copper: null,
        deadline_line: null,
      },
    ];
    const w = mountTracker({ rows });
    const doneBox = w.get('[data-testid="objective-tracker__box--q_done"]');
    expect(doneBox.classes()).toContain("done");
    expect(doneBox.find("svg").exists()).toBe(true);

    const pending = mountTracker({ rows: [rows[1]] });
    const notDoneBox = pending.get('[data-testid="objective-tracker__box--q_not_done"]');
    expect(notDoneBox.classes()).not.toContain("done");
    expect(notDoneBox.find("svg").exists()).toBe(false);
  });

  it("handles the .pr slot matrix: progress numeral vs reward copper vs empty", () => {
    const rows = [
      {
        quest_id: "q_multi",
        display_name: "計數任務",
        objective_line: "收集藥草",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 2,
        objective_quantity: 5,
        reward_copper: 100, // quantity > 1 takes precedence: displays 2/5
        deadline_line: null,
      },
      {
        quest_id: "q_single_reward",
        display_name: "懸賞任務",
        objective_line: "擊敗通緝犯",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 0,
        objective_quantity: 1,
        reward_copper: 80, // quantity == 1 and reward != null: displays +80
        deadline_line: null,
      },
      {
        quest_id: "q_single_no_reward",
        display_name: "劇情任務",
        objective_line: "與導師對話",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 0,
        objective_quantity: 1,
        reward_copper: null, // neither: empty .pr slot
        deadline_line: null,
      },
    ];
    // The slot matrix is evaluated against the first row, so each case
    // mounts its own first row.
    const multi = mountTracker({ rows: [rows[0]] });
    const progressEl = multi.find('[data-testid="objective-tracker__progress--q_multi"]');
    expect(progressEl.exists()).toBe(true);
    expect(progressEl.text()).toBe("2/5");
    expect(multi.find('[data-testid="objective-tracker__reward--q_multi"]').exists()).toBe(false);

    const reward = mountTracker({ rows: [rows[1]] });
    const rewardEl = reward.find('[data-testid="objective-tracker__reward--q_single_reward"]');
    expect(rewardEl.exists()).toBe(true);
    expect(rewardEl.text()).toBe("+80");
    expect(reward.find('[data-testid="objective-tracker__progress--q_single_reward"]').exists()).toBe(false);

    const none = mountTracker({ rows: [rows[2]] });
    expect(none.find('[data-testid="objective-tracker__progress--q_single_no_reward"]').exists()).toBe(false);
    expect(none.find('[data-testid="objective-tracker__reward--q_single_no_reward"]').exists()).toBe(false);
  });

  it("renders no deadline line on the stage", () => {
    const rows = [
      {
        quest_id: "q_deadline",
        display_name: "限時任務",
        objective_line: "護送商隊",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 0,
        objective_quantity: 1,
        reward_copper: null,
        deadline_line: "剩餘 2 日",
      },
      {
        quest_id: "q_no_deadline",
        display_name: "一般任務",
        objective_line: "探查洞窟",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 0,
        objective_quantity: 1,
        reward_copper: null,
        deadline_line: null,
      },
    ];
    const w = mountTracker({ rows });
    expect(w.findAll('[data-testid^="objective-tracker__deadline--"]')).toHaveLength(0);
    expect(w.text()).not.toContain("剩餘 2 日");
  });

  it("renders nothing when rows is empty", () => {
    const w = mountTracker({ rows: [] });
    expect(w.find('[data-testid="objective-tracker"]').exists()).toBe(false);

    const wEmptyFixture = mountTracker({ rows: OBJECTIVES_PANEL_EMPTY_SAMPLE.rows });
    expect(wEmptyFixture.find('[data-testid="objective-tracker"]').exists()).toBe(false);
  });

  it("is purely display-only and carries zero action controls or inputs", () => {
    const w = mountTracker();
    expect(w.findAll("button")).toHaveLength(0);
    expect(w.findAll("input")).toHaveLength(0);
    expect(w.findAll("select")).toHaveLength(0);
    expect(w.findAll("textarea")).toHaveLength(0);
    expect(w.findAll("a")).toHaveLength(0);
  });
});
