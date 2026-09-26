import { h } from "vue";
import SettingsOverlay from "../../components/SettingsOverlay.vue";

// SettingsOverlay (B5 overlay family): the full-viewport settings dialog —
// client-local options (type scale, the motion level, the text-to-HTML
// narrative toggle, colorblind-safe status palette, and the reading
// preferences: text speed and auto-advance). All preferences are
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
  args: { motionLevel: "full", textSpeed: "normal", autoAdvance: false },
};

// webclient-motion-level (task 4.2): the 減少 level — short fades only, and
// message pages in full at once.
export const MotionReduced = {
  render: renderOverlay,
  args: { motionLevel: "reduced" },
};

export const HtmlNarrative = {
  render: renderOverlay,
  args: { textToHtml: true },
};

export const Colorblind = {
  render: renderOverlay,
  args: { colorblind: true },
};

// webclient-typewriter-reading-prefs: a non-default text speed and
// auto-advance on.
export const ReadingPreferences = {
  render: renderOverlay,
  args: { textSpeed: "fast", autoAdvance: true },
};
