import { h } from "vue";
import PartySkillTab from "../../components/PartySkillTab.vue";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab } from "../../components/party-window-memory.js";
import {
  CHARACTER_SKILL_COMPANION_SAMPLE,
  CHARACTER_SKILL_LADDER_SAMPLE,
  CHARACTER_SKILL_NO_MASTERY_SAMPLE,
} from "../fixtures/skill_tab_panels.js";
import { PARTY_INVENTORY_PURSE_SAMPLE, PARTY_WINDOW_PANEL_SAMPLE } from "../fixtures/party_panels.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// PartySkillTab (webclient-party-skill-tab): the party window's 技能 tab,
// rendered inside the real PartyWindow for side by side review with
// Design/PartyMemberManagement (the skill browsing and freeform-scale stories,
// SkillInCombat) at both viewport sizes. The viewed member is the companion
// 蕾娜:
//   * Book — her field heal 治癒之光 selected: target, cost and the field
//     capability, the booked practice (修煉中), proficiency, the lineage
//     position 祈禱 → 治癒之光 → 群體治癒 and the 施放 / 排入修煉 bar; the
//     fresh 群體治癒 carries 新 and the capped 寒霜之觸 見頂;
//   * FreeformScales — the ice entry 冰錐術 with her water mastery: the
//     威力與消耗 row with three unlocked rungs and two locked at 需 Lv 6 / 10,
//     and the combat-only capability with 施放's committed reason;
//   * NoMastery — the same skill without the mastery: no 威力與消耗 row;
//   * InCombat — both actions disabled with their committed reasons.
// Deterministic and offline; selecting is local and every request is inert.

export default {
  title: "Overlays/PartySkillTab",
  component: PartySkillTab,
  parameters: windowViewportParameters,
};

const STATES = {
  book: { character: CHARACTER_SKILL_COMPANION_SAMPLE, skill: "healing_light", combat: false },
  scales: { character: CHARACTER_SKILL_LADDER_SAMPLE, skill: "ice_shard", combat: false },
  noMastery: { character: CHARACTER_SKILL_NO_MASTERY_SAMPLE, skill: "ice_shard", combat: false },
  combat: { character: CHARACTER_SKILL_COMPANION_SAMPLE, skill: "healing_light", combat: true },
};

const render = (args) => ({
  setup() {
    const scope = `story|skills|${args.state}`;
    rememberPartyWindowTab(scope, "skills");
    const state = STATES[args.state];
    return () =>
      h("div", { style: "position: relative; width: 100%; height: 100vh; background: var(--ink-950, #0d0a12); overflow: hidden;" }, [
        h(PartyWindow, {
          party: PARTY_WINDOW_PANEL_SAMPLE,
          partyInventory: PARTY_INVENTORY_PURSE_SAMPLE,
          character: state.character,
          combat: state.combat,
          mode: state.combat ? "combat" : "exploration",
          initialSkill: state.skill,
          memoryScope: scope,
          requestSkill: () => null,
          onClose: () => {},
        }),
      ]);
  },
});

export const BookReference = { render, args: { state: "book" }, ...atReference };
export const BookFullHd = { render, args: { state: "book" }, ...atFullHd };
export const FreeformScalesReference = { render, args: { state: "scales" }, ...atReference };
export const FreeformScalesFullHd = { render, args: { state: "scales" }, ...atFullHd };
export const NoMasteryReference = { render, args: { state: "noMastery" }, ...atReference };
export const NoMasteryFullHd = { render, args: { state: "noMastery" }, ...atFullHd };
export const InCombatReference = { render, args: { state: "combat" }, ...atReference };
export const InCombatFullHd = { render, args: { state: "combat" }, ...atFullHd };
