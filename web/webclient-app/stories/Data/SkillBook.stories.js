import { h } from "vue";
import SkillBook from "../../components/SkillBook.vue";
import { SKILLS_SLICE_SAMPLE } from "../fixtures.js";

// SkillBook (skillbook-authoritative-casting D8): the master–detail
// spellbook. Props: skills ({actives, passives} in the character payload's
// category/group/skill shape), initialTab / initialQuery (showcase seeds),
// mode (what 施放 does: exploration preview, combat hand-off, dialogue
// refusal), usePendingKey / useNotice (the in-flight and refused preview
// states). Tab, search, expansion, and selection are view-local state.

const renderBook = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 16px; background: var(--panel-solid); height: 600px; overflow: auto;" }, [
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

export const CombatHandOff = {
  render: renderBook,
  args: {
    skills: SKILLS_SLICE_SAMPLE,
    mode: "combat",
  },
};

export const PendingPreview = {
  render: renderBook,
  args: {
    skills: SKILLS_SLICE_SAMPLE,
    usePendingKey: SKILLS_SLICE_SAMPLE.actives[0].groups[0].skills[0].key,
  },
};

export const RefusedPreview = {
  render: renderBook,
  args: {
    skills: SKILLS_SLICE_SAMPLE,
    useNotice: {
      skillKey: SKILLS_SLICE_SAMPLE.actives[0].groups[0].skills[0].key,
      message: "你的資源不足。",
    },
  },
};
