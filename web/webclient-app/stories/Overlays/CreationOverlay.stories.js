import { h } from "vue";
import CreationOverlay from "../../components/CreationOverlay.vue";
import {
  CREATION_PANEL_SAMPLE,
  CREATION_PANEL_PRESET_DRAFT_SAMPLE,
  CREATION_PANEL_CUSTOM_DRAFT_SAMPLE,
  CREATION_PANEL_PROPOSAL_SAMPLE,
  CREATION_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// CreationOverlay (B5 overlays family): the full-viewport character-creation
// wizard for the committed `creation` v2 panel — preset pick, custom form
// (adult gate on BOTH the age and apparent_age fields, design D1), the
// concept branch (transient proposal fill, retool-concept-transient-fill),
// and the server-persisted wizard draft. Every action emits the exact
// `creation.*` OOB envelope; the offline showcase stays truthful: no
// invented preset fields, budgets, or affinity values.

const renderOverlay = (args) => ({ render: () => h(CreationOverlay, args) });

export default {
  title: "Overlays/CreationOverlay",
  component: CreationOverlay,
};

export const Default = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_SAMPLE },
};

export const PresetDraft = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_PRESET_DRAFT_SAMPLE },
};

export const CustomDraft = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_CUSTOM_DRAFT_SAMPLE },
};

export const Proposal = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_PROPOSAL_SAMPLE },
};

export const Unavailable = {
  render: renderOverlay,
  args: { creation: CREATION_PANEL_UNAVAILABLE_SAMPLE },
};
