import { h } from "vue";
import PartyStrip from "../../components/PartyStrip.vue";
import {
  PARTY_PANEL_EMPTY_SAMPLE,
  PARTY_PANEL_SAMPLE,
  PARTY_PANEL_FULL_SAMPLE,
  PARTY_COMBAT_PARTICIPANTS_SAMPLE,
  ART_PANEL_SAMPLE,
} from "../fixtures.js";

// PartyStrip (webclient-align-05-party-hud; webclient-avg-stage-hud-anchors
// design D3): the compact companion quickbar (.comps) stories — two
// companions (with combat token badges), a full party of four, and an empty
// party, which renders nothing. No invite padding cells. The frame is the
// `vitals` anchor's width at 1920x1080 (298px); `NarrowAnchor` is its
// narrowest width, 184px at 1280x720.

export default {
  title: "Overlays/PartyStrip",
  component: PartyStrip,
};

const renderStrip = ({ width = 298, ...props }) => ({
  render: () =>
    h(
      "div",
      {
        style:
          `position: relative; width: ${width}px; padding: 16px; background: var(--ink-950, #0d0a12);`,
      },
      [h(PartyStrip, props)],
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
  // An empty party renders nothing (webclient-retire-redundant-hud).
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

export const NarrowAnchor = {
  render: renderStrip,
  args: {
    slots: PARTY_PANEL_FULL_SAMPLE.slots,
    combatParticipants: [],
    artPanel: ART_PANEL_SAMPLE,
    width: 184,
  },
};
