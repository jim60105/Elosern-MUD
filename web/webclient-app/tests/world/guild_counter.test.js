import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GuildCounter from "../../components/GuildCounter.vue";
import {
  SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE,
  SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE,
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
    expect(w.emitted("exam_request")).toEqual([
      [{ action_id: "guild.exam_request", payload: { target_rank: "B" } }],
    ]);
  });

  it("offers the exam request below the merit threshold and says so honestly", async () => {
    const w = mountCounter();
    const status = w.get('[data-testid="guild-counter__merit-status"]');
    expect(status.attributes("data-qualified")).toBe("false");
    expect(status.text()).toContain("功績未達標");
    expect(status.text()).toContain("尚差 160");
    const exam = w.get('[data-testid="guild-counter__exam"]');
    expect(exam.isVisible()).toBe(true);
    expect(exam.attributes("disabled")).toBeUndefined();
    expect(exam.text()).toContain("預約升等考核");
    const hint = w.get('[data-testid="guild-counter__exam-hint"]');
    expect(hint.text()).toContain("考官在公會時即可應考");
    expect(exam.attributes("aria-describedby")).toBe(hint.attributes("id"));
    expect(w.find('[data-testid="guild-counter__exam-reason"]').exists()).toBe(false);
    await exam.trigger("click");
    expect(w.emitted("exam_request")).toEqual([
      [{ action_id: "guild.exam_request", payload: { target_rank: "B" } }],
    ]);
  });

  it("exposes the merit meter as a clamped progressbar", () => {
    const below = mountCounter();
    const meter = below.get('[data-testid="guild-counter__merit-meter"]');
    expect(meter.attributes("role")).toBe("progressbar");
    expect(meter.attributes("aria-valuemin")).toBe("0");
    expect(meter.attributes("aria-valuemax")).toBe("300");
    expect(meter.attributes("aria-valuenow")).toBe("140");
    expect(below.get('[data-testid="guild-counter__merit"]').text()).toContain("140");
    below.unmount();

    // Merit past the threshold fills the bar without overflowing it.
    const met = mountCounter({ services: SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE });
    const full = met.get('[data-testid="guild-counter__merit-meter"]');
    expect(full.attributes("aria-valuenow")).toBe("300");
    expect(full.attributes("aria-valuetext")).toContain("325");
    expect(full.get(".guild-counter__meter-fill").attributes("style")).toContain("width: 100%");
    const status = met.get('[data-testid="guild-counter__merit-status"]');
    expect(status.attributes("data-qualified")).toBe("true");
    expect(status.text()).toContain("功績已達標");
    expect(met.get('[data-testid="guild-counter__exam"]').attributes("disabled")).toBeUndefined();
  });

  it("renders the top rank without a meter and with its disabled reason", async () => {
    const w = mountCounter({ services: SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE });
    expect(w.get('[data-testid="guild-counter__rank-level"]').text()).toContain("S");
    expect(w.get('[data-testid="guild-counter__rank-top"]').text()).toContain("最高等級");
    expect(w.find('[data-testid="guild-counter__merit-meter"]').exists()).toBe(false);
    expect(w.find('[data-testid="guild-counter__merit-status"]').exists()).toBe(false);
    expect(w.text()).not.toContain("null");
    const exam = w.get('[data-testid="guild-counter__exam"]');
    expect(exam.attributes("disabled")).toBeDefined();
    const reason = w.get('[data-testid="guild-counter__exam-reason"]');
    expect(reason.attributes("data-reason-code")).toBe("top_rank");
    expect(reason.text()).toContain("你已是最高階級，沒有下一場升等考核。");
    expect(exam.attributes("aria-describedby")).toBe(reason.attributes("id"));
    expect(w.find('[data-testid="guild-counter__exam-hint"]').exists()).toBe(false);
    await exam.trigger("click");
    expect(w.emitted("exam_request")).toBeUndefined();
  });

  it("renders a busy counter and an unregistered holder as disabled requests with reasons", () => {
    const busy = mountCounter({ services: SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE });
    expect(busy.get('[data-testid="guild-counter__exam"]').attributes("disabled")).toBeDefined();
    expect(busy.get('[data-testid="guild-counter__exam-reason"]').text()).toContain(
      "她現在正忙著，沒有理會你。",
    );
    // Merit progress still reads honestly while the counter is busy.
    expect(busy.find('[data-testid="guild-counter__merit-meter"]').exists()).toBe(true);
    busy.unmount();

    const unregistered = mountCounter({ services: SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE });
    expect(unregistered.get('[data-testid="guild-counter__registration"]').attributes("data-registered")).toBe(
      "false",
    );
    expect(unregistered.get('[data-testid="guild-counter__rank-level"]').text()).toContain("尚未評級");
    expect(unregistered.find('[data-testid="guild-counter__rank-top"]').exists()).toBe(false);
    expect(unregistered.find('[data-testid="guild-counter__merit-meter"]').exists()).toBe(false);
    expect(unregistered.get('[data-testid="guild-counter__exam"]').attributes("disabled")).toBeDefined();
    const reason = unregistered.get('[data-testid="guild-counter__exam-reason"]');
    expect(reason.attributes("data-reason-code")).toBe("unregistered");
    expect(reason.text()).toContain("你尚未註冊為冒險者。");
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
