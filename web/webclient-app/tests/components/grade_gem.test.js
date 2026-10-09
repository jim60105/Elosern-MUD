import { afterEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import GradeGem from "../../components/GradeGem.vue";
import { GRADE_MATERIALS, gradeMaterial } from "../../components/grade-materials.js";

const GRADES = ["F", "E", "D", "C", "B", "A", "S"];
const MATERIAL_PROPS = ["--gem-hi", "--gem-lo", "--gem-rim", "--gem-ink", "--gem-inner"];

describe("GradeGem (quest-drawer-ui-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  function mountGem(props) {
    wrapper = mount(GradeGem, { props });
    return wrapper;
  }

  it("defines all five material properties for each of the seven grades", () => {
    expect(Object.keys(GRADE_MATERIALS)).toEqual(GRADES);
    for (const grade of GRADES) {
      expect(Object.keys(GRADE_MATERIALS[grade])).toEqual(MATERIAL_PROPS);
    }
    // The ladder's two ends: iron and seal-red with a gold rim.
    expect(GRADE_MATERIALS.F["--gem-rim"]).toBe("#6d6a62");
    expect(GRADE_MATERIALS.S["--gem-hi"]).toBe("var(--seal-600)");
    expect(GRADE_MATERIALS.S["--gem-rim"]).toBe("var(--gold-400)");
  });

  it.each(GRADES)("binds grade %s's material as inline custom properties", (grade) => {
    const style = mountGem({ grade }).get(".grade-gem").attributes("style");
    for (const [prop, value] of Object.entries(GRADE_MATERIALS[grade])) {
      expect(style).toContain(`${prop}: ${value}`);
    }
  });

  it("falls back to iron for an unknown or missing grade", () => {
    expect(gradeMaterial("Z")).toBe(GRADE_MATERIALS.F);
    expect(gradeMaterial(null)).toBe(GRADE_MATERIALS.F);
    expect(gradeMaterial("toString")).toBe(GRADE_MATERIALS.F);
    const style = mountGem({ grade: "Z" }).get(".grade-gem").attributes("style");
    expect(style).toContain(`--gem-rim: ${GRADE_MATERIALS.F["--gem-rim"]}`);
  });

  it("always renders the letter, whatever the material", () => {
    expect(mountGem({ grade: "B" }).get(".grade-gem__letter").text()).toBe("B");
    wrapper.unmount();
    expect(mountGem({ grade: "Z" }).get(".grade-gem__letter").text()).toBe("Z");
    wrapper.unmount();
    expect(mountGem({}).get(".grade-gem__letter").text()).toBe("—");
  });

  it("is decorative unless a label is passed", () => {
    const decorative = mountGem({ grade: "E" }).get(".grade-gem");
    expect(decorative.attributes("aria-hidden")).toBe("true");
    expect(decorative.attributes("role")).toBeUndefined();
    expect(decorative.attributes("aria-label")).toBeUndefined();
    wrapper.unmount();

    const labelled = mountGem({ grade: "E", label: "等級 E" }).get(".grade-gem");
    expect(labelled.attributes("aria-hidden")).toBeUndefined();
    expect(labelled.attributes("role")).toBe("img");
    expect(labelled.attributes("aria-label")).toBe("等級 E");
  });

  it.each(["sm", "md", "lg"])("renders the %s size class", (size) => {
    expect(mountGem({ grade: "C", size }).classes()).toContain(`grade-gem--${size}`);
  });
});
