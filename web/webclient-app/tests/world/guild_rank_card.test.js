import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GuildRankCard from "../../components/GuildRankCard.vue";
import {
  SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE,
  SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE,
  SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE,
  SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE,
  SERVICES_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// The rank-block assertions moved here from guild_counter.test.js when the
// block was extracted into GuildRankCard (quest-drawer-ui-primitives).
describe("GuildRankCard (quest-drawer-ui-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  function mountCard(services = SERVICES_PANEL_SAMPLE) {
    wrapper = mount(GuildRankCard, { props: { rank: services.guild.rank } });
    return wrapper;
  }

  it("renders the rank card root with the rank and next step", () => {
    const w = mountCard();
    const root = w.get('[data-testid="guild-rank-card"]');
    expect(root.classes()).toContain("guild-counter__rank-card");
    expect(root.attributes("data-top-rank")).toBe("false");
    expect(w.get('[data-testid="guild-counter__rank-level"]').text()).toContain("C");
    expect(w.get('[data-testid="guild-counter__rank-next"]').text()).toContain("B");
  });

  it("offers the exam request below the merit threshold and says so honestly", async () => {
    const w = mountCard();
    const status = w.get('[data-testid="guild-counter__merit-status"]');
    expect(status.attributes("data-qualified")).toBe("false");
    expect(status.text()).toContain("功績未達標");
    expect(status.text()).toContain("尚差 160");
    const exam = w.get('[data-testid="guild-counter__exam"]');
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
    const below = mountCard();
    const meter = below.get('[data-testid="guild-counter__merit-meter"]');
    expect(meter.attributes("role")).toBe("progressbar");
    expect(meter.attributes("aria-valuemin")).toBe("0");
    expect(meter.attributes("aria-valuemax")).toBe("300");
    expect(meter.attributes("aria-valuenow")).toBe("140");
    expect(below.get('[data-testid="guild-counter__merit"]').text()).toContain("140");
    below.unmount();

    // Merit past the threshold fills the bar without overflowing it.
    const met = mountCard(SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE);
    const full = met.get('[data-testid="guild-counter__merit-meter"]');
    expect(full.attributes("aria-valuenow")).toBe("300");
    expect(full.attributes("aria-valuetext")).toContain("325");
    expect(full.get(".guild-counter__meter-fill").attributes("style")).toContain("width: 100%");
    const status = met.get('[data-testid="guild-counter__merit-status"]');
    expect(status.attributes("data-qualified")).toBe("true");
    expect(status.text()).toContain("功績已達標");
    const exam = met.get('[data-testid="guild-counter__exam"]');
    expect(exam.attributes("disabled")).toBeUndefined();
    expect(exam.classes()).toContain("guild-counter__exam-button--ready");
  });

  it("renders the top rank crest without a meter and with its disabled reason", async () => {
    const w = mountCard(SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE);
    expect(w.get('[data-testid="guild-rank-card"]').attributes("data-top-rank")).toBe("true");
    expect(w.get(".guild-counter__crest").classes()).toContain("guild-counter__crest--top");
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

  it("renders a busy counter and an unregistered holder as disabled requests with reasons", async () => {
    const busy = mountCard(SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE);
    const busyExam = busy.get('[data-testid="guild-counter__exam"]');
    expect(busyExam.attributes("disabled")).toBeDefined();
    expect(busy.get('[data-testid="guild-counter__exam-reason"]').text()).toContain(
      "她現在正忙著，沒有理會你。",
    );
    // Merit progress still reads honestly while the counter is busy.
    expect(busy.find('[data-testid="guild-counter__merit-meter"]').exists()).toBe(true);
    // The click handler refuses a disabled request even if the event fires.
    busyExam.element.disabled = false;
    await busyExam.trigger("click");
    expect(busy.emitted("exam_request")).toBeUndefined();
    busy.unmount();

    const unregistered = mountCard(SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE);
    expect(unregistered.get('[data-testid="guild-rank-card"]').attributes("data-top-rank")).toBe("false");
    expect(unregistered.get('[data-testid="guild-counter__rank-level"]').text()).toContain("尚未評級");
    expect(unregistered.get(".guild-counter__crest-letter").text()).toBe("—");
    expect(unregistered.find('[data-testid="guild-counter__rank-top"]').exists()).toBe(false);
    expect(unregistered.find('[data-testid="guild-counter__merit-meter"]').exists()).toBe(false);
    expect(unregistered.get('[data-testid="guild-counter__exam"]').attributes("disabled")).toBeDefined();
    const reason = unregistered.get('[data-testid="guild-counter__exam-reason"]');
    expect(reason.attributes("data-reason-code")).toBe("unregistered");
    expect(reason.text()).toContain("你尚未註冊為冒險者。");
  });
});
