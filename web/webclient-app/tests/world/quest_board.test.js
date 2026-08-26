import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import QuestBoard from "../../components/QuestBoard.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("QuestBoard (B4 services family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountBoard(props = {}) {
    wrapper = mount(QuestBoard, {
      props: {
        services: SERVICES_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders both board rows from the payload with objective and reward summaries", () => {
    const w = mountBoard();
    const mill = w.get('[data-testid="quest-board__board-row--quest_mill_grain"]');
    expect(mill.text()).toContain("磨坊糧運");
    expect(mill.text()).toContain("將十袋糧食運往磨坊");
    expect(mill.text()).toContain("400 銅＋公會功績 25");
    expect(mill.text()).toContain("C");

    const harbor = w.get('[data-testid="quest-board__board-row--quest_harbor_light"]');
    expect(harbor.text()).toContain("燈塔值守");
    expect(harbor.text()).toContain("為渡口燈塔補足燈油");
    expect(harbor.text()).toContain("220 銅＋公會功績 15");
    expect(harbor.text()).toContain("B");
  });

  it("clicking an enabled accept control emits the payload's own guild.quest_accept intent", async () => {
    const w = mountBoard();
    const accept = w
      .get('[data-testid="quest-board__board-row--quest_mill_grain"]')
      .find(".quest-board__action");
    await accept.trigger("click");
    expect(w.emitted("quest_accept")).toEqual([
      [{ action_id: "guild.quest_accept", payload: { definition_key: "quest_mill_grain" } }],
    ]);
  });

  it("renders the registration line with the disabled register reason", () => {
    const reg = mountBoard().get('[data-testid="quest-board__registration"]');
    expect(reg.attributes("data-registered")).toBe("true");
    expect(reg.text()).toContain("已加入公會");
    expect(reg.text()).toContain("你已經是公會成員");
  });

  it("renders the active quest detail with state, stage progress, deadline, and story text", () => {
    const row = mountBoard().get('[data-testid="quest-board__quest-row--q_1042"]');
    expect(row.text()).toContain("磨坊糧運");
    expect(row.get('[data-testid="quest-board__quest-state"]').text()).toBe("進行中");
    expect(row.get('[data-testid="quest-board__quest-stage"]').text()).toContain("3");
    expect(row.get('[data-testid="quest-board__quest-deadline"]').text()).toBe("剩餘 2 日");
    expect(row.get('[data-testid="quest-board__quest-detail"]').text()).toBe(
      "老周把三袋糧食交給你，要求天亮前送到磨坊。",
    );
    // The disabled turnin action shows its reason text, not a control.
    expect(row.text()).toContain("任務目標尚未完成");
  });

  it("abandon uses a two-step confirmation: 確認放棄 only then dispatches guild.quest_abandon (H4 task 7.2)", async () => {
    const w = mountBoard();
    const abandon = w.get('[data-testid="quest-board__abandon"]');
    await abandon.trigger("click");
    // Arming the abandon button shows the confirm bar; the action is not
    // dispatched until the explicit confirm is clicked.
    const confirmBar = w.get('[data-testid="quest-board__abandon-confirm"]');
    expect(confirmBar.exists()).toBe(true);
    expect(w.emitted("quest_abandon")).toBeUndefined();
    await confirmBar.find('[data-testid="quest-board__abandon-confirm-yes"]').trigger("click");
    expect(w.emitted("quest_abandon")).toEqual([
      [{ action_id: "guild.quest_abandon", payload: { quest_id: "q_1042" } }],
    ]);
    // The confirm bar closes after dispatching.
    expect(w.find('[data-testid="quest-board__abandon-confirm"]').exists()).toBe(false);
  });

  it("cancelling the abandon confirmation keeps the confirm state cleared and emits nothing", async () => {
    const w = mountBoard();
    await w.get('[data-testid="quest-board__abandon"]').trigger("click");
    const confirmBar = w.get('[data-testid="quest-board__abandon-confirm"]');
    await confirmBar.find('[data-testid="quest-board__abandon-confirm-no"]').trigger("click");
    expect(w.emitted("quest_abandon")).toBeUndefined();
    expect(w.find('[data-testid="quest-board__abandon-confirm"]').exists()).toBe(false);
  });

  it("renders the rank block with merit and the next-rank threshold", () => {
    const w = mountBoard();
    expect(w.get('[data-testid="quest-board__rank"]').text()).toContain("C");
    expect(w.get('[data-testid="quest-board__merit"]').text()).toContain("140");
    expect(w.get('[data-testid="quest-board__merit"]').text()).toContain("300");
    expect(w.get('[data-testid="quest-board__merit"]').text()).toContain("B");
  });

  it("clicking the enabled exam control emits exam_start", async () => {
    const w = mountBoard();
    const exam = w.get('[data-testid="quest-board__exam"]');
    await exam.trigger("click");
    expect(w.emitted("exam_start")).toEqual([[{ action_id: "guild.exam_start" }]]);
  });

  it("renders the honest absent marker when the guild section is missing", () => {
    const w = mountBoard({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    expect(w.get('[data-testid="quest-board__absent"]').exists()).toBe(true);
    expect(w.findAll('[data-testid^="quest-board__board-row--"]')).toHaveLength(0);
    expect(w.findAll('[data-testid^="quest-board__quest-row--"]')).toHaveLength(0);
    expect(w.find('[data-testid="quest-board__rankblock"]').exists()).toBe(false);
  });

  it("labels a failed quest with the server bounded-state label (no invented states)", () => {
    const services = {
      ...SERVICES_PANEL_SAMPLE,
      guild: {
        ...SERVICES_PANEL_SAMPLE.guild,
        quests: [{ ...SERVICES_PANEL_SAMPLE.guild.quests[0], state: "failed" }],
      },
    };
    const row = mountBoard({ services }).get('[data-testid="quest-board__quest-row--q_1042"]');
    expect(row.get('[data-testid="quest-board__quest-state"]').text()).toBe("失敗");
  });

  it("renders the terminal rank without a fabricated promotion line (nullable next rank/threshold)", () => {
    const services = {
      ...SERVICES_PANEL_SAMPLE,
      guild: {
        ...SERVICES_PANEL_SAMPLE.guild,
        rank: { ...SERVICES_PANEL_SAMPLE.guild.rank, next_rank: null, next_threshold: null },
      },
    };
    const w = mountBoard({ services });
    const merit = w.get('[data-testid="quest-board__merit"]');
    expect(merit.text()).toContain("140");
    expect(merit.text()).toContain("最高等級");
    expect(merit.text()).not.toContain("null");
  });

  it("unavailable services: renders only the registry-owned reason, no guild content", () => {
    const w = mountBoard({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    const reason = w.get('[data-testid="quest-board__unavailable"]');
    expect(reason.text()).toBe("服務選單目前無法顯示");
    expect(w.find('[data-testid="quest-board__absent"]').exists()).toBe(false);
    expect(w.find('[data-testid="quest-board__rankblock"]').exists()).toBe(false);
    expect(w.find('[data-testid="quest-board__registration"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="quest-board__board-row--"]')).toHaveLength(0);
    expect(w.findAll('[data-testid^="quest-board__quest-row--"]')).toHaveLength(0);
  });
});
