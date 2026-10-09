import { h } from "vue";
import GuildRankCard from "../../components/GuildRankCard.vue";
import {
  SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE,
  SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE,
  SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE,
  SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE,
  SERVICES_PANEL_SAMPLE,
} from "../fixtures.js";

// GuildRankCard (quest-drawer-ui-primitives): the guild rank block extracted
// from the retired GuildCounter. It shows the rank crest, a merit meter with an explicit
// met / short status (merit_qualified), and the 預約升等考核 request, whose
// enabled state is independent of merit. It renders the `services` v5
// payload's `guild.rank` object and emits the exact exam-request intent.

// The width of the redesigned drawer's list column, where it will sit.
const renderCard = (args) => ({
  render: () =>
    h("div", { style: "width: calc(420px * var(--ui-scale)); padding: calc(16px * var(--ui-scale));" }, [
      h(GuildRankCard, args),
    ]),
});

export default {
  title: "World/GuildRankCard",
  component: GuildRankCard,
};

// Merit 140 of 300 (merit_qualified false) while the counter still takes
// the request.
export const ExamRequestBelowMerit = {
  render: renderCard,
  args: {
    rank: SERVICES_PANEL_SAMPLE.guild.rank,
  },
};

// Merit meets the threshold: full meter, 功績已達標, the request emphasised.
export const ExamRequestMeritQualified = {
  render: renderCard,
  args: {
    rank: SERVICES_PANEL_GUILD_MERIT_QUALIFIED_SAMPLE.guild.rank,
  },
};

// S rank: no next rank, no meter, the 最高等級 crest and the top_rank reason.
export const TopRank = {
  render: renderCard,
  args: {
    rank: SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE.guild.rank,
  },
};

// The clerk is busy (schedule_blocked): the request renders disabled with
// her reason visible.
export const CounterBusy = {
  render: renderCard,
  args: {
    rank: SERVICES_PANEL_GUILD_COUNTER_BUSY_SAMPLE.guild.rank,
  },
};

// An unregistered holder: no rank yet, the request disabled with the
// unregistered reason.
export const Unregistered = {
  render: renderCard,
  args: {
    rank: SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE.guild.rank,
  },
};
