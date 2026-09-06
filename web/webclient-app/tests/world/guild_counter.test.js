import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GuildCounter from "../../components/GuildCounter.vue";
import {
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
    const mill = w.get('[data-testid="guild-counter__board-row--quest_mill_grain"]');
    expect(mill.text()).toContain("磨坊糧運");
    expect(mill.text()).toContain("將十袋糧食運往磨坊");
    expect(mill.text()).toContain("400 銅＋公會功績 25");
    const accept = mill.get('[data-testid="guild-counter__accept"]');
    await accept.trigger("click");
    expect(w.emitted("quest_accept")).toEqual([
      [{ action_id: "guild.quest_accept", payload: { definition_key: "quest_mill_grain" } }],
    ]);
    expect(w.get('[data-testid="guild-counter__rankblock"]').exists()).toBe(true);
    expect(w.get('[data-testid="guild-counter__rank-level"]').text()).toContain("C");
    const exam = w.get('[data-testid="guild-counter__exam"]');
    await exam.trigger("click");
    expect(w.emitted("exam_start")).toEqual([
      [{ action_id: "guild.exam_start", payload: { target_rank: "B" } }],
    ]);
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
