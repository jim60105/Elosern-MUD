import { h } from "vue";
import GradeGem from "../../components/GradeGem.vue";

// GradeGem (quest-drawer-ui-primitives): the rotated-square grade seal with
// the upright letter. The F→S material ladder runs iron, bronze, dark
// bronze, silver, gold, bright gold, and seal-red with a gold rim. `sm`
// sits in list rows, `md` in the grade rail, `lg` in the detail hero.

const GRADES = ["F", "E", "D", "C", "B", "A", "S"];
const SIZES = ["sm", "md", "lg"];

export default {
  title: "World/GradeGem",
  component: GradeGem,
  argTypes: {
    grade: { control: "select", options: [...GRADES, "?"] },
    size: { control: "inline-radio", options: SIZES },
  },
};

// One gem, driven by the controls.
export const Single = {
  args: { grade: "E", size: "md", label: null },
};

// A labelled gem: an image named by `label` instead of a decorative seal.
export const Labelled = {
  args: { grade: "A", size: "lg", label: "A 級" },
};

// The whole ladder at every size.
export const Ladder = {
  args: { grades: GRADES, sizes: SIZES },
  render: (args) => ({
    render: () =>
      h(
        "div",
        { style: "display: grid; gap: calc(16px * var(--ui-scale)); padding: calc(24px * var(--ui-scale));" },
        args.sizes.map((size) =>
          h(
            "div",
            {
              style: "display: flex; align-items: center; gap: calc(14px * var(--ui-scale)); color: var(--paper-500);",
              "data-size": size,
            },
            [
              h("span", { style: "width: 3em; font: var(--text-xs) var(--f-num);" }, size),
              ...args.grades.map((grade) => h(GradeGem, { grade, size })),
            ],
          ),
        ),
      ),
  }),
};
