import { readFileSync } from "node:fs";
import { join } from "node:path";
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

  function counted(quest_id, objective_quantity, stage_progress) {
    return {
      quest_id,
      display_name: "計數任務",
      objective_line: "收集藥草",
      stage_index: 1,
      stage_total: 1,
      stage_progress,
      objective_quantity,
      reward_copper: null,
      deadline_line: null,
    };
  }

  it("names the region 目標 without a visible label and counts further rows with a glyph", () => {
    const w = mountTracker();
    const root = w.get('[data-testid="objective-tracker"]');
    expect(w.find(".obj__label").exists()).toBe(false);
    expect(root.text()).not.toContain("目標");
    expect(root.attributes("aria-label")).toBe("目標");
    expect(root.attributes("role")).toBe("region");
    expect(root.classes()).toEqual(expect.arrayContaining(["obj", "instrument-panel"]));
    const more = w.get('[data-testid="objective-tracker__more"]');
    expect(more.text()).toBe("2");
    expect(more.attributes("aria-label")).toBe("另有 2 項追蹤目標");
    expect(more.attributes("title")).toBe("另有 2 項追蹤目標");
    expect(more.find("svg").exists()).toBe(true);
    expect(more.text()).not.toContain("+");
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

  it("fills the lozenge with a check and names it 已達成 once reached, else an open 進行中 lozenge", () => {
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
    expect(doneBox.attributes("aria-label")).toBe("已達成");
    expect(doneBox.find(".bx__check").exists()).toBe(true);

    const pending = mountTracker({ rows: [rows[1]] });
    const notDoneBox = pending.get('[data-testid="objective-tracker__box--q_not_done"]');
    expect(notDoneBox.classes()).not.toContain("done");
    expect(notDoneBox.attributes("aria-label")).toBe("進行中");
    expect(notDoneBox.find("svg .bx__lozenge").exists()).toBe(true);
    expect(notDoneBox.find(".bx__check").exists()).toBe(false);
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
        reward_copper: 100, // quantity > 1 takes precedence: displays 2 / 5
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
    expect(progressEl.get("b").text()).toBe("2");
    expect(progressEl.get("i").text()).toBe("/ 5");
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

  it("draws one tick per unit up to twelve, reached ticks first", () => {
    const w = mountTracker({ rows: [counted("q_ticks", 5, 2)] });
    const ticks = w.findAll('[data-testid="objective-tracker__tick"]');
    expect(ticks).toHaveLength(5);
    expect(ticks.map((t) => t.classes().includes("obj__tick--on"))).toEqual([true, true, false, false, false]);
    expect(w.get('[data-testid="objective-tracker__ticks"]').attributes("aria-hidden")).toBe("true");
    expect(w.find('[data-testid="objective-tracker__stroke"]').exists()).toBe(false);

    const over = mountTracker({ rows: [counted("q_over", 12, 15)] });
    const overTicks = over.findAll('[data-testid="objective-tracker__tick"]');
    expect(overTicks).toHaveLength(12);
    expect(overTicks.every((t) => t.classes().includes("obj__tick--on"))).toBe(true);

    const reached = mountTracker({ rows: [counted("q_reached", 5, 5)] });
    expect(reached.get('[data-testid="objective-tracker"]').classes()).toContain("obj--done");
  });

  it("draws one stroke above twelve units, filled to the ratio", () => {
    const w = mountTracker({ rows: [counted("q_long_count", 30, 12)] });
    expect(w.find('[data-testid="objective-tracker__tick"]').exists()).toBe(false);
    const stroke = w.get('[data-testid="objective-tracker__stroke"]');
    expect(stroke.attributes("aria-hidden")).toBe("true");
    expect(w.get('[data-testid="objective-tracker__stroke-fill"]').attributes("style")).toContain("width: 40%");

    const negative = mountTracker({ rows: [counted("q_negative", 30, -3)] });
    expect(negative.get('[data-testid="objective-tracker__stroke-fill"]').attributes("style")).toContain("width: 0%");

    const notANumber = mountTracker({ rows: [counted("q_nan", 30, Number.NaN)] });
    expect(notANumber.get('[data-testid="objective-tracker__stroke-fill"]').attributes("style")).toContain("width: 0%");
  });

  it("draws no quantity marks for a single-count objective", () => {
    const missing = counted("q_missing", 5, 0);
    delete missing.objective_quantity;
    for (const row of [counted("q_one", 1, 0), missing, counted("q_string", "5", 5)]) {
      const w = mountTracker({ rows: [row] });
      expect(w.find('[data-testid="objective-tracker__ticks"]').exists()).toBe(false);
      expect(w.find('[data-testid="objective-tracker__stroke"]').exists()).toBe(false);
    }
    const stringy = mountTracker({ rows: [counted("q_string", "5", 5)] });
    expect(stringy.get('[data-testid="objective-tracker__box--q_string"]').classes()).not.toContain("done");
  });

  it("wears the shared instrument-panel chrome and paints no box of its own", () => {
    const source = readFileSync(
      join(process.cwd(), "web/webclient-app/components/ObjectiveTracker.vue"),
      "utf-8",
    );
    expect(source).toContain('import "./instrument-panel.css";');
    const style = source.slice(source.indexOf("<style"));
    const rule = style.match(/\n\.obj \{([\s\S]*?)\}/);
    expect(rule).not.toBeNull();
    // Property declarations, not substrings: `box-sizing: border-box` is allowed.
    const forbidden = /(^|[;{\s])(height|padding[\w-]*|background[\w-]*|border[\w-]*|box-shadow|backdrop-filter)\s*:/;
    expect(rule[1]).not.toMatch(forbidden);
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
