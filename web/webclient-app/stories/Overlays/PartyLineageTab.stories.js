import { h } from "vue";
import PartyLineageTab from "../../components/PartyLineageTab.vue";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab } from "../../components/party-window-memory.js";
import { CHARACTER_SKILL_COMPANION_SAMPLE } from "../fixtures/skill_tab_panels.js";
import { LINEAGE_COMPANION_SAMPLE } from "../fixtures/lineage_tab_panels.js";
import { PARTY_INVENTORY_PURSE_SAMPLE, PARTY_WINDOW_PANEL_SAMPLE } from "../fixtures/party_panels.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// PartyLineageTab (webclient-party-lineage-tab): the party window's 系譜
// tab, rendered inside the real PartyWindow for side by side review with
// Design/PartyMemberManagement (LineageGraph, LineageSingleNode,
// LineageReadyToUnlock) at both viewport sizes. The viewed member is the
// companion 蕾娜, whose ledger groups four graphs under 水, 神聖 and 杖術:
//   * Graph — the seven-node 水 graph: two roots, the ready 冰霜護甲, the
//     merge node 冰晶風暴 drawn once under its two Lv 2 edges;
//   * SingleNode — the one-node, fully capped 聖水祝福 (已全數見頂);
//   * ReadyToUnlock — the 杖術 graph whose 迴旋杖 is ready (可解鎖).
// Deterministic and offline; selecting a node switches to 技能 locally and
// every request is inert.

export default {
  title: "Overlays/PartyLineageTab",
  component: PartyLineageTab,
  parameters: windowViewportParameters,
};

const GRAPHS = { graph: "frost_touch", single: "holy_water", ready: "staff_strike" };

const render = (args) => ({
  setup() {
    const scope = `story|lineage|${args.state}`;
    rememberPartyWindowTab(scope, "lineage");
    return () =>
      h("div", { style: "position: relative; width: 100%; height: 100vh; background: var(--ink-950, #0d0a12); overflow: hidden;" }, [
        h(PartyWindow, {
          party: PARTY_WINDOW_PANEL_SAMPLE,
          partyInventory: PARTY_INVENTORY_PURSE_SAMPLE,
          character: CHARACTER_SKILL_COMPANION_SAMPLE,
          lineage: LINEAGE_COMPANION_SAMPLE,
          initialGraph: GRAPHS[args.state],
          memoryScope: scope,
          requestSkill: () => null,
          onClose: () => {},
        }),
      ]);
  },
});

export const GraphReference = { render, args: { state: "graph" }, ...atReference };
export const GraphFullHd = { render, args: { state: "graph" }, ...atFullHd };
export const SingleNodeReference = { render, args: { state: "single" }, ...atReference };
export const SingleNodeFullHd = { render, args: { state: "single" }, ...atFullHd };
export const ReadyToUnlockReference = { render, args: { state: "ready" }, ...atReference };
export const ReadyToUnlockFullHd = { render, args: { state: "ready" }, ...atFullHd };
