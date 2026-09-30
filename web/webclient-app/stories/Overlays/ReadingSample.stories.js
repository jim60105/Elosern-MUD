import { h } from "vue";
import ReadingSample from "../../components/ReadingSample.vue";

// ReadingSample (webclient-settings-reading-preview): the settings overlay's
// local reading preview — one fixed line set like a message-window page at
// the chosen prose scale, typed at the rate the message window would use.
// Offline and deterministic: it reads only its props and touches no store.
// The instant and reduced-motion stories show the line in full at once, so
// their captures never catch it mid-type.

const ground = (args) => ({
  render: () =>
    h(
      "div",
      { style: "padding: 32px; background: var(--ink-950); min-height: 100vh; box-sizing: border-box;" },
      [h(ReadingSample, args)],
    ),
});

export default {
  title: "Overlays/ReadingSample",
  component: ReadingSample,
};

export const Default = {
  render: ground,
  args: { fontScale: 1, textSpeed: "normal", motionLevel: "full" },
};

export const LargestScaleSlow = {
  render: ground,
  args: { fontScale: 1.12, textSpeed: "slow", motionLevel: "full" },
};

export const Instant = {
  render: ground,
  args: { fontScale: 0.92, textSpeed: "instant", motionLevel: "full" },
};

// Any effective motion level other than 完整 shows the line at once,
// whatever the chosen speed (the message window's reading contract).
export const MotionReduced = {
  render: ground,
  args: { fontScale: 1, textSpeed: "slow", motionLevel: "reduced" },
};
