import { h } from "vue";
import SettingsOverlay from "../../components/SettingsOverlay.vue";

// SettingsOverlay (B5 overlay family): the full-viewport settings dialog —
// client-local options (fonts, type scale, reduced motion, the text-to-HTML
// narrative toggle, colorblind-safe status palette). No OOB settings panel;
// each change emits the matching `options.*` OOB action envelope for the
// C-wave store to persist and dispatch.

const renderOverlay = (args) => ({ render: () => h(SettingsOverlay, args) });

export default {
  title: "Overlays/SettingsOverlay",
  component: SettingsOverlay,
};

export const Default = {
  render: renderOverlay,
  args: {},
};

export const ReducedMotionOn = {
  render: renderOverlay,
  args: { options: { reduced_motion: "on" } },
};

export const HtmlNarrative = {
  render: renderOverlay,
  args: { options: { text_to_html: true } },
};

export const Colorblind = {
  render: renderOverlay,
  args: { options: { colorblind: true } },
};
