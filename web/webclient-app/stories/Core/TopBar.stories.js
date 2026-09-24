import { h } from "vue";
import TopBar from "../../components/TopBar.vue";

// TopBar (the slim 48px header surface, webclient-avg-place-card-top-bar
// design D1). Props: connected (the transport slice), the roster slice for
// the CharacterSwitcher, and the possession banner. Location and world time
// are not here: the stage's place card states them (see Core/PlaceCard).
// The connection state pairs a glyph dot with a label and a state border,
// never color alone; the state classes are preserved DOM contract.

const renderTopBar = (args) => ({ render: () => h(TopBar, args) });

export default {
  title: "Core/TopBar",
  component: TopBar,
};

export const Connected = {
  render: renderTopBar,
  args: { connected: true },
};

export const Disconnected = {
  render: renderTopBar,
  args: { connected: false },
};

export const PossessionBannerActive = {
  render: renderTopBar,
  args: {
    connected: true,
    possessionBanner: { available: true, host_name: "小艾", since_tick: 42 },
  },
};
