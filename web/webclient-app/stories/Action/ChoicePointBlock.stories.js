import { h } from "vue";
import ChoicePointBlock from "../../components/ChoicePointBlock.vue";
import {
  SUGGESTIONS_GENERATING_SAMPLE,
  SUGGESTIONS_READY_SAMPLE,
} from "../fixtures.js";

// ChoicePointBlock: the narrative stream-end choice-point block. Props:
// suggestions (the committed context_actions v5 suggestions envelope; the
// stream renders only `generating` and `ready` — anything else mounts
// nothing through the preserved choice-point reducer). Event: action (the
// card intents plus the shared options.dismiss control). The block is a
// single stateless root: the narrative stream owns its position, so newer
// text can move it to the stream end without re-creating it.

const renderBlock = (args) => ({
  render: () =>
    h(
      "div",
      {
        style:
          "max-width: 720px; padding: 12px; font-family: var(--f-serif); color: var(--paper-100);",
      },
      [h(ChoicePointBlock, args)],
    ),
});

// The stream context: the block sits at the narrative end, beneath the
// latest text (the moved-to-end position the C3 stream owns).
const renderStreamEnd = (args) => ({
  render: () =>
    h(
      "div",
      {
        style:
          "max-width: 720px; padding: 12px; font-family: var(--f-serif); color: var(--paper-100); line-height: 1.82;",
      },
      [
        h(
          "p",
          { style: "margin: 0 0 8px 0;" },
          "夜色沉靜，霧燈在街角明滅。",
        ),
        h(ChoicePointBlock, args),
      ],
    ),
});

export default {
  title: "Action/ChoicePointBlock",
  component: ChoicePointBlock,
};

export const Generating = {
  render: renderBlock,
  args: { suggestions: SUGGESTIONS_GENERATING_SAMPLE },
};

export const Ready = {
  render: renderBlock,
  args: { suggestions: SUGGESTIONS_READY_SAMPLE },
};

export const StreamEnd = {
  render: renderStreamEnd,
  args: { suggestions: SUGGESTIONS_READY_SAMPLE },
};
