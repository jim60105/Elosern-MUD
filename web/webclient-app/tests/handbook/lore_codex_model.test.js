import { describe, expect, it } from "vitest";
import {
  MONSTER_CATEGORY,
  codexDetail,
  codexFieldLabel,
  codexGroups,
  codexRail,
  defaultCodexCategory,
  firstEntryKey,
  loreCodexStatus,
} from "../../components/handbook/lore-codex-model.js";
import { CODEX_PLACEHOLDER, codexCategory, codexEntry, loreCodex } from "../../stories/fixtures/lore_codex_panels.js";

// Synthetic panel: an empty first category, a plain category with one null
// label group, and the monster wall (the model-owned wire key) with two tiers.
const SIGHTED = codexEntry("k_sighted", "合成目擊", {
  stage: "sighted",
  card: [
    { name: "display_name_zh", value: "合成目擊" },
    { name: "published_appearance_zh", value: "合成外觀。" },
    { name: "threat_tier", value: "合成階" },
  ],
  locked_fields: ["published_description_zh", "published_ecology_zh", "habitat_tags", "variants"],
});
const DEFEATED = codexEntry("k_defeated", "合成擊敗", {
  stage: "defeated",
  card: [
    { name: "display_name_zh", value: "合成擊敗" },
    { name: "published_ecology_zh", value: "合成生態。" },
    { name: "x_unknown_field", value: "合成未知值。" },
  ],
});
const panel = () =>
  loreCodex([
    codexCategory("cat_empty", "空類", [{ key: "cat_empty", label: null, slots: [CODEX_PLACEHOLDER] }]),
    codexCategory("cat_plain", "平類", [
      { key: "cat_plain", label: null, slots: [CODEX_PLACEHOLDER, codexEntry("k_plain", "合成平條目"), CODEX_PLACEHOLDER] },
    ]),
    codexCategory(MONSTER_CATEGORY, "獸類", [
      { key: "tier_a", label: "甲階", slots: [SIGHTED, CODEX_PLACEHOLDER] },
      { key: "tier_b", label: "乙階", slots: [CODEX_PLACEHOLDER, DEFEATED] },
    ]),
  ]);

describe("lore-codex-model (handbook-codex-tab)", () => {
  it("reports absent, unavailable and available", () => {
    expect(loreCodexStatus(null)).toBe("absent");
    expect(loreCodexStatus({ available: false, reason: { code: "x", message: "y" } })).toBe("unavailable");
    expect(loreCodexStatus(panel())).toBe("available");
  });

  it("builds the rail in panel order with discovered counts", () => {
    expect(codexRail(panel())).toEqual([
      { key: "cat_empty", label: "空類", count: 0 },
      { key: "cat_plain", label: "平類", count: 1 },
      { key: MONSTER_CATEGORY, label: "獸類", count: 2 },
    ]);
    expect(codexRail(null)).toEqual([]);
  });

  it("defaults to the first category with a discovery, else the first, else null", () => {
    expect(defaultCodexCategory(panel())).toBe("cat_plain");
    const none = loreCodex([
      codexCategory("cat_x", "甲", [{ key: "g", label: null, slots: [CODEX_PLACEHOLDER] }]),
      codexCategory("cat_y", "乙", [{ key: "g", label: null, slots: [] }]),
    ]);
    expect(defaultCodexCategory(none)).toBe("cat_x");
    expect(defaultCodexCategory(null)).toBeNull();
  });

  it("keeps group order and null labels, and identity-free unique placeholders", () => {
    const groups = codexGroups(panel(), MONSTER_CATEGORY);
    expect(groups.map((group) => [group.key, group.label])).toEqual([
      ["tier_a", "甲階"],
      ["tier_b", "乙階"],
    ]);
    expect(codexGroups(panel(), "cat_plain")[0].label).toBeNull();
    const placeholders = groups.flatMap((group) => group.items).filter((item) => item.placeholder);
    expect(placeholders).toEqual([
      { id: "p:tier_a:1", selectable: false, label: "未記錄", placeholder: true },
      { id: "p:tier_b:0", selectable: false, label: "未記錄", placeholder: true },
    ]);
    const plainIds = codexGroups(panel(), "cat_plain")[0].items.map((item) => item.id);
    expect(new Set(plainIds).size).toBe(plainIds.length);
  });

  it("labels entry items with the title and the stage suffix", () => {
    const items = codexGroups(panel(), MONSTER_CATEGORY).flatMap((group) => group.items);
    expect(items.map((item) => item.label)).toEqual(["合成目擊，已目擊", "未記錄", "未記錄", "合成擊敗，已擊敗"]);
    const plain = codexGroups(panel(), "cat_plain")[0].items[1];
    expect(plain).toMatchObject({ id: "k_plain", selectable: true, label: "合成平條目", stage: null, art: null });
  });

  it("finds the first entry key per category", () => {
    expect(firstEntryKey(panel(), MONSTER_CATEGORY)).toBe("k_sighted");
    expect(firstEntryKey(panel(), "cat_empty")).toBeNull();
    expect(firstEntryKey(panel(), "missing")).toBeNull();
  });

  it("renders the card without the title field under readable names", () => {
    const detail = codexDetail(panel(), MONSTER_CATEGORY, "k_defeated");
    expect(detail).toMatchObject({
      kind: "codex",
      id: "k_defeated",
      category: MONSTER_CATEGORY,
      name: "合成擊敗",
      ribbon: "獸類",
      emblem: MONSTER_CATEGORY,
      stage: "defeated",
      stamp: { kind: "defeated", label: "已擊敗" },
      locked: [],
    });
    expect(detail.fields).toEqual([
      { name: "published_ecology_zh", label: "生態", value: "合成生態。" },
      { name: "x_unknown_field", label: "資料", value: "合成未知值。" },
    ]);
    expect(codexFieldLabel("x_unknown_field")).toBe("資料");
  });

  it("lists the locked fields and derives the sighted track's unlocks from them", () => {
    const detail = codexDetail(panel(), MONSTER_CATEGORY, "k_sighted");
    expect(detail.stamp).toEqual({ kind: "sighted", label: "目擊" });
    expect(detail.locked.map((item) => item.name)).toEqual(SIGHTED.locked_fields);
    expect(detail.locked.every((item) => item.label && item.label !== item.name)).toBe(true);
    expect(detail.track).toEqual([
      { key: "sighted", label: "目擊", unlocks: null, reached: true },
      { key: "defeated", label: "擊敗", unlocks: detail.locked.map((item) => item.label).join("・"), reached: false },
    ]);
    const defeated = codexDetail(panel(), MONSTER_CATEGORY, "k_defeated");
    expect(defeated.track.map((step) => step.reached)).toEqual([true, true]);
    expect(defeated.track[1].unlocks).toBeNull();
  });

  it("gives a stageless entry no stamp and no track", () => {
    const detail = codexDetail(panel(), "cat_plain", "k_plain");
    expect(detail.stamp).toBeNull();
    expect(detail.track).toBeNull();
    expect(detail.fields.map((field) => field.name)).toEqual(["description"]);
  });

  it("returns null for an unknown key or category", () => {
    expect(codexDetail(panel(), MONSTER_CATEGORY, "nope")).toBeNull();
    expect(codexDetail(panel(), "missing", "k_plain")).toBeNull();
    expect(codexDetail(null, MONSTER_CATEGORY, "k_sighted")).toBeNull();
  });
});
