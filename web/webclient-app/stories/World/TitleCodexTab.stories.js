import { h, nextTick, onMounted, ref } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";
import TitleCodexTab from "../../components/handbook/TitleCodexTab.vue";
import { useQuestDrawerMemory } from "../../components/quest-drawer-memory.js";
import { BALLOT, UNAVAILABLE_CODEX, titleCodex } from "../fixtures/title_codex_panels.js";

// TitleCodexTab (handbook-titles-tab): the 手帳's 稱號 tab inside the real
// HudDrawer chrome, over synthetic `title_codex` v1 panels. The rail lists
// the six fixed-title categories with unlocked counts, then 異名 and, while a
// ballot is pending, 提名. Fixed titles are a medal wall; epithets and
// nominees are list rows; the detail footer carries 裝備, the two-step 移除
// and the ballot answers. Props: codex (the committed panel or null),
// memoryScope, combat. Every intent is emitted as `action`.

export default {
  title: "World/TitleCodexTab",
  component: TitleCodexTab,
};

// Each story seeds its own session memory scope with its rail and selection.
// `armRemoval` presses the selected epithet's 移除… once mounted.
const renderTab = ({ rail = null, selection = null, armRemoval = false, ...args }, context) => ({
  setup() {
    const scope = `story:${context.id}`;
    const memory = useQuestDrawerMemory(scope);
    memory.titlesRail = rail;
    if (rail && selection) memory.selectedByTab = { [`titles:${rail}`]: selection };
    const host = ref(null);
    onMounted(async () => {
      if (!armRemoval) return;
      await nextTick();
      host.value?.querySelector('[data-testid="handbook__remove"]')?.click();
    });
    return () =>
      h("div", { ref: host, style: "display: contents" }, [
        h(HudDrawer, { open: true, title: "手帳", icon: "quests", drawerKey: "quest", bodyFlush: true }, () => [
          h(TitleCodexTab, { ...args, memoryScope: scope }),
        ]),
      ]);
  },
});

// A fixed category with a locked medal selected: its name and 取得條件 hint.
export const LockedSelection = {
  render: renderTab,
  args: { codex: titleCodex(), rail: "combat", selection: "t_beta" },
};

// The equipped fixed title: 裝備 is disabled with the ★ reason.
export const EquippedFixed = {
  render: renderTab,
  args: { codex: titleCodex(), rail: "combat", selection: "t_alpha" },
};

// The guild category: a grade gem on the matching key, the emblem otherwise.
export const GuildMedals = {
  render: renderTab,
  args: { codex: titleCodex(), rail: "guild", selection: "g_x_rank" },
};

// The equipped epithet: no 移除 (its row's can_remove is false).
export const EpithetEquipped = {
  render: renderTab,
  args: { codex: titleCodex(), rail: "epithet", selection: "合成異名乙" },
};

// The removal confirmation armed on a removable epithet.
export const RemovalArmed = {
  render: renderTab,
  args: { codex: titleCodex(), rail: "epithet", selection: "合成異名甲", armRemoval: true },
};

// A pending ballot: the hot 提名 entry with the accept and decline answers.
export const Ballot = {
  render: renderTab,
  args: { codex: titleCodex({ pending_ballot: BALLOT }), rail: "ballot", selection: "合成提名乙" },
};

// Before the first `title_codex` commit.
export const Absent = {
  render: renderTab,
  args: { codex: null },
};

// In combat with the common unavailable form: the panel's reason.
export const UnavailableInCombat = {
  render: renderTab,
  args: { codex: UNAVAILABLE_CODEX, combat: true },
};
