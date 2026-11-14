import { h } from "vue";
import RiteArrivalCard from "../../components/rite/RiteArrivalCard.vue";
import RitePanel from "../../components/rite/RitePanel.vue";
import RiteBackdrop from "../../components/rite/RiteBackdrop.vue";
import { ritePerformers } from "../../components/rite/rite-model.js";
import { RITE_ART_PANEL, RITE_PARTY, ritePanel, ritePanelWithArt } from "../fixtures/rite.js";

// The landmark rite surfaces (landmark-rite-surfaces; approved prototype
// Design/LandmarkRites): the rite arrival card, the rite panel and the rite
// backdrop, each rendered alone over a synthetic committed `rite` panel.
// Nothing mounts them in the client yet and they send nothing: the card
// emits approach / leave and the panel perform(key) / leave.
//
// The cards sit in a frame sized like HudFrame's `choices` anchor over the
// dialogue stage (centred, min(560px·S, 40%) wide, from the top inset to the
// scene caption row); the backdrop fills the whole stage.

const stage = (children) =>
  h(
    "div",
    {
      style: {
        position: "relative",
        height: "calc(100vh - var(--header-h))",
        overflow: "hidden",
        background: "radial-gradient(80% 70% at 50% 40%, #2a2a33, #0b0d10)",
      },
    },
    children,
  );

const choicesAnchor = (child) =>
  stage([
    h(
      "div",
      {
        style: {
          position: "absolute",
          top: "var(--stage-inset-y)",
          bottom: "calc(var(--stage-caption-top) + 8px * var(--ui-scale))",
          left: "calc(50% - min(280px * var(--ui-scale), 20%))",
          width: "min(560px * var(--ui-scale), 40%)",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        },
      },
      [child],
    ),
  ]);

const arrival = (args) => ({
  render: () =>
    choicesAnchor(
      h(RiteArrivalCard, {
        key: JSON.stringify(args),
        rite: args.rite,
        artPanel: RITE_ART_PANEL,
        revisit: args.revisit,
        entrance: args.entrance,
      }),
    ),
});

const panel = (args) => ({
  render: () => {
    const performers = ritePerformers(args.rite);
    return choicesAnchor(
      h(RitePanel, {
        key: JSON.stringify(args),
        rite: args.rite,
        performer: performers[args.performerIndex] ?? performers[0],
        entrance: args.entrance,
      }),
    );
  },
});

const backdrop = (args) => ({
  render: () => stage([h(RiteBackdrop, { rite: args.rite, artPanel: RITE_ART_PANEL })]),
});

export default {
  title: "World/LandmarkRite",
  component: RiteArrivalCard,
  parameters: { layout: "fullscreen" },
  args: { revisit: false, entrance: true, performerIndex: 0 },
};

const LIT = { ...ritePanel().district, lit: true };

// Arriving on an unlit district's landmark: the archetype art in its 16:5
// band, nothing experienced yet, focus on 走近.
export const ArrivalCard = { name: "Arrival Card", render: arrival, args: { rite: ritePanelWithArt() } };
// The district is lit and one of the two options was experienced.
export const ArrivalCardLit = {
  name: "Arrival Card Lit",
  render: arrival,
  args: { rite: ritePanelWithArt({ district: LIT, seen: ["drink"] }) },
};
// The archetype art has not been generated: the quiet ink band.
export const ArrivalCardNoArt = { name: "Arrival Card No Art", render: arrival, args: { rite: ritePanel() } };
// Reopened from the return entry: the kicker names the rite, not the arrival.
export const ArrivalCardRevisit = {
  name: "Arrival Card Revisit",
  render: arrival,
  args: { rite: ritePanelWithArt({ district: LIT, seen: ["drink"] }), revisit: true },
};

// The rite panel: the controlled character performs, both options unseen.
export const Panel = { render: panel, args: { rite: ritePanel({ performers: RITE_PARTY }) } };
// The first option was experienced: its pip is gone.
export const PanelExperienced = {
  name: "Panel Experienced",
  render: panel,
  args: { rite: ritePanel({ performers: RITE_PARTY, seen: ["drink"] }) },
};
// A companion performs: the solo-only option is disabled with its reason.
export const PanelCompanion = {
  name: "Panel Companion",
  render: panel,
  args: { rite: ritePanel({ performers: RITE_PARTY }), performerIndex: 1 },
};
// A third option is authored.
export const PanelThreeOptions = {
  name: "Panel Three Options",
  render: panel,
  args: {
    rite: ritePanel({ options: [...ritePanel().options, { key: "listen", label: "把耳貼上水面", companion: true }] }),
  },
};

// The rite stage's ground: the archetype art under the ink wash and the
// plate naming the landmark and the guardian.
export const Backdrop = { render: backdrop, args: { rite: ritePanelWithArt() } };
// No art: quiet ink with the same plate.
export const BackdropNoArt = { name: "Backdrop No Art", render: backdrop, args: { rite: ritePanel() } };
