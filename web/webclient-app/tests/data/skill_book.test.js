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
      "sexual_act",
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
    // Each passive row now carries a trailing 被動 badge.
    // Vue drops the whitespace-only text nodes between the row's elements,
    // so the badge text concatenates directly onto the skill label.
    expect(rows.map((r) => r.text())).toEqual(["強化身體被動", "防衛本能被動", "精靈長壽被動"]);
  });

  it("renders the combat pill only for rows whose usable_out_of_combat is true", () => {
    const w = mountBook();
    // Three fixture rows carry usable_out_of_combat: true → the pill renders.
    for (const key of ["firebolt", "gale_dash", "solace"]) {
      const row = w.find(`[data-testid="skill-book__skill"][data-key="${key}"]`);
      const pill = row.find('[data-testid="skill-book__ooc"]');
      expect(pill.exists()).toBe(true);
      expect(pill.text()).toBe("combat");
    }

    // Every other active row lacks the field, so the pill is absent.
    for (const key of ["fireball", "firestorm", "mend_glow", "quake", "basic_attack", "light_blade", "flee", "legacy_stance"]) {
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

  it("rotates the category chevron with the details open state", async () => {
    // Attach to the document so jsdom recomputes styles when the native
    // `open` attribute changes (a detached tree does not track it reliably).
    const w = mount(SkillBook, {
      props: { skills: SKILLS_SLICE_SAMPLE },
      attachTo: document.body,
    });
    const cats = categories(w);
    // The first category starts open, the second closed (the component's
    // `:open="index === 0"` binding).
    expect(cats[0].element.hasAttribute("open")).toBe(true);
    expect(cats[1].element.hasAttribute("open")).toBe(false);
    // The open category's chevron resolves to the draft's 90° rotation; a
    // closed category's chevron has no transform set (jsdom reports "").
    expect(
      window.getComputedStyle(cats[0].find('[data-testid="skill-book__category-chevron"]').element).transform,
    ).toBe("rotate(90deg)");
    expect(
      window.getComputedStyle(cats[1].find('[data-testid="skill-book__category-chevron"]').element).transform,
    ).toBe("");
    // Setting the native `open` attribute flips the computed transform.
    cats[1].element.open = true;
    await nextTick();
    expect(
      window.getComputedStyle(cats[1].find('[data-testid="skill-book__category-chevron"]').element).transform,
    ).toBe("rotate(90deg)");
    w.unmount();
  });

  it("renders group colour dots only for reference-sampled elements", () => {
    const w = mountBook();
    const fireDot = w.find('[data-testid="skill-book__group--fire"] [data-testid="skill-book__group-dot"]');
    expect(fireDot.element.style.background).toBe("var(--seal-500)");
    const waterDot = w.find('[data-testid="skill-book__group--water"] [data-testid="skill-book__group-dot"]');
    expect(waterDot.element.style.background).toBe("var(--vit-mp)");
    const windDot = w.find('[data-testid="skill-book__group--wind"] [data-testid="skill-book__group-dot"]');
    expect(windDot.element.style.background).toBe("var(--warn)");
    const soloDot = w.find('[data-testid="skill-book__group--solo"] [data-testid="skill-book__group-dot"]');
    expect(soloDot.element.style.background).toBe("var(--seal-500)");
    // A group for an element the reference never colour-codes renders with no dot.
    expect(
      w.find('[data-testid="skill-book__group--earth"] [data-testid="skill-book__group-dot"]').exists(),
    ).toBe(false);
  });

  it("colour-codes cost cells by the resource they spend", () => {
    const w = mountBook();
    expect(
      w.find('[data-testid="skill-book__skill"][data-key="firebolt"] [data-testid="skill-book__cost"]').classes(),
    ).toContain("mp");
    expect(
      w.find('[data-testid="skill-book__skill"][data-key="light_blade"] [data-testid="skill-book__cost"]').classes(),
    ).toContain("sp");
    expect(
      w.find('[data-testid="skill-book__skill"][data-key="gale_dash"] [data-testid="skill-book__cost"]').classes(),
    ).toContain("sp");
    // A mixed mp+sp cost reads the SP tone — sp wins when both are present.
    expect(
      w.find('[data-testid="skill-book__skill"][data-key="firestorm"] [data-testid="skill-book__cost"]').classes(),
    ).toContain("sp");
    expect(
      w.find('[data-testid="skill-book__skill"][data-key="basic_attack"] [data-testid="skill-book__cost"]').classes(),
    ).toContain("free");
    expect(
      w.find('[data-testid="skill-book__skill"][data-key="flee"] [data-testid="skill-book__cost"]').classes(),
    ).toContain("free");
    expect(
      w.find('[data-testid="skill-book__skill"][data-key="solace"] [data-testid="skill-book__cost"]').classes(),
    ).toContain("free");
  });

  it("keeps a zero-value resource key on the free colour", () => {
    const skills = {
      actives: [
        {
          category: "elemental_magic",
          label: "元素魔法",
          groups: [
            {
              group: "earth",
              label: "土",
              skills: [
                { key: "z1", label: "土刺", cost: { sp: 0 }, target_spec: "single" },
                { key: "z2", label: "土盾", cost: { mp: 0, sp: 0 }, target_spec: "self" },
              ],
            },
          ],
        },
      ],
      passives: [],
    };
    const w = mountBook({ skills });
    const z1 = w.find('[data-testid="skill-book__skill"][data-key="z1"]');
    expect(z1.find('[data-testid="skill-book__cost"]').text()).toBe("免費");
    expect(z1.find('[data-testid="skill-book__cost"]').classes()).toContain("free");
    const z2 = w.find('[data-testid="skill-book__skill"][data-key="z2"]');
    expect(z2.find('[data-testid="skill-book__cost"]').classes()).toContain("free");
  });

  it("renders the combat pill with the reference's bordered-pill styling", () => {
    const w = mountBook();
    const pill = w.get('[data-testid="skill-book__ooc"]');
    expect(pill.text()).toBe("combat");
    const cs = window.getComputedStyle(pill.element);
    expect(cs.borderRadius).toBe("4px");
    expect(cs.fontSize).toBe("9px");
    expect(cs.color).toContain("var(--ok)");
  });

  it("renders the 被動 badge on passive-tab rows only", () => {
    const wp = mountBook({ initialTab: "passive" });
    const rows = wp.findAll('[data-testid="skill-book__skill"]');
    for (const row of rows) {
      expect(row.find('[data-testid="skill-book__passive-badge"]').text()).toBe("被動");
    }
    wp.unmount();
    const wa = mountBook();
    expect(wa.find('[data-testid="skill-book__passive-badge"]').exists()).toBe(false);
  });

  it("shows the list-conventions legend on the active tab only", () => {
    const wa = mountBook();
    const legend = wa.find('[data-testid="skill-book__legend"]');
    expect(legend.exists()).toBe(true);
    expect(legend.text().replace(/\s+/g, " ").trim()).toBe(
      "依分類分群；戰鬥外 表示非戰鬥亦可施放；未解鎖之性愛行為「藏而不列」。",
    );
    const okSpan = legend.find("span");
    expect(okSpan.text()).toBe("戰鬥外");
    expect(okSpan.element.style.color).toBe("var(--ok)");
    wa.unmount();
    const wp = mountBook({ initialTab: "passive" });
    expect(wp.find('[data-testid="skill-book__legend"]').exists()).toBe(false);
  });

  it("right-aligns the cost cell as the row's last column", () => {
    const w = mountBook();
    // The reference's `.srow .cost{margin-left:auto}`: target/cast detail
    // stays on the name side; the cost cell is the row's rightmost column.
    const firestorm = w.find('[data-testid="skill-book__skill"][data-key="firestorm"]');
    expect(
      Array.from(firestorm.element.children).map((el) => el.className),
    ).toEqual([
      "skill-book__skill-name",
      "skill-book__target",
      "skill-book__cast",
      "skill-book__cost sp",
    ]);
    expect(window.getComputedStyle(firestorm.element.children[3]).marginLeft).toBe("auto");
  });

  it("keeps the previous 8px top spacing for label-less groups", () => {
    const w = mountBook();
    const ungrouped = w.get('[data-testid="skill-book__group--ungrouped"]');
    expect(ungrouped.classes()).toContain("skill-book__group--ungrouped");
    // jsdom reports the unresolved token reference verbatim (tokens.css is
    // not loaded in the test DOM): `var(--sp-2)` = 8px in the app.
    expect(window.getComputedStyle(ungrouped.element).marginTop).toBe("var(--sp-2)");
  });
});
