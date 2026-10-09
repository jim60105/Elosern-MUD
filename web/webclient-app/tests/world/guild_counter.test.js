import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GuildCounter from "../../components/GuildCounter.vue";
import {
  SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE,
  SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE,
  SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("GuildCounter (quest-drawer-split)", () => {
  let wrapper;

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
      wrapper = undefined;
    }
  });

  function mountCounter(props = {}) {
    wrapper = mount(GuildCounter, {
      props: {
        services: SERVICES_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders registration, board rows with accept, and the rank block (task 2.1)", async () => {
    const w = mountCounter();
    const reg = w.get('[data-testid="guild-counter__registration"]');
    expect(reg.attributes("data-registered")).toBe("true");
    expect(reg.text()).toContain("已加入公會");
    expect(reg.text()).toContain("你已經是公會成員");
    const mill = w.get('[data-testid="guild-counter__board-row--eastern_plains_sway_whistle_sparrow"]');
    expect(mill.text()).toContain("驅除東部平原穗鳴雀");
    expect(mill.text()).toContain("在東部大平原討伐 2 隻穗鳴雀");
    expect(mill.text()).toContain("銅 50、功績 25");
    const accept = mill.get('[data-testid="guild-counter__accept"]');
    await accept.trigger("click");
    expect(w.emitted("quest_accept")).toEqual([
      [{ action_id: "guild.quest_accept", payload: { definition_key: "eastern_plains_sway_whistle_sparrow" } }],
    ]);
    expect(w.get('[data-testid="guild-counter__rankblock"]').exists()).toBe(true);
    expect(w.get('[data-testid="guild-counter__rank-level"]').text()).toContain("C");
    const exam = w.get('[data-testid="guild-counter__exam"]');
    await exam.trigger("click");
    expect(w.emitted("exam_request")).toEqual([
      [{ action_id: "guild.exam_request", payload: { target_rank: "B" } }],
    ]);
  });

  it("renders structured rewards under one label with optional facts verbatim", () => {
    const services = structuredClone(SERVICES_PANEL_SAMPLE);
    const row = services.guild.board[0];
    row.reward = { copper: 120, merit: 45, items: [{ item_key: "synthetic_item", display_name: "合成物品", quantity: 2 }] };
    row.deadline_line = "接取後 3 日";
    const w = mountCounter({ services });
    const board = w.get(`[data-testid="guild-counter__board-row--${row.definition_key}"]`);
    expect(board.get(".guild-counter__row-reward").text()).toBe("獎勵：銅 120、功績 45、合成物品 × 2");
    expect(board.get('[data-testid="guild-counter__objective-note"]').text()).toBe(row.objective_note);
    expect(board.get('[data-testid="guild-counter__deadline"]').text()).toBe(row.deadline_line);
    expect(board.text().match(/獎勵：/g)).toHaveLength(1);
  });

  it("omits zero merit and null optional facts without placeholders", () => {
    const services = structuredClone(SERVICES_PANEL_SAMPLE);
    const row = services.guild.board[0];
    row.reward = { copper: 120, merit: 0, items: [] };
    row.objective_note = row.deadline_line = row.rationale = row.flavor = null;
    const w = mountCounter({ services });
    const board = w.get(`[data-testid="guild-counter__board-row--${row.definition_key}"]`);
    expect(board.get(".guild-counter__row-reward").text()).toBe("獎勵：銅 120");
    expect(board.find('[data-testid="guild-counter__objective-note"]').exists()).toBe(false);
    expect(board.find('[data-testid="guild-counter__deadline"]').exists()).toBe(false);
    expect(board.text()).not.toContain("功績");
    expect(board.text()).not.toContain("無期限");
    expect(board.text()).not.toContain("null");
  });

  it("hosts the rank card and forwards its exam request (rank details: guild_rank_card.test.js)", async () => {
    const w = mountCounter({ services: SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE });
    const block = w.get('[data-testid="guild-counter__rankblock"]');
    expect(block.get(".guild-counter__section-title").text()).toBe("公會等級");
    expect(block.get('[data-testid="guild-rank-card"]').attributes("data-top-rank")).toBe("true");
    w.unmount();

    const busy = mountCounter({ services: SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE });
    expect(busy.get('[data-testid="guild-counter__exam"]').attributes("disabled")).toBeDefined();
    busy.unmount();

    const unregistered = mountCounter({ services: SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE });
    expect(unregistered.get('[data-testid="guild-counter__registration"]').attributes("data-registered")).toBe(
      "false",
    );
    expect(unregistered.get('[data-testid="guild-counter__rank-level"]').text()).toContain("尚未評級");
  });

  it("renders no accepted-quest rows even when the payload carries them (task 2.2)", () => {
    const w = mountCounter();
    // The services sample's guild section carries the q_1042 record row; the
    // counter must not list it — the quest book owns the holder's records.
    expect(w.find('[data-testid="guild-counter__quest-row--q_1042"]').exists()).toBe(false);
    expect(w.text()).not.toContain("老周把三袋糧食交給你");
    expect(w.text()).not.toContain("放棄任務");
  });

  it("renders the registry-owned unavailable reason and the absent marker honestly (task 2.3)", () => {
    const unavailable = mountCounter({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    expect(unavailable.get('[data-testid="guild-counter__unavailable"]').text()).toContain(
      "服務選單目前無法顯示",
    );
    expect(unavailable.findAll('[data-testid^="guild-counter__board-row--"]')).toHaveLength(0);
    unavailable.unmount();

    const absent = mountCounter({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    expect(absent.get('[data-testid="guild-counter__absent"]').exists()).toBe(true);
    expect(absent.find('[data-testid="guild-counter__registration"]').exists()).toBe(false);
  });
});
