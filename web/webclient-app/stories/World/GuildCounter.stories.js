import { h } from "vue";
import GuildCounter from "../../components/GuildCounter.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// GuildCounter (quest-issuer-model change 11): the guild counter surface —
// registration, the quest board (接取), and guild rank with the promotion
// examination. It renders only the committed `services` v4 payload's guild
// section and does NOT re-list the holder's accepted quest records (the quest
// book owns them). The register / accept / exam controls emit the exact OOB
// action intents.

const renderCounter = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(GuildCounter, args),
    ]),
});

export default {
  title: "World/GuildCounter",
  component: GuildCounter,
};

export const FullCounter = {
  render: renderCounter,
  args: {
    services: SERVICES_PANEL_SAMPLE,
  },
};

export const GuildAbsent = {
  render: renderCounter,
  args: {
    services: SERVICES_PANEL_MINIMAL_SAMPLE,
  },
};

export const CounterUnavailable = {
  render: renderCounter,
  args: {
    services: SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  },
};
