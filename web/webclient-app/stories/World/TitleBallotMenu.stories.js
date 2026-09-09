import { h } from "vue";
import TitleBallotMenu from "../../components/TitleBallotMenu.vue";

export default {
  title: "World/TitleBallotMenu",
  component: TitleBallotMenu,
};

const renderBallot = (args) => ({
  render: () => h("div", { style: "width:min(360px,100%)" }, [
    h(TitleBallotMenu, args),
  ]),
});

const ballot = {
  schema_version: 1,
  available: true,
  kind: "title_ballot",
  candidates: [
    { index: 1, display: "夜襲之人", basis: "夜半三度出入敵陣。" },
    { index: 2, display: "不屈之壁", basis: "重傷仍守住隘口。" },
  ],
};

export const Pending = { render: renderBallot, args: { ballot } };
export const LongBasis = {
  render: renderBallot,
  args: { ballot: { ...ballot, candidates: [{ index: 1, display: "不屈之壁", basis: "重傷仍守住隘口。".repeat(12) }] } },
};
export const Idle = { render: renderBallot, args: { ballot: { ...ballot, candidates: [] } } };
