import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import LoreCodexTab from "../../components/handbook/LoreCodexTab.vue";
import { MONSTER_CATEGORY } from "../../components/handbook/lore-codex-model.js";
import { resetQuestDrawerMemory, useQuestDrawerMemory } from "../../components/quest-drawer-memory.js";
import { CODEX_PLACEHOLDER, codexArt, codexCategory, codexEntry, loreCodex } from "../../stories/fixtures/lore_codex_panels.js";

// A synthetic v2 panel: a plain category with two entries and a placeholder,
// a category with nothing discovered, and the monster wall.
const ENTRY_A = codexEntry("k_a", "合成甲", {
  card: [
    { name: "display_name_zh", value: "合成甲" },
    { name: "description", value: "合成甲的記述。" },
    { name: "x_unknown_field", value: "合成甲的未知值。" },
  ],
});
const ENTRY_B = codexEntry("k_b", "合成乙", { art: codexArt("subject:b", "/art/synthetic/b.webp") });
const MONSTER = codexEntry("k_m", "合成獸", { stage: "sighted", locked_fields: ["field_one"] });
const panelWith = (plainSlots = [ENTRY_A, CODEX_PLACEHOLDER, ENTRY_B]) =>
  loreCodex([
    codexCategory("cat_plain", "平類", [{ key: "cat_plain", label: null, slots: plainSlots }]),
    codexCategory("cat_none", "空類", [{ key: "cat_none", label: null, slots: [CODEX_PLACEHOLDER, CODEX_PLACEHOLDER] }]),
    codexCategory(MONSTER_CATEGORY, "獸類", [{ key: "tier", label: "甲階", slots: [MONSTER, CODEX_PLACEHOLDER] }]),
  ]);
const NOTHING = loreCodex([
  codexCategory("cat_x", "甲類", [{ key: "cat_x", label: null, slots: [CODEX_PLACEHOLDER, CODEX_PLACEHOLDER] }]),
  codexCategory(MONSTER_CATEGORY, "獸類", [{ key: "tier", label: "甲階", slots: [CODEX_PLACEHOLDER] }]),
]);

