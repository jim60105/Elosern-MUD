import { h, nextTick, onMounted } from "vue";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab } from "../../components/party-window-memory.js";
import { ART_PANEL_SAMPLE } from "../fixtures.js";
import {
  COMPANION_PORTRAIT_CATALOG,
  PARTY_INVENTORY_PURSE_SAMPLE,
  PARTY_MEMBER_COMPANION_SAMPLE,
  PARTY_MEMBER_KNOCKED_OUT_SAMPLE,
  PARTY_MEMBER_PANEL_SAMPLE,
  PARTY_WINDOW_INVITE_DISABLED_TARGETS,
  PARTY_WINDOW_PANEL_SAMPLE,
} from "../fixtures/party_panels.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// PartyWindow (webclient-party-window-member-tab): the one party window on
// the shared WindowFrame, its member rail (the commander first, then the
// companions, 空位 while the general quota has room) and the 成員 tab, for
// side by side review with Design/PartyMemberManagement at both viewport
// sizes. Each story is one member state — a companion, the commander, a
// knocked-out companion, and 空位 with a gated invite. Deterministic and
// offline; selecting and dispatching are inert here.

export default {
  title: "Overlays/PartyWindow",
  component: PartyWindow,
  parameters: windowViewportParameters,
};

const ART = {
  ...ART_PANEL_SAMPLE,
  portrait_catalog: { ...(ART_PANEL_SAMPLE.portrait_catalog || {}), ...COMPANION_PORTRAIT_CATALOG },
};

const STATES = {
  companion: { viewed: 101, partyMember: PARTY_MEMBER_COMPANION_SAMPLE },
  commander: { viewed: 42, partyMember: PARTY_MEMBER_PANEL_SAMPLE },
  knockedOut: { viewed: 102, partyMember: PARTY_MEMBER_KNOCKED_OUT_SAMPLE },
  // The rail's 空位 entry is a local selection; the story opens it by
  // activating the entry once mounted.
  emptySlot: { viewed: 42, partyMember: PARTY_MEMBER_PANEL_SAMPLE, empty: true },
};

const render = (args) => ({
  setup() {
    const state = STATES[args.state];
    const scope = `story|${args.state}`;
    rememberPartyWindowTab(scope, "member");
    if (state.empty) {
      onMounted(async () => {
        await nextTick();
        document.querySelector('[data-testid="member-rail__entry--empty"]')?.click();
      });
    }
    return () =>
      h("div", { style: "position: relative; width: 100%; height: 100vh; background: var(--ink-950, #0d0a12); overflow: hidden;" }, [
        h(PartyWindow, {
          party: { ...PARTY_WINDOW_PANEL_SAMPLE, viewed_member_id: state.viewed },
          partyMember: state.partyMember,
          partyInventory: PARTY_INVENTORY_PURSE_SAMPLE,
          artPanel: ART,
          interactTargets: PARTY_WINDOW_INVITE_DISABLED_TARGETS,
          memoryScope: scope,
          onClose: () => {},
        }),
      ]);
  },
});

export const CompanionReference = { render, args: { state: "companion" }, ...atReference };
export const CompanionFullHd = { render, args: { state: "companion" }, ...atFullHd };
export const CommanderReference = { render, args: { state: "commander" }, ...atReference };
export const CommanderFullHd = { render, args: { state: "commander" }, ...atFullHd };
export const KnockedOutReference = { render, args: { state: "knockedOut" }, ...atReference };
export const KnockedOutFullHd = { render, args: { state: "knockedOut" }, ...atFullHd };
export const EmptySlotReference = { render, args: { state: "emptySlot" }, ...atReference };
export const EmptySlotFullHd = { render, args: { state: "emptySlot" }, ...atFullHd };
