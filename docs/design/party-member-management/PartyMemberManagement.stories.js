// Approved visual prototypes of the party window, shop, and main navigation
// (docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md).
// Reference only: self-contained mock data, not wired to any payload, and
// outside the webclient component-coverage manifest. The real components
// get their own stories when they are implemented.
import { h } from "vue";
import PartyWindowPrototype from "./PartyWindowPrototype.vue";
import ShopPrototype from "./ShopPrototype.vue";
import MainNavPrototype from "./MainNavPrototype.vue";

// The drawer workspace over a dimmed stage, as the quest drawer prototype.
const workspace = (component) => (args) => ({
  render: () =>
    h(
      "div",
      {
        style: [
          "position: fixed; inset: 0;",
          "background: linear-gradient(rgba(5,6,8,.72), rgba(5,6,8,.82)), url(/art/showcase/sample-guild.webp) center/cover;",
          "padding: calc(60px * var(--ui-scale)) calc(16px * var(--ui-scale)) calc(16px * var(--ui-scale));",
          "box-sizing: border-box;",
        ].join(""),
      },
      [h(component, args)],
    ),
});
const fullscreen = (component) => (args) => ({
  // z-index 8 lifts the prototype bar above the shell header band
  // (.elosern-root::before, z-index 7) that the preview decorator draws.
  render: () => h("div", { style: "position: fixed; inset: 0; z-index: 8;" }, [h(component, args)]),
});

const party = workspace(PartyWindowPrototype);

export default {
  title: "Design/PartyMemberManagement",
  parameters: {
    docs: {
      description: {
        component:
          "隊伍視窗、商店與主導覽列的定稿設計稿。附身與否畫面完全相同；畫面上不放規則說明（移到說明視窗）。快捷鍵：P 隊伍、B 背包、C 狀態、K 技能、L 系譜、J 任務、M 地圖，焦點在文字輸入框時不生效。",
      },
    },
  },
};

export const MainNavigation = { render: fullscreen(MainNavPrototype), args: { possessing: false } };
export const MainNavigationPossessing = { render: fullscreen(MainNavPrototype), args: { possessing: true } };

export const MemberCompanion = { render: party, args: { initialTab: "member", initialMember: 2 } };
export const MemberCommander = { render: party, args: { initialTab: "member", initialMember: 1 } };
export const MemberKnockedOut = { render: party, args: { initialTab: "member", initialMember: 3 } };
export const MemberEmptySlot = { render: party, args: { initialTab: "member", initialMember: "empty" } };

export const BagConsumable = { render: party, args: { initialTab: "bag", initialMember: 1, initialItem: "potion_heal" } };
export const BagEquipment = { render: party, args: { initialTab: "bag", initialMember: 1, initialItem: "steel_shortsword" } };
export const BagInCombat = { render: party, args: { initialTab: "bag", initialMember: 2, initialItem: "potion_mana", combat: true } };

export const StatusTraitBreakdown = { render: party, args: { initialTab: "status", initialMember: 2, initialTrait: "magic_power" } };
export const StatusNoGuild = { render: party, args: { initialTab: "status", initialMember: 3 } };

export const SkillBook = { render: party, args: { initialTab: "skill", initialMember: 2, initialSkill: "healing_light" } };
export const SkillInCombat = { render: party, args: { initialTab: "skill", initialMember: 2, initialSkill: "healing_light", combat: true } };

export const LineageGraph = { render: party, args: { initialTab: "lineage", initialMember: 2, initialGraph: "ice" } };
export const LineageSingleNode = { render: party, args: { initialTab: "lineage", initialMember: 2, initialGraph: "holy_water" } };
export const LineageReadyToUnlock = { render: party, args: { initialTab: "lineage", initialMember: 1, initialGraph: "sword" } };

export const ShopBuyEquipment = { render: workspace(ShopPrototype), args: { initialTab: "buy", initialMember: 2 } };
export const ShopSell = { render: workspace(ShopPrototype), args: { initialTab: "sell", initialMember: 3 } };