describe("LoreCodexTab (handbook-codex-tab)", () => {
  let wrapper;

  beforeEach(() => resetQuestDrawerMemory());

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountTab(codex = panelWith(), props = {}) {
    wrapper = mount(LoreCodexTab, { attachTo: document.body, props: { codex, memoryScope: "1|1", ...props } });
    return wrapper;
  }

  const find = (id) => wrapper.find(`[data-testid="handbook__${id}"]`);
  const railTab = (key) => wrapper.get(`[data-testid="handbook__codex-rail"] [data-tab-key="${key}"]`);
  const railKeys = () =>
    wrapper.findAll('[data-testid="handbook__codex-rail"] [role="tab"]').map((tab) => tab.attributes("data-tab-key"));
  const tiles = () => wrapper.findAll('[data-testid="tile-wall"] [role="option"]').map((cell) => cell.attributes("data-tile"));
  const detailId = () => find("detail").attributes("data-detail-id");

  it("lists every shipped category in panel order with its discovered count", () => {
    mountTab();
    expect(railKeys()).toEqual(["cat_plain", "cat_none", MONSTER_CATEGORY]);
    expect(railTab("cat_plain").attributes("aria-label")).toBe("平類（2）");
    expect(railTab("cat_none").attributes("aria-label")).toBe("空類（0）");
  });

  it("shows exactly the selected category's slots and dispatches nothing", async () => {
    mountTab();
    expect(tiles()).toEqual(["k_a", "p:cat_plain:1", "k_b"]);
    await railTab(MONSTER_CATEGORY).trigger("click");
    expect(tiles()).toEqual(["k_m", "p:tier:1"]);
    expect(find("codex-legend").exists()).toBe(true);
    expect(Object.keys(wrapper.emitted())).not.toContain("action");
    expect(wrapper.emitted("action")).toBeUndefined();
  });

  it("renders the card verbatim under readable names, without the title field", () => {
    mountTab();
    expect(detailId()).toBe("k_a");
    expect(find("detail").get("h3").text()).toBe("合成甲");
    const sections = wrapper.findAll('[data-testid="handbook__section"]');
    expect(sections.map((section) => [section.get("h4").text(), section.get("p").text()])).toEqual([
      ["描述", "合成甲的記述。"],
      ["資料", "合成甲的未知值。"],
    ]);
    const text = find("detail").text();
    for (const raw of ["display_name_zh", "description", "x_unknown_field"]) expect(text).not.toContain(raw);
    expect(find("actions").exists()).toBe(false);
  });

  it("remembers the selection per category within the memory scope", async () => {
    mountTab();
    await wrapper.get('[data-tile="k_b"]').trigger("click");
    expect(detailId()).toBe("k_b");
    await railTab(MONSTER_CATEGORY).trigger("click");
    expect(detailId()).toBe("k_m");
    await railTab("cat_plain").trigger("click");
    expect(detailId()).toBe("k_b");
    expect(useQuestDrawerMemory("1|1").codexCategory).toBe("cat_plain");
    wrapper.unmount();
    mountTab();
    expect(detailId()).toBe("k_b");
  });

  it("shows the hero emblem for a null art and the image for an entry with art", async () => {
    mountTab();
    expect(find("detail").find('[data-testid="handbook__art-emblem"]').exists()).toBe(true);
    expect(find("detail").find("img").exists()).toBe(false);
    await wrapper.get('[data-tile="k_b"]').trigger("click");
    expect(find("detail").get("img").attributes("src")).toBe("/art/synthetic/b.webp");
  });

  it("shows the shared empty state and no tile before the first commit", () => {
    mountTab(null);
    expect(find("codex-absent").classes()).toContain("empty-state");
    expect(wrapper.find('[data-testid="tile-wall"]').exists()).toBe(false);
    expect(find("codex-rail").exists()).toBe(false);
  });

  it("states the unavailable panel's reason", () => {
    mountTab({ schema_version: 2, available: false, reason: { code: "x_code", message: "合成的圖鑑不可用原因" } });
    expect(find("codex-unavailable").text()).toContain("合成的圖鑑不可用原因");
    expect(wrapper.find('[data-testid="tile-wall"]').exists()).toBe(false);
  });

  it("renders the full placeholder wall and the empty guidance when nothing is discovered", async () => {
    mountTab(NOTHING);
    expect(tiles()).toEqual(["p:cat_x:0", "p:cat_x:1"]);
    expect(find("detail").exists()).toBe(false);
    const empty = find("codex-empty");
    expect(empty.classes()).toContain("empty-state");
    expect(empty.text()).toContain("尚無記錄");
    await railTab(MONSTER_CATEGORY).trigger("click");
    expect(tiles()).toEqual(["p:tier:0"]);
    expect(find("codex-empty").exists()).toBe(true);
  });

  it("falls back to the category's first entry, then to the empty detail, when the selection vanishes", async () => {
    mountTab();
    await wrapper.get('[data-tile="k_b"]').trigger("click");
    expect(detailId()).toBe("k_b");
    await wrapper.setProps({ codex: panelWith([ENTRY_A, CODEX_PLACEHOLDER, CODEX_PLACEHOLDER]) });
    expect(detailId()).toBe("k_a");
    await wrapper.setProps({ codex: panelWith([CODEX_PLACEHOLDER]) });
    // The remembered category stays; it now has no entry.
    useQuestDrawerMemory("1|1").codexCategory = "cat_plain";
    await nextTick();
    expect(find("detail").exists()).toBe(false);
    expect(find("codex-empty").exists()).toBe(true);
  });

  it("returns focus to the rail when a commit removes the focused tile", async () => {
    mountTab();
    const tile = wrapper.get('[data-tile="k_b"]');
    tile.element.focus();
    expect(document.activeElement).toBe(tile.element);
    await wrapper.setProps({ codex: panelWith([ENTRY_A]) });
    await nextTick();
    await nextTick();
    expect(document.activeElement?.getAttribute("data-tab-key")).toBe("cat_plain");
  });
});
