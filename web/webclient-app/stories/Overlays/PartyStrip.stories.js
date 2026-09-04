import { h } from "vue";
import PartyStrip from "../../components/PartyStrip.vue";
import {
  PARTY_PANEL_EMPTY_SAMPLE,
  PARTY_PANEL_SAMPLE,
  PARTY_PANEL_FULL_SAMPLE,
  PARTY_COMBAT_PARTICIPANTS_SAMPLE,
  ART_PANEL_SAMPLE,
} from "../fixtures.js";

// PartyStrip (webclient-align-05-party-hud):
// the left-HUD companion quickbar (.comps) stories — empty, two companions
// (with combat token), full four companions, and missing-portrait fallback.

export default {
  title: "Overlays/PartyStrip",
  component: PartyStrip,
};

const renderStrip = (args) => ({
  render: () =>
    h(
      "div",
      {
        style:
          "position: relative; width: 280px; padding: 16px; background: var(--ink-950, #0d0a12);",
      },
      [h(PartyStrip, args)],
    ),
});

export const TwoCompanions = {
  render: renderStrip,
  args: {
    slots: PARTY_PANEL_SAMPLE.slots,
    combatParticipants: PARTY_COMBAT_PARTICIPANTS_SAMPLE,
    artPanel: ART_PANEL_SAMPLE,
  },
};

export const EmptyParty = {
  render: renderStrip,
  args: {
    slots: PARTY_PANEL_EMPTY_SAMPLE.slots,
    combatParticipants: [],
    artPanel: null,
  },
};

export const FullParty = {
  render: renderStrip,
  args: {
    slots: PARTY_PANEL_FULL_SAMPLE.slots,
    combatParticipants: PARTY_COMBAT_PARTICIPANTS_SAMPLE,
    artPanel: null,
  },
};
