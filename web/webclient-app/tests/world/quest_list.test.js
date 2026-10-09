import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import QuestList from "../../components/QuestList.vue";
import { bookListRow, rowsByState } from "../../components/quest-drawer-model.js";
import { QUEST_LOG_PANEL_SAMPLE, QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE } from "../../stories/fixtures.js";

const IN_PROGRESS = rowsByState(QUEST_LOG_PANEL_SAMPLE).in_progress.map(bookListRow);
const THREE = [
  ...IN_PROGRESS,
  { ...IN_PROGRESS[1], id: "q_3000", name: "第三份委託", tracked: false },
];

describe("QuestList (quest-drawer-book-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  // A selection host: the parent writes every emitted selection back.
  function mountList(props = {}) {
    wrapper = mount(QuestList, {
      attachTo: document.body,
      props: {
        heading: "進行中",
        rows: THREE,
        selectedId: "q_1042",
        onSelect: (id) => wrapper.setProps({ selectedId: id }),
        ...props,
      },
    });
    return wrapper;
  }

  const row = (id) => wrapper.get(`[data-testid="quest-drawer__row--${id}"]`);
  const tabindexes = () => wrapper.findAll('[role="option"]').map((option) => option.attributes("tabindex"));
  const focusedId = () => document.activeElement?.dataset.questId;

  async function press(key) {
    document.activeElement.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
    await nextTick();
    await nextTick();
  }

  it("renders a heading with the count and a single-selection listbox", () => {
    mountList();
    expect(wrapper.get(".quest-list__kicker").text()).toBe("進行中");
    expect(wrapper.get('[data-testid="quest-drawer__list-count"]').text()).toBe("3");
    const list = wrapper.get('[role="listbox"]');
    expect(list.attributes("aria-label")).toBe("任務");
    expect(row("q_1042").attributes("aria-selected")).toBe("true");
    expect(row("q_2077").attributes("aria-selected")).toBe("false");
    expect(tabindexes()).toEqual(["0", "-1", "-1"]);
  });

  it("renders the category glyph, name, tracked flag, grade, and progress", () => {
    mountList();
    const tracked = row("q_1042");
    expect(tracked.get(".quest-list__name-text").text()).toBe("驅除東部平原穗鳴雀");
    expect(tracked.find('[data-testid="quest-drawer__row-tracked"]').attributes("aria-label")).toBe("追蹤中");
    expect(tracked.find(".quest-list__cat svg path").exists()).toBe(true);
    expect(tracked.get(".grade-gem").attributes("data-grade")).toBe("F");
    expect(tracked.get(".quest-list__num").text()).toBe("1/2");
    expect(tracked.get(".quest-list__bar span").attributes("style")).toContain("width: 50%");
    expect(row("q_2077").find('[data-testid="quest-drawer__row-tracked"]').exists()).toBe(false);
  });

  it("shows the issuer line instead of progress on terminal rows", () => {
    mountList({ rows: rowsByState(QUEST_LOG_PANEL_SAMPLE).failed.map(bookListRow), selectedId: "q_0099" });
    expect(row("q_0099").get(".quest-list__sub").text()).toBe("公會委託 · 期限：已逾期");
    expect(row("q_0099").find(".quest-list__prog").exists()).toBe(false);
    expect(row("q_0099").classes()).toContain("is-failed");
  });

  it("selects on click and emits only on change", async () => {
    mountList();
    await row("q_2077").trigger("click");
    await row("q_2077").trigger("click");
    expect(wrapper.emitted("select")).toEqual([["q_2077"]]);
    expect(row("q_2077").attributes("aria-selected")).toBe("true");
  });

  it("moves focus with the arrows without selecting, and Enter selects", async () => {
    mountList();
    row("q_1042").element.focus();
    await press("ArrowDown");
    expect(focusedId()).toBe("q_2077");
    expect(wrapper.emitted("select")).toBeUndefined();
    await press("Enter");
    expect(wrapper.emitted("select")).toEqual([["q_2077"]]);
    await press("End");
    expect(focusedId()).toBe("q_3000");
    // No wraparound at either end.
    await press("ArrowDown");
    expect(focusedId()).toBe("q_3000");
    await press("Home");
    expect(focusedId()).toBe("q_1042");
    await press("ArrowUp");
    expect(focusedId()).toBe("q_1042");
    await press(" ");
    expect(wrapper.emitted("select")).toEqual([["q_2077"], ["q_1042"]]);
  });

  it("keeps a tab stop on the first row when nothing is selected", () => {
    mountList({ selectedId: null });
    expect(tabindexes()).toEqual(["0", "-1", "-1"]);
    expect(wrapper.findAll('[aria-selected="true"]')).toHaveLength(0);
  });

  it("shows the shared empty guidance for an empty state", () => {
    mountList({ rows: [], selectedId: null, emptyGuidance: "達成的委託會列在這裡。" });
    const empty = wrapper.get('[data-testid="quest-drawer__empty"]');
    expect(empty.classes()).toContain("empty-state");
    expect(empty.get(".empty-state__headline").text()).toBe("這裡還沒有任務。");
    expect(empty.get(".empty-state__guidance").text()).toBe("達成的委託會列在這裡。");
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="quest-drawer__list-count"]').text()).toBe("0");
  });

  it("shows the fixed absent line before the first commit", () => {
    mountList({ rows: [], selectedId: null, status: "absent" });
    expect(wrapper.get('[data-testid="quest-drawer__absent"]').text()).toBe("尚未取得任務簿資料");
    expect(wrapper.find('[data-testid="quest-drawer__empty"]').exists()).toBe(false);
    expect(wrapper.findAll('[role="option"]')).toHaveLength(0);
  });

  it("shows the unavailable reason with its code and no rows", () => {
    mountList({ rows: THREE, status: "unavailable", reason: QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE.reason });
    const reason = wrapper.get('[data-testid="quest-drawer__unavailable"]');
    expect(reason.text()).toBe("任務簿目前無法顯示");
    expect(reason.attributes("data-reason-code")).toBe("quest_log_unavailable");
    expect(wrapper.findAll('[role="option"]')).toHaveLength(0);
    expect(wrapper.find('[data-testid="quest-drawer__empty"]').exists()).toBe(false);
  });
});
