import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import SkillBook from "../../components/SkillBook.vue";
import { SKILLS_SLICE_SAMPLE } from "../../stories/fixtures.js";

describe("SkillBook (B3 data family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountBook(props = {}) {
    wrapper = mount(SkillBook, {
      props: {
        skills: SKILLS_SLICE_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  function categories(w) {
    return w.findAll('[data-testid="skill-book__category"]');
  }

  function setQuery(w, value) {
    const input = w.get('[data-testid="skill-book__search"]');
    input.element.value = value;
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
  }

  // The book's own title/count heading is gone (the counts now render once,
  // in the drawer head's subtitle, computed in AppClient). The remaining
  // tab / search assertions keep their `data-testid` values, unchanged.

  it("opens on the active tab with the payload's category, group, and skill ordering", async () => {
    const w = mountBook();
    expect(w.get('[data-testid="skill-book__tab--active"]').attributes("aria-selected")).toBe("true");
    expect(
      w.get('[data-testid="skill-book__tab--passive"]').attributes("aria-selected"),
    ).toBe("false");

    const cats = categories(w);
    expect(cats.map((c) => c.attributes("data-category"))).toEqual([
      "elemental_magic",
      "martial_arts",
      "movement",
    ]);
    expect(cats[0].text()).toContain("元素魔法");
    expect(cats[0].text()).toContain("火");
    // Sub-group order and skill order are the payload's own.
    expect(cats[0].text()).toContain("火矢");
    expect(cats[0].text().indexOf("火矢")).toBeLessThan(cats[0].text().indexOf("火球"));
    expect(cats[0].text().indexOf("火球")).toBeLessThan(
      cats[0].text().indexOf("微光治癒"),
    );
    // A null-keyed group renders no group heading.
    const martial = cats[1];
    expect(
      martial.find('[data-testid="skill-book__group--ungrouped"]').exists(),
    ).toBe(true);
    expect(martial.find('[data-testid="skill-book__group-label"]').exists()).toBe(false);
  });

  it("switches to the passive tab and shows only passive categories", async () => {
    const w = mountBook();
    await w.get('[data-testid="skill-book__tab--passive"]').trigger("click");
    expect(w.get('[data-testid="skill-book__tab--passive"]').attributes("aria-selected")).toBe("true");
    expect(categories(w).map((c) => c.attributes("data-category"))).toEqual([
      "enhancement",
      "innate_gift",
    ]);
    expect(w.text()).toContain("強化身體");
    expect(w.text()).not.toContain("火矢");
  });

  it("honors the initialTab showcase prop", () => {
    const w = mountBook({ initialTab: "passive" });
    expect(w.get('[data-testid="skill-book__tab--passive"]').attributes("aria-selected")).toBe("true");
    expect(categories(w).map((c) => c.attributes("data-category"))).toEqual([
      "enhancement",
      "innate_gift",
    ]);
  });

  it("filters by skill, group, and category label through the search", async () => {
    const w = mountBook();
    setQuery(w, "火");
    await nextTick();
    const cats = categories(w);
    expect(cats.map((c) => c.attributes("data-category"))).toEqual(["elemental_magic"]);
    expect(w.text()).toContain("火矢");
    expect(w.text()).toContain("火風暴");
    expect(w.text()).not.toContain("微光治癒");
    expect(w.text()).not.toContain("基本攻擊");

    setQuery(w, "治癒");
    await nextTick();
    expect(w.text()).toContain("微光治癒");
    expect(w.text()).not.toContain("火矢");
  });

  it("shows the honest empty state when nothing matches", async () => {
    const w = mountBook();
    setQuery(w, "不存在");
    await nextTick();
    expect(w.get('[data-testid="skill-book__empty"]').text()).toBe("沒有符合的技能");
    expect(categories(w)).toHaveLength(0);
  });

  it("renders per-skill cost, target, and cast detail only when the payload provides it", () => {
    const w = mountBook();

    // cost {mp} + target_spec single, no cast detail.
    const firebolt = w.find('[data-testid="skill-book__skill"][data-key="firebolt"]');
    expect(firebolt.find('[data-testid="skill-book__cost"]').text()).toBe("10 mp");
    expect(firebolt.find('[data-testid="skill-book__target"]').text()).toBe("單一目標");
    expect(firebolt.find('[data-testid="skill-book__cast"]').exists()).toBe(false);

    // Power scales become the cast detail, with their per-scale mp costs.
    const fireball = w.find('[data-testid="skill-book__skill"][data-key="fireball"]');
    expect(fireball.find('[data-testid="skill-book__cost"]').text()).toBe("14 mp");
    expect(fireball.find('[data-testid="skill-book__cast"]').text()).toBe(
      "威力 1/4（4 mp）・1/2（7 mp）・1（14 mp）・2（28 mp）・4（56 mp）",
    );

    // Multi-resource cost and the area target with cast shorthands.
    const firestorm = w.find('[data-testid="skill-book__skill"][data-key="firestorm"]');
    expect(firestorm.find('[data-testid="skill-book__cost"]').text()).toBe("30 mp ・ 5 sp");
    expect(firestorm.find('[data-testid="skill-book__target"]').text()).toBe("範圍");
    expect(firestorm.find('[data-testid="skill-book__cast"]').text()).toBe("範圍代號 all-enemies／all");

    // The empty cost object is the descriptor's free form: rendered 免費,
    // never an invented cost.
    const basic = w.find('[data-testid="skill-book__skill"][data-key="basic_attack"]');
    expect(basic.find('[data-testid="skill-book__cost"]').text()).toBe("免費");
    const flee = w.find('[data-testid="skill-book__skill"][data-key="flee"]');
    expect(flee.find('[data-testid="skill-book__cost"]').text()).toBe("免費");
    expect(flee.find('[data-testid="skill-book__target"]').text()).toBe("無目標");

    // The unregistered-key fallback row carries no detail fields at all.
    const legacy = w.find('[data-testid="skill-book__skill"][data-key="legacy_stance"]');
    expect(legacy.find('[data-testid="skill-book__cost"]').exists()).toBe(false);
    expect(legacy.find('[data-testid="skill-book__target"]').exists()).toBe(false);
    expect(legacy.find('[data-testid="skill-book__cast"]').exists()).toBe(false);
    expect(legacy.text()).toBe("legacy_stance");
  });

  it("renders passive rows as label-only (the payload gives them no detail)", () => {
    const w = mountBook({ initialTab: "passive" });
    const rows = w.findAll('[data-testid="skill-book__skill"]');
    expect(rows).toHaveLength(3);
    expect(rows.map((r) => r.text())).toEqual(["強化身體", "防衛本能", "精靈長壽"]);
  });

  it("renders the combat pill only for rows whose usable_out_of_combat is true", () => {
    const w = mountBook();
    // The only fixture row carrying the field renders the pill.
    const firebolt = w.find('[data-testid="skill-book__skill"][data-key="firebolt"]');
    const pill = firebolt.find('[data-testid="skill-book__ooc"]');
    expect(pill.exists()).toBe(true);
    expect(pill.text()).toBe("combat");

    // Every other active row lacks the field, so the pill is absent.
    for (const key of ["fireball", "firestorm", "mend_glow", "basic_attack", "light_blade", "flee", "legacy_stance"]) {
      const row = w.find(`[data-testid="skill-book__skill"][data-key="${key}"]`);
      expect(row.find('[data-testid="skill-book__ooc"]').exists()).toBe(false);
    }

    // The unregistered-key fallback row carries no detail fields at all.
    const legacy = w.find('[data-testid="skill-book__skill"][data-key="legacy_stance"]');
    expect(legacy.text()).toBe("legacy_stance");
  });

  it("renders no combat pill on the passive tab", () => {
    const w = mountBook({ initialTab: "passive" });
    expect(w.find('[data-testid="skill-book__ooc"]').exists()).toBe(false);
  });
});
