import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import SkillBook from "../../components/SkillBook.vue";
import { SKILLS_SLICE_SAMPLE } from "../../stories/fixtures.js";

// Payload values referenced from the sample fixture instead of restating
// shipped catalog strings in this test's source (test-data-independence).
const FIRE_GROUP_LABEL = SKILLS_SLICE_SAMPLE.actives[0].groups[0].label;
const FIREBOLT = SKILLS_SLICE_SAMPLE.actives[0].groups[0].skills[0];
const FIREBALL = SKILLS_SLICE_SAMPLE.actives[0].groups[0].skills[1];
const FIRESTORM = SKILLS_SLICE_SAMPLE.actives[0].groups[0].skills[2];
const MARTIAL = SKILLS_SLICE_SAMPLE.actives[1];
const LEGACY = MARTIAL.groups[0].skills.find((row) => !("cost" in row));

describe("SkillBook (skillbook-authoritative-casting master–detail book)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountBook(props = {}) {
    wrapper = mount(SkillBook, {
      attachTo: document.body,
      props: { skills: SKILLS_SLICE_SAMPLE, ...props },
    });
    return wrapper;
  }

  const categories = (w) => w.findAll('[data-testid="skill-book__category"]');
  const row = (w, key) => w.get(`[data-testid="skill-book__skill"][data-key="${key}"]`);
  const detail = (w) => w.get('[data-testid="skill-book__detail"]');

  async function select(w, key) {
    const head = w.findAll('[data-testid="skill-book__category-head"]');
    for (const h of head) {
      if (h.attributes("aria-expanded") === "false") await h.trigger("click");
    }
    await row(w, key).trigger("click");
  }

  function setQuery(w, value) {
    const input = w.get('[data-testid="skill-book__search"]');
    input.element.value = value;
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
  }

  it("keeps practice separate and converts fractional hours to seconds", async () => {
    const w = mountBook();
    await w.get(`button[aria-label="修煉${FIREBOLT.label}"]`).trigger("click");
    expect(w.find('[data-testid="skill-book"]').exists()).toBe(false);
    await w.get('input[type="number"]').setValue("1.5");
    await w.get("form").trigger("submit");
    expect(w.emitted("practice")).toEqual([[{ skill: FIREBOLT.key, seconds: 5400 }]]);
  });

  it("rejects out-of-range duration and blocks repeat practice while locked", async () => {
    const w = mountBook();
    await w.get(`button[aria-label="修煉${FIREBOLT.label}"]`).trigger("click");
    await w.get('input[type="number"]').setValue("12.01");
    await w.get("form").trigger("submit");
    expect(w.get('[role="alert"]').text()).toContain("12");
    expect(w.emitted("practice")).toBeUndefined();
    await w.get('input[type="number"]').setValue("12");
    await w.setProps({ practiceDisabled: true });
    await w.get("form").trigger("submit");
    expect(w.emitted("practice")).toBeUndefined();
    await w.setProps({ practiceDisabled: false });
    await w.get("form").trigger("submit");
    expect(w.emitted("practice")[0][0].seconds).toBe(43200);
  });

  it("keeps the payload's category, group, and skill order in a keyboard tree", () => {
    const w = mountBook();
    expect(w.get('[data-testid="skill-book__tree"]').attributes("role")).toBe("tree");
    expect(categories(w).map((c) => c.attributes("data-category"))).toEqual([
      "elemental_magic",
      "martial_arts",
      "sexual_act",
    ]);
    const first = categories(w)[0];
    expect(first.text()).toContain(FIRE_GROUP_LABEL);
    expect(first.text().indexOf(FIREBOLT.label)).toBeLessThan(first.text().indexOf(FIREBALL.label));
    // Only the first category starts expanded; the others show their header.
    expect(first.attributes("data-open")).toBe("true");
    expect(categories(w)[1].attributes("data-open")).toBe("false");
    // The first visible skill is selected and owns the tree's tab stop.
    expect(row(w, FIREBOLT.key).attributes("aria-selected")).toBe("true");
    expect(row(w, FIREBOLT.key).attributes("tabindex")).toBe("0");
  });

  it("moves selection with the arrow keys and Enter goes to the actions without casting", async () => {
    const w = mountBook();
    const tree = w.get('[data-testid="skill-book__tree"]');
    await tree.trigger("keydown", { key: "ArrowDown" });
    await nextTick();
    expect(row(w, FIREBALL.key).attributes("aria-selected")).toBe("true");
    expect(detail(w).get('[data-testid="skill-book__detail-title"]').text()).toBe(FIREBALL.label);
    await tree.trigger("keydown", { key: "ArrowDown" });
    await tree.trigger("keydown", { key: "ArrowLeft" });
    await nextTick();
    // ← from a skill lands on its category header; ← again collapses it.
    await tree.trigger("keydown", { key: "ArrowLeft" });
    await nextTick();
    expect(categories(w)[0].attributes("data-open")).toBe("false");
    await tree.trigger("keydown", { key: "ArrowRight" });
    await nextTick();
    expect(categories(w)[0].attributes("data-open")).toBe("true");
    await row(w, FIREBOLT.key).trigger("click");
    await tree.trigger("keydown", { key: "Enter" });
    await nextTick();
    expect(document.activeElement?.getAttribute("data-testid")).toBe("skill-book__use");
    expect(w.emitted("use")).toBeUndefined();
  });

  it("switches to the passive tab with read-only rows and no actions", async () => {
    const w = mountBook();
    await w.get('[data-testid="skill-book__tab--passive"]').trigger("click");
    expect(categories(w).map((c) => c.attributes("data-category"))).toEqual(["enhancement"]);
    expect(w.findAll('[data-testid="skill-book__passive-badge"]').length).toBeGreaterThan(0);
    expect(w.find('[data-testid="skill-book__use"]').exists()).toBe(false);
    expect(w.find('[data-testid="skill-book__practice"]').exists()).toBe(false);
    expect(w.find('[data-testid="skill-book__field"]').exists()).toBe(false);
    expect(w.get('[data-testid="skill-book__passive-note"]').text()).toContain("不需施放");
  });

  it("filters through the search and offers a way out of an empty result", async () => {
    const w = mountBook();
    setQuery(w, FIRE_GROUP_LABEL);
    await nextTick();
    expect(categories(w).map((c) => c.attributes("data-category"))).toEqual(["elemental_magic"]);
    setQuery(w, "不存在");
    await nextTick();
    const empty = w.get('[data-testid="skill-book__empty"]');
    expect(empty.text()).toContain("沒有符合「不存在」的技能");
    await empty.get("button").trigger("click");
    expect(w.get('[data-testid="skill-book__search"]').element.value).toBe("");
  });

  it("marks only field-usable rows, with words rather than colour alone", () => {
    const w = mountBook();
    expect(row(w, FIREBOLT.key).find('[data-testid="skill-book__field"]').text()).toBe("戰鬥外可用");
    expect(row(w, FIREBALL.key).find('[data-testid="skill-book__field"]').exists()).toBe(false);
    expect(w.text()).not.toMatch(/\bcombat\b/);
  });

  it("states costs with a resource prefix and a range for advertised rungs", () => {
    const w = mountBook();
    expect(row(w, FIREBOLT.key).get('[data-testid="skill-book__cost"]').text()).toBe(`MP${FIREBOLT.cost.mp}`);
    expect(row(w, FIREBALL.key).get('[data-testid="skill-book__cost"]').text()).toBe("MP4–56");
    expect(row(w, FIREBALL.key).get('[data-testid="skill-book__cost"]').classes()).toContain("mp");
  });

  it("renders detail cells only when the payload provides them", async () => {
    const w = mountBook();
    await select(w, LEGACY.key);
    expect(row(w, LEGACY.key).find('[data-testid="skill-book__cost"]').exists()).toBe(false);
    expect(detail(w).find('[data-testid="skill-book__capability"]').exists()).toBe(false);
    // An undescribed row offers no 施放 (nothing is invented) but keeps 修煉.
    expect(w.find('[data-testid="skill-book__use"]').exists()).toBe(false);
    expect(w.find('[data-testid="skill-book__practice"]').exists()).toBe(true);
  });

  it("distinguishes static capability from current availability", async () => {
    const w = mountBook();
    const capability = detail(w).get('[data-testid="skill-book__capability"]');
    expect(capability.text()).toContain("可於戰鬥外使用");
    expect(capability.text()).toContain("對同場魔物施放將直接開戰");
    expect(capability.text()).toContain("於施放時依當下狀態判定");
    await select(w, FIRESTORM.key);
    expect(detail(w).text()).toContain("僅能在戰鬥中使用");
    // A combat-only skill outside combat never looks executable.
    const use = w.get('[data-testid="skill-book__use"]');
    expect(use.attributes("disabled")).toBeDefined();
    expect(w.get('[data-testid="skill-book__use-note"]').text()).toContain("僅能在戰鬥中使用");
  });

  it("shows the advertised 威力 rungs as a read-only table", async () => {
    const w = mountBook();
    await select(w, FIREBALL.key);
    const table = w.get('[data-testid="skill-book__scales"]');
    expect(table.findAll("th").map((th) => th.text())).toEqual(FIREBALL.freeform_scales.map((e) => `×${e.label}`));
    expect(table.find("button").exists()).toBe(false);
  });

  it("emits one use intent for an exploration field skill and nothing while locked", async () => {
    const w = mountBook();
    await w.get('[data-testid="skill-book__use"]').trigger("click");
    expect(w.emitted("use")).toEqual([[FIREBOLT.key]]);
    await w.setProps({ useLocked: true });
    await w.get('[data-testid="skill-book__use"]').trigger("click");
    expect(w.emitted("use")).toHaveLength(1);
  });

  it("adapts the action to the mode: combat hand-off, dialogue refusal", async () => {
    const w = mountBook({ mode: "combat" });
    const use = w.get('[data-testid="skill-book__use"]');
    expect(use.text()).toBe("改用戰鬥指令");
    await use.trigger("click");
    expect(w.emitted("use")).toEqual([[FIREBOLT.key]]);
    await w.setProps({ mode: "dialogue" });
    expect(w.get('[data-testid="skill-book__use"]').attributes("disabled")).toBeDefined();
    expect(w.get('[data-testid="skill-book__use-note"]').text()).toContain("對話中無法施放");
  });

  it("shows the pending state and a refused preview's server message", async () => {
    const w = mountBook({ usePendingKey: FIREBOLT.key });
    const use = w.get('[data-testid="skill-book__use"]');
    expect(use.text()).toBe("準備中…");
    expect(use.attributes("aria-busy")).toBe("true");
    await w.setProps({ usePendingKey: null, useNotice: { skillKey: FIREBOLT.key, message: "你的資源不足。" } });
    const alert = w.get('[data-testid="skill-book__notice"]');
    expect(alert.attributes("role")).toBe("alert");
    expect(alert.text()).toBe("無法施放：你的資源不足。");
  });

  it("returns focus to the invoking skill's 施放 when reopened from the dock", async () => {
    const w = mountBook({ returnTarget: { skillKey: FIREBALL.key, seq: 1 } });
    await new Promise((resolve) => setTimeout(resolve, 0));
    await nextTick();
    expect(row(w, FIREBALL.key).attributes("aria-selected")).toBe("true");
    // The combat-only skill's 施放 is disabled, so focus lands on its row.
    expect(document.activeElement?.getAttribute("data-key")).toBe(FIREBALL.key);
    await w.setProps({ returnTarget: { skillKey: FIREBOLT.key, seq: 2 } });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.activeElement?.getAttribute("data-testid")).toBe("skill-book__use");
  });

  it("states the withheld panel's reason and offers only the combat hand-off", async () => {
    const w = mountBook({
      skills: { schema_version: 7, available: false, reason: { code: "character_unavailable", message: "角色狀態目前無法顯示" } },
      mode: "combat",
    });
    expect(w.get('[data-testid="skill-book__unavailable"]').text()).toBe("角色狀態目前無法顯示");
    expect(w.find('[data-testid="skill-book__empty"]').exists()).toBe(false);
    expect(w.find('[data-testid="skill-book__detail"]').exists()).toBe(false);
    await w.get('[data-testid="skill-book__combat-handoff"]').trigger("click");
    expect(w.emitted("use")).toEqual([[null]]);
    await w.setProps({ useLocked: true });
    expect(w.get('[data-testid="skill-book__combat-handoff"]').attributes("disabled")).toBeDefined();
  });
});
