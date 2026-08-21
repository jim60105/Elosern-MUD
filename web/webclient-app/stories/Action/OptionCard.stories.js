import { h } from "vue";
import OptionCard from "../../components/OptionCard.vue";
import { SUGGESTIONS_READY_SAMPLE } from "../fixtures.js";

// OptionCard: one context_actions v5 suggestion card — the exact
// server-authored shape { kind, action_code, label, params, hint? } rendered
// as text nodes. Event: action (the exact OOB action intent — known_action
// carries its params unchanged; freeform is explore.talk_freeform with the
// label as speech).

const renderCard = (args) => ({
  render: () =>
    h("div", { style: "max-width: 24rem;" }, [h(OptionCard, { card: args.card })]),
});

export default {
  title: "Action/OptionCard",
  component: OptionCard,
};

const KNOWN_CARD = SUGGESTIONS_READY_SAMPLE.cards[0];
const KNOWN_CARD_WITH_HINT = SUGGESTIONS_READY_SAMPLE.cards[1];
const FREEFORM_CARD = SUGGESTIONS_READY_SAMPLE.cards[3];

export const Known = {
  render: renderCard,
  args: { card: KNOWN_CARD },
};

export const KnownWithHint = {
  render: renderCard,
  args: { card: KNOWN_CARD_WITH_HINT },
};

export const Freeform = {
  render: renderCard,
  args: { card: FREEFORM_CARD },
};
