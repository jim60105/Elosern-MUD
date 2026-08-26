import { h } from "vue";
import SettingsOverlay from "../../components/SettingsOverlay.vue";

// SettingsOverlay (B5 overlay family): the full-viewport settings dialog —
// client-local options (type scale, reduced motion, the text-to-HTML
// narrative toggle, colorblind-safe status palette). All preferences are
// client-local: the store persists them through the versioned layout store
// and applies them to the document's presentation tokens immediately. They
// dispatch no `ui_action` (webclient-component-showcase: "the settings
// surface offers no control it does not implement").

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
  args: { reducedMotion: "on" },
};

export const HtmlNarrative = {
  render: renderOverlay,
  args: { textToHtml: true },
};

export const Colorblind = {
  render: renderOverlay,
  args: { colorblind: true },
};
