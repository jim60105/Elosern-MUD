import { h } from "vue";
import HelpOverlay from "../../components/HelpOverlay.vue";
import { ONBOARDING_GUIDE_SAMPLE } from "../fixtures.js";

// HelpOverlay (B5 full-overlays family): the full-viewport help dialog
// backed by the game-authored onboarding guide — the arrival scene, the
// South-Gate guard's guidance, and the keyword Q&A. The fixture is the
// single source for the showcased content (no invented help copy); the
// "Bare" story keeps only the arrival section, showing that the component
// renders exactly what the data gives (the truthful-data rule).

const renderOverlay = (args) => ({ render: () => h(HelpOverlay, args) });

export default {
  title: "Overlays/HelpOverlay",
  component: HelpOverlay,
};

export const Default = {
  render: renderOverlay,
  args: { guide: ONBOARDING_GUIDE_SAMPLE },
};

// Arrival-only guide (no guard, no Q&A): a minimal, truthfully rendered
// surface.
export const Bare = {
  render: renderOverlay,
  args: {
    guide: { arrival: ONBOARDING_GUIDE_SAMPLE.arrival },
  },
};
