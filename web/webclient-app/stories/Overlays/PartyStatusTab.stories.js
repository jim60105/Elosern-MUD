import { h } from "vue";
import PartyStatusTab from "../../components/PartyStatusTab.vue";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab } from "../../components/party-window-memory.js";
import {
  CHARACTER_PANEL_SAMPLE,
  CHARACTER_PANEL_UNDISGUISED_SAMPLE,
  CHARACTER_STATUS_COMPANION_SAMPLE,
} from "../fixtures/character_panels.js";
import { PARTY_INVENTORY_PURSE_SAMPLE, PARTY_PANEL_EMPTY_SAMPLE, PARTY_WINDOW_PANEL_SAMPLE } from "../fixtures/party_panels.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// PartyStatusTab (webclient-party-status-tab): the party window's 狀態 tab,
// rendered inside the real PartyWindow for side by side review with
// Design/PartyMemberManagement (StatusTraitBreakdown, StatusNoGuild) at both
// viewport sizes. Every story shows true values only:
//   * TraitBreakdown — the companion 蕾娜: guild F with merit, her 魔力
//     waterfall (18 → 27 through four layers), a blessing and a fatigue,
//     and the disguise footer whose displayed values differ from the rows;
//   * SixteenLayers — the commander's 防禦 at the 16-layer bound, every
//     layer rendered without truncation (the breakdown-state story; the
//     sample also carries the worn bias-bearing and adjustment-bearing rows);
//   * NoGuild — no rank (no gem, no merit), no layers, no disguise and no
//     condition;
//   * InCombat — the same companion in combat: the tab keeps her committed
//     values instead of an unavailable reason.
// Deterministic and offline; selecting is local and dispatching is inert.

export default {
  title: "Overlays/PartyStatusTab",
  component: PartyStatusTab,
  parameters: windowViewportParameters,
};

const STATES = {
  breakdown: { party: PARTY_WINDOW_PANEL_SAMPLE, character: CHARACTER_STATUS_COMPANION_SAMPLE, trait: "magic_power", combat: false },
  sixteen: { party: PARTY_PANEL_EMPTY_SAMPLE, character: CHARACTER_PANEL_SAMPLE, trait: "defense", combat: false },
  noGuild: { party: PARTY_PANEL_EMPTY_SAMPLE, character: CHARACTER_PANEL_UNDISGUISED_SAMPLE, trait: null, combat: false },
  combat: { party: PARTY_WINDOW_PANEL_SAMPLE, character: CHARACTER_STATUS_COMPANION_SAMPLE, trait: null, combat: true },
};

const render = (args) => ({
  setup() {
    const scope = `story|status|${args.state}`;
    rememberPartyWindowTab(scope, "status");
    const state = STATES[args.state];
    return () =>
      h("div", { style: "position: relative; width: 100%; height: 100vh; background: var(--ink-950, #0d0a12); overflow: hidden;" }, [
        h(PartyWindow, {
          party: state.party,
          partyInventory: PARTY_INVENTORY_PURSE_SAMPLE,
          character: state.character,
          combat: state.combat,
          statusTrait: state.trait,
          memoryScope: scope,
          onClose: () => {},
        }),
      ]);
  },
});

export const TraitBreakdownReference = { render, args: { state: "breakdown" }, ...atReference };
export const TraitBreakdownFullHd = { render, args: { state: "breakdown" }, ...atFullHd };
export const SixteenLayersReference = { render, args: { state: "sixteen" }, ...atReference };
export const SixteenLayersFullHd = { render, args: { state: "sixteen" }, ...atFullHd };
export const NoGuildReference = { render, args: { state: "noGuild" }, ...atReference };
export const NoGuildFullHd = { render, args: { state: "noGuild" }, ...atFullHd };
export const InCombatReference = { render, args: { state: "combat" }, ...atReference };
export const InCombatFullHd = { render, args: { state: "combat" }, ...atFullHd };
