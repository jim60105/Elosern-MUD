import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import QuestDetail from "../../components/QuestDetail.vue";
import { bookActions, bookDetail, offerActions, offerDetail } from "../../components/quest-drawer-model.js";
import { QUEST_LOG_PANEL_SAMPLE, SERVICES_PANEL_GUILD_BOARD_SAMPLE } from "../../stories/fixtures.js";

const rowById = (id) => QUEST_LOG_PANEL_SAMPLE.rows.find((row) => row.quest_id === id);
const enabled = (action_id, label) => ({ action_id, label, enabled: true, disabled_reason: null, quantity: null });
const disabled = (action_id, label, message) => ({
  action_id,
  label,
  enabled: false,
  disabled_reason: { code: "x", message },
  quantity: null,
});
const counterRow = (quest_id, overrides = {}) => ({
  quest_id,
  abandon: enabled("guild.quest_abandon", "放棄任務"),
  turnin: disabled("guild.quest_turnin", "交派任務", "任務目標尚未完成"),
  ...overrides,
});

describe("QuestDetail (quest-drawer-book-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountDetail(row, counter = null) {
    wrapper = mount(QuestDetail, {
      attachTo: document.body,
      props: { detail: bookDetail(row), actions: bookActions(row, counter) },
    });
    return wrapper;
  }

  async function show(row, counter = null) {
    await wrapper.setProps({ detail: bookDetail(row), actions: bookActions(row, counter) });
  }

  const find = (id) => wrapper.find(`[data-testid="quest-drawer__${id}"]`);
  const get = (id) => wrapper.get(`[data-testid="quest-drawer__${id}"]`);

  it("renders the hero, one-based progress pips, conditions, letter, and reward", () => {
    mountDetail({ ...rowById("q_1042"), stage_index: 0, stage_total: 1 });
    expect(get("ribbon").text()).toBe("討伐委託");
    expect(wrapper.get(".quest-detail__title").text()).toBe("驅除東部平原穗鳴雀");
    expect(wrapper.get(".quest-detail__objective").text()).toBe("在東部大平原討伐 2 隻穗鳴雀");
    expect(wrapper.get(".quest-detail__note").text()).toBe("計數變體：領群型、啄穗型");
    expect(wrapper.get(".grade-gem").attributes("aria-label")).toBe("F 級");
    expect(find("stamp").exists()).toBe(false);
    expect(get("stage").text()).toBe("階段 1 / 1");
    const pips = get("pips").findAll("span");
    expect(pips).toHaveLength(2);
    expect(pips.map((pip) => pip.classes().includes("is-on"))).toEqual([true, false]);
    expect(get("rationale").text()).toContain("低階群居鳥類");
    expect(get("deadline").text()).toContain("期限：剩餘 48 小時");
    expect(get("issuer").text()).toContain(rowById("q_1042").issuer.label);
    expect(get("issuer").text()).toContain("收穫已近尾聲");
    const cells = get("reward").findAll("li").map((cell) => cell.text().replace(/\s+/g, ""));
    const [item] = rowById("q_1042").reward.items;
    expect(cells).toEqual(["40銅", "20功績", `${item.display_name}×${item.quantity}`]);
    expect(get("settlement").text()).toBe("回公會櫃檯領取");
  });

  it("renders a bar for a target above twelve", () => {
    mountDetail({ ...rowById("q_1042"), objective_quantity: 30, stage_progress: 15 });
    expect(find("pips").exists()).toBe(false);
    expect(get("bar").get("span").attributes("style")).toContain("width: 50%");
  });

  it("stamps completed and failed rows and shows no progress for them", async () => {
    mountDetail(rowById("q_0301"));
    expect(get("stamp").text()).toBe("達成");
    expect(get("stamp").classes()).toContain("quest-detail__stamp--completed");
    expect(find("progress").exists()).toBe(false);
    await show(rowById("q_0099"));
    expect(get("stamp").text()).toBe("失敗");
    expect(get("stamp").classes()).toContain("quest-detail__stamp--failed");
  });

  it("omits null sections and shows the fixed fallbacks", () => {
    mountDetail({ ...rowById("q_0099"), rationale: null, flavor: null, deadline_line: null });
    expect(find("rationale").exists()).toBe(false);
    expect(get("issuer").get(".quest-detail__letter--muted").text()).toBe("委託人沒有留下說明。");
    expect(get("deadline").text()).toContain("無期限");
    // A null reward omits the whole section and its settlement note.
    expect(find("reward").exists()).toBe(false);
    expect(find("settlement").exists()).toBe(false);
  });

  it("emits the exact tracking payload and reflects only the committed flag", async () => {
    mountDetail({ ...rowById("q_1042"), tracked: false });
    const track = get("track");
    expect(track.attributes("aria-pressed")).toBe("false");
    expect(track.text()).toBe("追蹤");
    await track.trigger("click");
    expect(wrapper.emitted("action")).toEqual([
      [{ action_id: "guild.quest_track", payload: { quest_id: "q_1042", tracked: true } }],
    ]);
    // The pressed state waits for the commit.
    expect(get("track").attributes("aria-pressed")).toBe("false");
    await show(rowById("q_1042"));
    expect(get("track").attributes("aria-pressed")).toBe("true");
    expect(get("track").text()).toBe("追蹤中");
  });

  it("renders no tracking control for completed or failed rows", async () => {
    mountDetail(rowById("q_0301"));
    expect(find("track").exists()).toBe(false);
    await show(rowById("q_0099"));
    expect(find("track").exists()).toBe(false);
    expect(get("action-reason").text()).toBe("此委託已失敗，沒有報酬。");
  });

  it("arms abandon first, names the quest, and dispatches only on confirm", async () => {
    mountDetail(rowById("q_1042"), counterRow("q_1042"));
    await get("abandon").trigger("click");
    expect(wrapper.emitted("action")).toBeUndefined();
    expect(get("abandon-confirm").text()).toBe("放棄「驅除東部平原穗鳴雀」後任務會判定失敗，且無法回復。");
    expect(document.activeElement).toBe(get("abandon-confirm-no").element);
    await get("abandon-confirm-yes").trigger("click");
    expect(wrapper.emitted("action")).toEqual([
      [{ action_id: "guild.quest_abandon", payload: { quest_id: "q_1042" } }],
    ]);
    expect(find("abandon-confirm").exists()).toBe(false);
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(get("track").element);
  });

  it("cancels an armed abandon without dispatching and returns focus", async () => {
    mountDetail(rowById("q_1042"), counterRow("q_1042"));
    await get("abandon").trigger("click");
    await get("abandon-confirm-no").trigger("click");
    await wrapper.vm.$nextTick();
    expect(find("abandon-confirm").exists()).toBe(false);
    expect(document.activeElement).toBe(get("abandon").element);
    expect(wrapper.emitted("action")).toBeUndefined();
  });

  it("disarms when the selection changes or the abandon descriptor goes away", async () => {
    mountDetail(rowById("q_1042"), counterRow("q_1042"));
    await get("abandon").trigger("click");
    await show(rowById("q_2077"));
    expect(find("abandon-confirm").exists()).toBe(false);
    await show(rowById("q_1042"), counterRow("q_1042"));
    expect(find("abandon-confirm").exists()).toBe(false);

    await get("abandon").trigger("click");
    await show(rowById("q_1042"), null);
    expect(find("abandon-confirm").exists()).toBe(false);
    await show(rowById("q_1042"), counterRow("q_1042"));
    expect(find("abandon-confirm").exists()).toBe(false);
    expect(wrapper.emitted("action")).toBeUndefined();
  });

  it("offers an enabled turn-in with the descriptor's label and exact payload", async () => {
    mountDetail(rowById("q_0301"), counterRow("q_0301", { turnin: enabled("guild.quest_turnin", "交派任務") }));
    expect(get("turnin").text()).toBe("交派任務");
    expect(find("action-reason").exists()).toBe(false);
    await get("turnin").trigger("click");
    expect(wrapper.emitted("action")).toEqual([
      [{ action_id: "guild.quest_turnin", payload: { quest_id: "q_0301" } }],
    ]);
  });

  it("shows a disabled turn-in's reason and no turn-in control", () => {
    mountDetail(rowById("q_0301"), counterRow("q_0301", { turnin: disabled("guild.quest_turnin", "交派任務", "報酬已領取過了") }));
    expect(find("turnin").exists()).toBe(false);
    expect(get("action-reason").text()).toBe("報酬已領取過了");
  });

  it("states the claimed reward or the counter return away from a clerk", async () => {
    mountDetail({ ...rowById("q_0301"), reward_claimed: true });
    expect(get("action-reason").text()).toBe("報酬已領取");
    await show(rowById("q_0301"));
    expect(get("action-reason").text()).toBe("回到公會櫃檯即可交付並領取報酬。");
  });

  it("offers only tracking for a private commission in front of a clerk", () => {
    mountDetail(rowById("q_2077"), null);
    expect(find("track").exists()).toBe(true);
    expect(find("abandon").exists()).toBe(false);
    expect(find("turnin").exists()).toBe(false);
  });

  it("renders an empty detail when nothing is selected", () => {
    wrapper = mount(QuestDetail, { props: { detail: null } });
    expect(find("detail-empty").exists()).toBe(true);
    expect(find("actions").exists()).toBe(false);
  });

  describe("a board offer (quest-drawer-guild-board-tab)", () => {
    const GUILD = SERVICES_PANEL_GUILD_BOARD_SAMPLE.guild;
    const open = GUILD.board.find((row) => row.accept.enabled && row.rationale);
    const held = GUILD.board.find((row) => !row.accept.enabled);

    function mountOffer(row) {
      wrapper = mount(QuestDetail, {
        attachTo: document.body,
        props: { detail: offerDetail(row, GUILD.branch_label), actions: offerActions(row) },
      });
    }

    it("shows the acceptance condition in place of the rationale cell", () => {
      mountOffer(open);
      expect(get("condition").text()).toContain("接取條件");
      expect(get("condition").text()).toContain(`公會等級 ${open.rank} 級以上`);
      expect(get("condition").text()).toContain(open.rationale);
      expect(find("rationale").exists()).toBe(false);
      expect(find("progress").exists()).toBe(false);
      expect(find("stamp").exists()).toBe(false);
    });

    it("renders the enabled accept as the primary action", async () => {
      mountOffer(open);
      const accept = get("accept");
      expect(accept.classes()).toContain("quest-detail__btn--primary");
      expect(accept.attributes("aria-disabled")).toBeUndefined();
      await accept.trigger("click");
      expect(wrapper.emitted("action")).toEqual([
        [{ action_id: open.accept.action_id, payload: { definition_key: open.definition_key } }],
      ]);
      expect(find("track").exists()).toBe(false);
    });

    it("keeps a disabled accept focusable beside its reason and inert", async () => {
      mountOffer(held);
      const accept = get("accept");
      expect(accept.attributes("disabled")).toBeUndefined();
      expect(accept.attributes("aria-disabled")).toBe("true");
      expect(get("action-reason").text()).toBe(held.accept.disabled_reason.message);
      await accept.trigger("click");
      expect(wrapper.emitted("action")).toBeUndefined();
    });
  });
});
