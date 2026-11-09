import { h } from "vue";
import CodexDetail from "../../components/handbook/CodexDetail.vue";

// CodexDetail (handbook-primitives): the handbook's shared detail column. The
// hero band holds a medal with the entry's grade gem or emblem (a dashed
// silhouette ring while locked) and an optional nameplate; then the ribbon,
// title, gold subtitle, sections, and the shared DetailFooter pinned at the
// bottom. Every fixture here is synthetic.

const renderDetail = (args) => ({
  render: () =>
    h("div", { style: "width: calc(760px * var(--ui-scale)); height: calc(640px * var(--ui-scale)); margin: calc(24px * var(--ui-scale));" }, [
      h(CodexDetail, args),
    ]),
});

const SECTIONS = [
  { label: "來歷", text: "這是一段示範用的說明文字，描述這一項的來歷。" },
  { label: "備註", text: "第二段示範文字。" },
];

export default {
  title: "World/CodexDetail",
  component: CodexDetail,
};

// An emblem hero with a nameplate, an equipped stamp and a footer.
export const EmblemHero = {
  render: renderDetail,
  args: {
    detail: {
      id: "sample-emblem",
      name: "示範稱號",
      ribbon: "探索",
      emblem: "explore",
      grade: null,
      locked: false,
      stamp: { kind: "equipped", label: "裝備中" },
      subtitle: "示範副標題",
      sections: SECTIONS.slice(0, 1),
      nameplate: "示範全稱",
    },
    footer: {
      reason: null,
      buttons: [{ key: "equip", label: "卸下", tone: "plain" }],
    },
  },
};

// A grade hero: the grade gem in the medal.
export const GradeHero = {
  render: renderDetail,
  args: {
    detail: {
      id: "sample-grade",
      name: "示範等級項目",
      ribbon: "戰鬥",
      emblem: "combat",
      grade: "B",
      locked: false,
      stamp: null,
      subtitle: "示範副標題",
      sections: SECTIONS,
      nameplate: null,
    },
    footer: {
      reason: null,
      buttons: [{ key: "equip", label: "裝備", tone: "primary" }],
    },
  },
};

// A locked entry: the silhouette ring, the locked stamp, two sections and a
// disabled action beside its reason.
export const LockedWithSections = {
  render: renderDetail,
  args: {
    detail: {
      id: "sample-locked",
      name: "未取得的項目",
      ribbon: "公會",
      emblem: "guild",
      grade: null,
      locked: true,
      stamp: { kind: "locked", label: "未取得" },
      subtitle: null,
      sections: SECTIONS,
      nameplate: null,
    },
    footer: {
      reason: "尚未取得。",
      buttons: [{ key: "equip", label: "裝備", tone: "primary", enabled: false, describedByReason: true }],
    },
  },
};

// No selection: the empty detail.
export const Empty = {
  render: renderDetail,
  args: { detail: null, footer: null },
};
