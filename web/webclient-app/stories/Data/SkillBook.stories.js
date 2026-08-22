import { h } from "vue";
import SkillBook from "../../components/SkillBook.vue";
import { SKILLS_SLICE_SAMPLE } from "../fixtures.js";

// SkillBook: the character's skill data as a two-level book. Props: skills
// ({actives, passives} in the character payload's category/group/skill
// shape, with optional cost/target/cast descriptor detail on some rows),
// initialTab (showcase: 'active' | 'passive'), initialQuery (showcase
// search seed). Tab and search are view-local state.

const renderBook = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(SkillBook, args),
    ]),
});

export default {
  title: "Data/SkillBook",
  component: SkillBook,
};

export const ActiveTab = {
  render: renderBook,
  args: {
    skills: SKILLS_SLICE_SAMPLE,
  },
};

export const PassiveTab = {
  render: renderBook,
  args: {
    skills: SKILLS_SLICE_SAMPLE,
    initialTab: "passive",
  },
};

export const SearchFiltered = {
  render: renderBook,
  args: {
    skills: SKILLS_SLICE_SAMPLE,
    initialQuery: "火",
  },
};
