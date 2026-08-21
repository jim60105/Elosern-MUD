import { h } from "vue";
import ChoiceCardRow from "../../components/ChoiceCardRow.vue";
import { SUGGESTIONS_READY_SAMPLE } from "../fixtures.js";

// ChoiceCardRow: the choice-card frame — the row of OptionCards for one
// suggestion set, shared by the dock suggestions section and the narrative
// choice-point (one card renderer). Props: cards (the exact server-authored
// cards). Event: action (each card's exact OOB action intent, re-emitted).

const renderRow = (args) => ({
  render: () =>
    h("div", { style: "max-width: 900px;" }, [h(ChoiceCardRow, args)]),
});

export default {
  title: "Action/ChoiceCardRow",
  component: ChoiceCardRow,
};

export const ReadyRow = {
  render: renderRow,
  args: { cards: SUGGESTIONS_READY_SAMPLE.cards },
};
