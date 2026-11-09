import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import CodexTileGrid from "../../components/handbook/CodexTileGrid.vue";
import { codexGroups, MONSTER_CATEGORY } from "../../components/handbook/lore-codex-model.js";
import { CODEX_PLACEHOLDER, codexCategory, codexEntry, loreCodex } from "../../stories/fixtures/lore_codex_panels.js";

// A synthetic monster wall: a headed tier with a defeated entry and a
// placeholder, then a second headed tier with a sighted entry; and a plain
// category with one null-label group.
const panel = loreCodex([
  codexCategory(MONSTER_CATEGORY, "獸類", [
    { key: "tier_a", label: "甲階", slots: [codexEntry("k_def", "合成擊敗", { stage: "defeated" }), CODEX_PLACEHOLDER] },
    { key: "tier_b", label: "乙階", slots: [codexEntry("k_sig", "合成目擊", { stage: "sighted" })] },
  ]),
  codexCategory("cat_plain", "平類", [
    { key: "cat_plain", label: null, slots: [codexEntry("k_plain", "合成平條目"), CODEX_PLACEHOLDER] },
  ]),
]);

describe("CodexTileGrid (handbook-codex-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountGrid(category = MONSTER_CATEGORY, props = {}) {
    wrapper = mount(CodexTileGrid, {
      attachTo: document.body,
      props: {
        groups: codexGroups(panel, category),
        category,
        heading: "合成分類",
        legend: category === MONSTER_CATEGORY,
        panel,
        ...props,
      },
    });
    return wrapper;
  }

  const cell = (id) => wrapper.get(`[data-tile="${id}"]`);
  const focusedTile = () => document.activeElement?.getAttribute("data-tile");

  it("marks defeated, sighted and placeholder tiles with three distinct stage shapes", () => {
    mountGrid();
    const wall = wrapper.get('[data-testid="tile-wall"]');
    const stageOf = (id) => wall.get(`[data-testid="handbook__tile--${id}"] [data-stage]`);
    expect(stageOf("k_def").attributes("data-stage")).toBe("defeated");
    expect(stageOf("k_sig").attributes("data-stage")).toBe("sighted");
    expect(stageOf("p:tier_a:1").attributes("data-stage")).toBe("unknown");
    // Shape, not colour: a filled diamond, a hollow diamond, and a ？ mark.
    expect(stageOf("k_def").get("path").attributes("fill")).toBe("currentColor");
    expect(stageOf("k_sig").get("path").attributes("fill")).toBe("none");
    expect(stageOf("p:tier_a:1").find("svg").exists()).toBe(false);
    expect(stageOf("p:tier_a:1").text()).toBe("？");
    expect(wall.get('[data-testid="handbook__tile--k_sig"]').classes()).toContain("is-sighted");
  });

  it("carries the legend with the three marks only on the monster wall, as the wall's last child", () => {
    mountGrid();
    const legend = wrapper.get('[data-testid="handbook__codex-legend"]');
    expect(legend.findAll("[data-stage]").map((mark) => mark.attributes("data-stage"))).toEqual([
      "defeated",
      "sighted",
      "unknown",
    ]);
    const wall = wrapper.get('[data-testid="handbook__codex-wall"]');
    expect(wall.element.lastElementChild).toBe(legend.element);
    wrapper.unmount();
    mountGrid("cat_plain");
    expect(wrapper.find('[data-testid="handbook__codex-legend"]').exists()).toBe(false);
  });

  it("lets a placeholder take focus but never select it", async () => {
    mountGrid();
    const placeholder = cell("p:tier_a:1");
    expect(placeholder.attributes("aria-disabled")).toBe("true");
    expect(placeholder.attributes("aria-label")).toBe("未記錄");
    placeholder.element.focus();
    expect(focusedTile()).toBe("p:tier_a:1");
    await placeholder.trigger("keydown", { key: "Enter" });
    await placeholder.trigger("click");
    expect(wrapper.emitted("select")).toBeUndefined();
  });

  it("walks the tiles across groups with arrows, Home and End, and selects on Enter", async () => {
    mountGrid();
    cell("k_def").element.focus();
    await cell("k_def").trigger("keydown", { key: "ArrowRight" });
    await nextTick();
    expect(focusedTile()).toBe("p:tier_a:1");
    await cell("p:tier_a:1").trigger("keydown", { key: "ArrowRight" });
    await nextTick();
    expect(focusedTile()).toBe("k_sig");
    await cell("k_sig").trigger("keydown", { key: "Home" });
    await nextTick();
    expect(focusedTile()).toBe("k_def");
    await cell("k_def").trigger("keydown", { key: "End" });
    await nextTick();
    expect(focusedTile()).toBe("k_sig");
    expect(wrapper.emitted("select")).toBeUndefined();
    await cell("k_sig").trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("select")).toEqual([["k_sig"]]);
  });

  it("renders a group heading only for a non-null label", () => {
    mountGrid();
    expect(wrapper.findAll(".tile-wall__group-head").map((head) => head.text())).toEqual(["甲階", "乙階"]);
    wrapper.unmount();
    mountGrid("cat_plain");
    expect(wrapper.findAll(".tile-wall__group-head")).toHaveLength(0);
  });

  it("names entry tiles with the title and the stage", () => {
    mountGrid();
    expect(cell("k_def").attributes("aria-label")).toBe("合成擊敗，已擊敗");
    expect(cell("k_sig").attributes("aria-label")).toBe("合成目擊，已目擊");
  });
});
