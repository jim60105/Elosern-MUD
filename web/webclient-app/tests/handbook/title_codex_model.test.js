import { describe, expect, it } from "vitest";
import {
  TITLE_CATEGORIES,
  defaultTitleRail,
  defaultTitleSelection,
  guildGrade,
  medalItems,
  titleCodexStatus,
  titleDetail,
  titleFooter,
  titleIntent,
  titleListRows,
  titleRail,
} from "../../components/handbook/title-codex-model.js";
import { BALLOT, UNAVAILABLE_CODEX, fixedRow, titleCodex } from "../../stories/fixtures/title_codex_panels.js";

const keys = (buttons) => buttons.map((button) => button.key);

describe("title-codex-model (handbook-titles-tab)", () => {
  it("reads the panel status", () => {
    expect(titleCodexStatus(null)).toBe("absent");
    expect(titleCodexStatus(UNAVAILABLE_CODEX)).toBe("unavailable");
    expect(titleCodexStatus(titleCodex())).toBe("available");
  });

  it("orders the rail by the closed categories, then the epithet entry, with unlocked counts", () => {
    const rail = titleRail(titleCodex());
    expect(rail.map((entry) => entry.key)).toEqual([...TITLE_CATEGORIES.map((c) => c.key), "epithet"]);
    // combat holds three rows of which one is unlocked.
    expect(rail.find((entry) => entry.key === "combat").count).toBe(1);
    expect(rail.find((entry) => entry.key === "guild").count).toBe(1);
    expect(rail.find((entry) => entry.key === "spell").count).toBe(0);
    expect(rail.find((entry) => entry.key === "epithet").count).toBe(2);
    expect(titleRail(null)).toEqual([]);
    expect(titleRail(UNAVAILABLE_CODEX)).toEqual([]);
  });

  it("adds a hot ballot entry only while a ballot is pending", () => {
    const rail = titleRail(titleCodex({ pending_ballot: BALLOT }));
    expect(rail.at(-1)).toMatchObject({ key: "ballot", count: 2, hot: true });
    expect(titleRail(titleCodex()).some((entry) => entry.key === "ballot")).toBe(false);
  });

  it("defaults the rail to the first category holding an unlocked row, else the first category", () => {
    expect(defaultTitleRail(titleCodex())).toBe("combat");
    const guildOnly = titleCodex({ fixed_rows: [fixedRow({ key: "t_x", category: "guild" })] });
    expect(defaultTitleRail(guildOnly)).toBe("guild");
    const allLocked = titleCodex({ fixed_rows: [fixedRow({ key: "t_y", category: "clergy", unlocked: false, flavor: "", hint: "合成條件" })] });
    expect(defaultTitleRail(allLocked)).toBe("combat");
    expect(defaultTitleRail(null)).toBe("combat");
  });

  it("reads a guild grade only from a guild row whose key matches the grade grammar", () => {
    expect(guildGrade({ category: "guild", key: "g_x_rank" })).toBe("X");
    expect(guildGrade({ category: "guild", key: "g_q_rank" })).toBe("Q");
    expect(guildGrade({ category: "guild", key: "t_guild_odd" })).toBeNull();
    expect(guildGrade({ category: "guild", key: "g_xy_rank" })).toBeNull();
    expect(guildGrade({ category: "combat", key: "g_x_rank" })).toBeNull();
  });

  it("builds medal items in payload order with lock, equip and grade marks", () => {
    const items = medalItems(titleCodex(), "combat");
    expect(items.map((item) => item.id)).toEqual(["t_alpha", "t_beta", "t_gamma"]);
    expect(items[0]).toMatchObject({ selectable: true, locked: false, equipped: true, grade: null });
    expect(items[1]).toMatchObject({ locked: true, equipped: false });
    expect(medalItems(titleCodex(), "guild")[0].grade).toBe("X");
    expect(medalItems(titleCodex(), "epithet")).toEqual([]);
  });

  it("builds list rows for epithets and nominees", () => {
    const rows = titleListRows(titleCodex(), "epithet");
    expect(rows.map((row) => row.id)).toEqual(["合成異名甲", "合成異名乙"]);
    expect(rows[0].sub).toBe("合成事蹟甲。");
    expect(rows[1].sub).toBe("★ 裝備中・合成事蹟乙。");
    expect(titleListRows(titleCodex({ pending_ballot: BALLOT }), "ballot").map((row) => row.id)).toEqual([
      "合成提名甲",
      "合成提名乙",
    ]);
    expect(titleListRows(titleCodex(), "combat")).toEqual([]);
  });

  it("defaults the selection to the first unlocked fixed row, else the first row", () => {
    expect(defaultTitleSelection(titleCodex(), "combat")).toBe("t_alpha");
    const lockedFirst = titleCodex({
      fixed_rows: [
        fixedRow({ key: "t_l", unlocked: false, flavor: "", hint: "合成條件" }),
        fixedRow({ key: "t_u" }),
      ],
    });
    expect(defaultTitleSelection(lockedFirst, "combat")).toBe("t_u");
    expect(defaultTitleSelection(titleCodex(), "epithet")).toBe("合成異名甲");
    expect(defaultTitleSelection(titleCodex(), "spell")).toBeNull();
  });

  it("details a locked row with its display and hint verbatim", () => {
    const detail = titleDetail(titleCodex(), "combat", "t_beta");
    expect(detail).toMatchObject({ kind: "fixed", name: "乙稱號", locked: true, stamp: { kind: "locked" } });
    expect(detail.sections).toEqual([{ label: "取得條件", text: "完成合成條件乙。" }]);
    expect(titleDetail(titleCodex(), "combat", "t_none")).toBeNull();
  });

  it("disables equip for a locked row and for the equipped row", () => {
    const locked = titleFooter(titleDetail(titleCodex(), "combat", "t_beta"));
    expect(locked.buttons[0]).toMatchObject({ key: "equip", enabled: false });
    expect(locked.reason).toBeTruthy();
    const equipped = titleFooter(titleDetail(titleCodex(), "combat", "t_alpha"));
    expect(equipped.buttons[0]).toMatchObject({ key: "equip", enabled: false });
    expect(equipped.reason).toBeTruthy();
    const free = titleFooter(titleDetail(titleCodex(), "guild", "g_x_rank"));
    expect(free.buttons[0]).toMatchObject({ key: "equip", enabled: true });
    const equippedEpithet = titleFooter(titleDetail(titleCodex(), "epithet", "合成異名乙"));
    expect(keys(equippedEpithet.buttons)).toEqual(["equip"]);
    expect(equippedEpithet.buttons[0].enabled).toBe(false);
  });

  it("offers removal only from the flag, and the armed confirmation only for a removable epithet", () => {
    const removable = titleDetail(titleCodex(), "epithet", "合成異名甲");
    expect(keys(titleFooter(removable).buttons)).toEqual(["remove", "equip"]);
    const armed = titleFooter(removable, { armed: true });
    expect(keys(armed.buttons)).toEqual(["cancel", "confirm-remove"]);
    expect(armed).toMatchObject({ reasonTone: "danger", reasonRole: "alert" });
    const fixed = titleDetail(titleCodex(), "guild", "g_x_rank");
    expect(keys(titleFooter(fixed, { armed: true }).buttons)).toEqual(["equip"]);
  });

  it("offers decline and accept for a nominee", () => {
    const detail = titleDetail(titleCodex({ pending_ballot: BALLOT }), "ballot", "合成提名乙");
    expect(detail.index).toBe(1);
    expect(keys(titleFooter(detail).buttons)).toEqual(["decline", "accept"]);
  });

  it("builds the exact intents and none for a disabled equip", () => {
    const codex = titleCodex({ pending_ballot: BALLOT });
    expect(titleIntent(titleDetail(codex, "guild", "g_x_rank"), "equip")).toEqual({
      action_id: "title.equip",
      payload: { kind: "fixed", identifier: "g_x_rank" },
    });
    expect(titleIntent(titleDetail(codex, "epithet", "合成異名甲"), "equip")).toEqual({
      action_id: "title.equip",
      payload: { kind: "epithet", identifier: "合成異名甲" },
    });
    expect(titleIntent(titleDetail(codex, "epithet", "合成異名甲"), "confirm-remove")).toEqual({
      action_id: "title.remove",
      payload: { display: "合成異名甲" },
    });
    expect(titleIntent(titleDetail(codex, "ballot", "合成提名乙"), "accept")).toEqual({
      action_id: "title.accept",
      payload: { index: 2 },
    });
    expect(titleIntent(titleDetail(codex, "ballot", "合成提名甲"), "decline")).toEqual({
      action_id: "title.decline",
      payload: {},
    });
    expect(titleIntent(titleDetail(codex, "combat", "t_beta"), "equip")).toBeNull();
    expect(titleIntent(titleDetail(codex, "combat", "t_alpha"), "equip")).toBeNull();
    expect(titleIntent(titleDetail(codex, "epithet", "合成異名乙"), "confirm-remove")).toBeNull();
    expect(titleIntent(null, "equip")).toBeNull();
  });
});
