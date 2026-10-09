import { h } from "vue";
import GuildCounter from "../../components/GuildCounter.vue";
import {
  SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE,
  SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE,
  SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE,
  SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// GuildCounter (quest-issuer-model change 11): the guild counter surface —
// registration, the quest board (接取), and guild rank with the promotion
// examination. It renders only the committed `services` v5 payload's guild
// section and does NOT re-list the holder's accepted quest records (the quest
// book owns them). The register / accept / exam-request controls emit the
// exact OOB action intents. The rank block shows the rank crest, a merit
// meter with an explicit met / short status (merit_qualified), and the
// 預約升等考核 request, whose enabled state is independent of merit.

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

// The full sample is the below-merit case: merit 140 of 300
// (merit_qualified false) while the counter still takes the request.
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

// The same below-merit request, named for the rank-block state it covers.
export const ExamRequestBelowMerit = {
  render: renderCounter,
  args: {
    services: SERVICES_PANEL_SAMPLE,
  },
};

// Merit meets the threshold: full meter, 功績已達標, the request emphasised.
export const ExamRequestMeritQualified = {
  render: renderCounter,
  args: {
    services: SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE,
  },
};

// S rank: no next rank, no meter, the 最高等級 crest and the top_rank reason.
export const TopRank = {
  render: renderCounter,
  args: {
    services: SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE,
  },
};

// The clerk is busy (schedule_blocked): the request renders disabled with
// her reason visible.
export const CounterBusy = {
  render: renderCounter,
  args: {
    services: SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE,
  },
};

// An unregistered holder: registration offered, no rank yet, the request
// disabled with the unregistered reason.
export const Unregistered = {
  render: renderCounter,
  args: {
    services: SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE,
  },
};
