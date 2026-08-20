import { h } from "vue";
import TopBar from "../../components/TopBar.vue";
import { STATUS_SLICE_SAMPLE } from "../fixtures.js";

// TopBar (the header surface). Props: locationLabel / timeLabel (the
// status-panel and serverTime slice; null renders the `--` placeholders),
// connected (the transport slice). No emitted events: a display surface.
// The connection state pairs a glyph dot with a label and a state border,
// never color alone; the `.header-conn` hook and the state classes are
// preserved DOM contract.

const renderTopBar = (args) => ({ render: () => h(TopBar, args) });

export default {
  title: "Core/TopBar",
  component: TopBar,
};

export const Connected = {
  render: renderTopBar,
  args: STATUS_SLICE_SAMPLE,
};

export const Disconnected = {
  render: renderTopBar,
  args: {
    connected: false,
    locationLabel: "測試起點",
    timeLabel: "春季 3 日 · 12:00",
  },
};

export const NoSlice = {
  render: renderTopBar,
  args: {
    connected: false,
    locationLabel: null,
    timeLabel: null,
  },
};
