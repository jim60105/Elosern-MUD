import { afterEach, describe, expect, it } from "vitest";
import {
  ABANDON_WARNING,
  BOOK_STATES,
  COUNTER_CLERK_REASON,
  bookActions,
  bookDetail,
  bookListRow,
  bookStatus,
  counterRowsById,
  counterTab,
  rowsByState,
  stateCounts,
  turninHot,
} from "../../components/quest-drawer-model.js";
import {
  resetQuestDrawerMemory,
  useQuestDrawerMemory,
} from "../../components/quest-drawer-memory.js";
import {
  QUEST_LOG_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_SAMPLE,
  QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

const rowById = (id) => QUEST_LOG_PANEL_SAMPLE.rows.find((row) => row.quest_id === id);
const descriptor = (action_id, label, enabled = true, message = null) => ({
  action_id,
  label,
  enabled,
  disabled_reason: enabled ? null : { code: "x", message },
  quantity: null,
});
const counterRow = (quest_id, overrides = {}) => ({
  quest_id,
  abandon: descriptor("guild.quest_abandon", "放棄任務"),
  turnin: descriptor("guild.quest_turnin", "交派任務", false, "任務目標尚未完成"),
  ...overrides,
});
const servicesWith = (quests) => ({
  ...SERVICES_PANEL_SAMPLE,
  guild: { ...SERVICES_PANEL_SAMPLE.guild, quests },
});

describe("quest-drawer-model: grouping and counts", () => {
  it("classifies the book's commit state", () => {
    expect(bookStatus(null)).toBe("absent");
    expect(bookStatus(QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE)).toBe("unavailable");
    expect(bookStatus(QUEST_LOG_PANEL_EMPTY_SAMPLE)).toBe("available");
  });

  it("groups rows by state in panel order and counts them", () => {
    const rows = [
      { quest_id: "a", state: "completed" },
      { quest_id: "b", state: "in_progress" },
      { quest_id: "c", state: "in_progress" },
      { quest_id: "d", state: "failed" },
      { quest_id: "e", state: "in_progress" },
      { quest_id: "f", state: "completed" },
    ];
    const groups = rowsByState({ schema_version: 2, available: true, rows });
    expect(BOOK_STATES.map((state) => state.key)).toEqual(["in_progress", "completed", "failed"]);
    expect(groups.in_progress.map((row) => row.quest_id)).toEqual(["b", "c", "e"]);
    expect(groups.completed.map((row) => row.quest_id)).toEqual(["a", "f"]);
    expect(stateCounts(groups)).toEqual({ in_progress: 3, completed: 2, failed: 1 });
  });

  it("lists no row for an absent or unavailable book", () => {
    for (const panel of [null, QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE]) {
      expect(stateCounts(rowsByState(panel))).toEqual({ in_progress: 0, completed: 0, failed: 0 });
    }
  });
});

describe("quest-drawer-model: the counter merge", () => {
  it("joins counter rows by quest_id only", () => {
    const rows = counterRowsById(SERVICES_PANEL_SAMPLE);
    expect([...rows.keys()]).toEqual(["q_1042"]);
    // The counter row's definition key differs from the book row's; only the
    // quest_id joins them.
    expect(rows.get("q_1042").definition_key).not.toBe(rowById("q_1042").definition_key);
  });

  it("yields no counter rows for an unavailable, guild-less, or missing services panel", () => {
    for (const services of [null, SERVICES_PANEL_UNAVAILABLE_SAMPLE, SERVICES_PANEL_MINIMAL_SAMPLE]) {
      expect(counterRowsById(services).size).toBe(0);
    }
  });

  it("marks the completed count hot only for an enabled matched turn-in", () => {
    const groups = rowsByState(QUEST_LOG_PANEL_SAMPLE);
    const enabled = counterRowsById(servicesWith([counterRow("q_0301", { turnin: descriptor("guild.quest_turnin", "交派任務") })]));
    expect(turninHot(groups, enabled)).toBe(true);
    const disabled = counterRowsById(servicesWith([counterRow("q_0301")]));
    expect(turninHot(groups, disabled)).toBe(false);
    // An enabled turn-in on an in-progress row never heats the completed tab.
    const inProgress = counterRowsById(servicesWith([counterRow("q_1042", { turnin: descriptor("guild.quest_turnin", "交派任務") })]));
    expect(turninHot(groups, inProgress)).toBe(false);
    expect(turninHot(groups, counterRowsById(SERVICES_PANEL_MINIMAL_SAMPLE))).toBe(false);
  });

  it("enables the counter tab only with a usable guild section", () => {
    expect(counterTab(SERVICES_PANEL_SAMPLE)).toEqual({ enabled: true, reason: null, reasonCode: null });
    expect(counterTab(SERVICES_PANEL_UNAVAILABLE_SAMPLE)).toEqual({
      enabled: false,
      reason: SERVICES_PANEL_UNAVAILABLE_SAMPLE.reason.message,
      reasonCode: "services_unavailable",
    });
    expect(counterTab(SERVICES_PANEL_MINIMAL_SAMPLE)).toEqual({ enabled: false, reason: COUNTER_CLERK_REASON, reasonCode: null });
    expect(counterTab(null).enabled).toBe(false);
  });
});

describe("quest-drawer-model: list rows", () => {
  it("shows progress for an in-progress row and the issuer line otherwise", () => {
    expect(bookListRow(rowById("q_1042"))).toEqual({
      id: "q_1042",
      name: "驅除東部平原穗鳴雀",
      state: "in_progress",
      glyph: "cat_defeat",
      tracked: true,
      grade: "F",
      progress: { value: 1, target: 2, pct: 50 },
      sub: null,
    });
    const failed = bookListRow(rowById("q_0099"));
    expect(failed.progress).toBeNull();
    expect(failed.sub).toBe("公會委託 · 期限：已逾期");
    expect(bookListRow({ ...rowById("q_2077"), state: "completed" }).sub).toBe("守塔人");
  });

  it("never reports a terminal row as tracked and guards a zero target", () => {
    expect(bookListRow({ ...rowById("q_1042"), state: "completed" }).tracked).toBe(false);
    expect(bookListRow({ ...rowById("q_1042"), objective_quantity: 0 }).progress.pct).toBe(0);
    expect(bookListRow({ ...rowById("q_1042"), stage_progress: 9 }).progress.pct).toBe(100);
  });
});

describe("quest-drawer-model: the detail view model", () => {
  it("numbers stages from one and picks pips up to twelve", () => {
    const detail = bookDetail({ ...rowById("q_1042"), stage_index: 0, stage_total: 1 });
    expect(detail.progress).toMatchObject({ stage: 1, stages: 1, value: 1, target: 2, mode: "pips" });
    expect(bookDetail({ ...rowById("q_1042"), objective_quantity: 12 }).progress.mode).toBe("pips");
    expect(bookDetail({ ...rowById("q_1042"), objective_quantity: 13, stage_progress: 13 }).progress).toMatchObject({
      mode: "bar",
      pct: 100,
    });
    expect(bookDetail(rowById("q_0301")).progress).toBeNull();
  });

  it("builds the ribbon from the category and the issuer kind", () => {
    expect(bookDetail(rowById("q_1042")).ribbon).toEqual({ glyph: "cat_defeat", label: "討伐委託" });
    expect(bookDetail(rowById("q_2077")).ribbon).toEqual({ glyph: "cat_gather", label: "採集 · 私人委託" });
  });

  it("stamps completed and failed rows only", () => {
    expect(bookDetail(rowById("q_1042")).stamp).toBeNull();
    expect(bookDetail(rowById("q_0301")).stamp).toEqual({ kind: "completed", label: "達成" });
    expect(bookDetail(rowById("q_0099")).stamp).toEqual({ kind: "failed", label: "失敗" });
  });

  it("keeps null prose honest", () => {
    const detail = bookDetail({ ...rowById("q_1042"), rationale: null, flavor: null, deadline_line: null });
    expect(detail.rationale).toBeNull();
    expect(detail.issuer).toMatchObject({ letter: null, fallback: "委託人沒有留下說明。" });
    expect(detail.deadline).toEqual({ line: "無期限", note: "這份委託沒有時間限制。", open: true });
    const withProse = bookDetail(rowById("q_1042"));
    expect(withProse.rationale).toBe(rowById("q_1042").rationale);
    expect(withProse.issuer).toMatchObject({ letter: rowById("q_1042").flavor, fallback: null });
    // The deadline prose renders verbatim.
    expect(withProse.deadline.line).toBe("期限：剩餘 48 小時");
    expect(withProse.objective).toBe(rowById("q_1042").objective_line);
    expect(withProse.note).toBe("計數變體：領群型、啄穗型");
  });

  it("lists reward cells, omitting zero merit, with the settlement note", () => {
    const [item] = rowById("q_1042").reward.items;
    expect(bookDetail(rowById("q_1042")).reward).toEqual({
      cells: [
        { kind: "copper", glyph: "reward_copper", value: 40, unit: "銅" },
        { kind: "merit", glyph: "reward_merit", value: 20, unit: "功績" },
        { kind: "item", glyph: "reward_item", key: item.item_key, name: item.display_name, quantity: item.quantity },
      ],
      settlement: "回公會櫃檯領取",
    });
    expect(bookDetail(rowById("q_2077")).reward).toEqual({
      cells: [{ kind: "copper", glyph: "reward_copper", value: 220, unit: "銅" }],
      settlement: "完成即結算",
    });
  });

  it("omits the reward section for a null reward", () => {
    expect(bookDetail(rowById("q_0099")).reward).toBeNull();
  });
});

describe("quest-drawer-model: the action bar", () => {
  const inProgress = rowById("q_1042");
  const completed = rowById("q_0301");

  it("tracks an in-progress row from its own descriptor, toggling the stored flag", () => {
    const tracked = bookActions(inProgress, null).track;
    expect(tracked).toMatchObject({
      enabled: true,
      pressed: true,
      label: "追蹤中",
      action_id: "guild.quest_track",
      payload: { quest_id: "q_1042", tracked: false },
    });
    const untracked = bookActions({ ...inProgress, tracked: false }, null).track;
    expect(untracked).toMatchObject({ pressed: false, label: "追蹤", payload: { quest_id: "q_1042", tracked: true } });
  });

  it("mirrors an enabled abandon and drops it away from the counter", () => {
    expect(bookActions(inProgress, counterRow("q_1042")).abandon).toEqual({
      action_id: "guild.quest_abandon",
      label: "放棄任務",
      payload: { quest_id: "q_1042" },
    });
    const away = bookActions(inProgress, null);
    expect(away.abandon).toBeNull();
    expect(away.turnin).toBeNull();
    expect(away.reason).toBeNull();
  });

  it("shows a disabled abandon's reason instead of a control", () => {
    const actions = bookActions(inProgress, counterRow("q_1042", { abandon: descriptor("guild.quest_abandon", "放棄任務", false, "櫃台忙碌中") }));
    expect(actions.abandon).toBeNull();
    expect(actions.reason).toBe("櫃台忙碌中");
  });

  it("offers an enabled turn-in on a completed row and no tracking", () => {
    const actions = bookActions(completed, counterRow("q_0301", { turnin: descriptor("guild.quest_turnin", "交派任務") }));
    expect(actions.track).toBeNull();
    expect(actions.abandon).toBeNull();
    expect(actions.turnin).toEqual({ action_id: "guild.quest_turnin", label: "交派任務", payload: { quest_id: "q_0301" } });
    expect(actions.reason).toBeNull();
  });

  it("states the counter's disabled reason before any client line", () => {
    const actions = bookActions(
      { ...completed, reward_claimed: true },
      counterRow("q_0301", { turnin: descriptor("guild.quest_turnin", "交派任務", false, "報酬已於先前領取") }),
    );
    expect(actions.turnin).toBeNull();
    expect(actions.reason).toBe("報酬已於先前領取");
  });

  it("says 報酬已領取 for a claimed reward away from the counter", () => {
    expect(bookActions({ ...completed, reward_claimed: true }, null).reason).toBe("報酬已領取");
  });

  it("points a pending counter reward back to the counter", () => {
    expect(bookActions(completed, null).reason).toBe("回到公會櫃檯即可交付並領取報酬。");
  });

  it("invents no line for an unclaimed auto settlement or a null reward", () => {
    expect(bookActions({ ...completed, settlement: "auto" }, null).reason).toBeNull();
    expect(bookActions({ ...completed, settlement: null, reward: null }, null).reason).toBeNull();
    // The counter hint never promises a reward the row does not carry.
    expect(bookActions({ ...completed, reward: null }, null).reason).toBeNull();
    expect(bookActions({ ...completed, reward_claimed: undefined }, null).reason).toBeNull();
    expect(bookActions({ ...completed, settlement: "auto", reward_claimed: true }, null).reason).toBe("報酬已領取");
  });

  it("states that a failed quest pays nothing and offers no tracking", () => {
    const actions = bookActions(rowById("q_0099"), counterRow("q_0099"));
    expect(actions).toEqual({ track: null, abandon: null, turnin: null, reason: "此委託已失敗，沒有報酬。" });
  });

  it("names the quest in the abandon warning", () => {
    expect(ABANDON_WARNING("磨坊糧運")).toBe("放棄「磨坊糧運」後任務會判定失敗，且無法回復。");
  });
});

describe("quest-drawer-memory", () => {
  afterEach(() => resetQuestDrawerMemory());

  it("keeps memory within one scope and resets it on a new scope", () => {
    const memory = useQuestDrawerMemory("1|7");
    memory.top = "counter";
    memory.selectedByTab["book:in_progress"] = "q_2077";
    expect(useQuestDrawerMemory("1|7").top).toBe("counter");
    const fresh = useQuestDrawerMemory("2|7");
    expect(fresh.top).toBe("book");
    expect(fresh.bookState).toBe("in_progress");
    expect(fresh.selectedByTab).toEqual({});
  });
});
