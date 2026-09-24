import { h } from "vue";
import CommandLine from "../../components/CommandLine.vue";
import { COMMAND_HISTORY_SAMPLE, PROMPT_SAMPLE } from "../fixtures.js";

// CommandLine (H5, webclient-hud-05-overlays-and-command-line;
// webclient-collapsible-command-line design D1/D3/D4): the 44px command-line
// bar (prompt chevron, `#inputfield` + send control, hint cluster, and
// history controls — no utility openers). The stories below cover ordinary
// command entry and a locked client (a rejected send preserves the typed speech).

const renderLine = (args) => ({
  render: () =>
    h("div", { style: "height: 44px; border-top: 1px solid var(--ink-700);" }, [h(CommandLine, args)]),
});

export default {
  title: "Core/CommandLine",
  component: CommandLine,
};

export const Exploration = {
  render: renderLine,
  args: {
    prompt: PROMPT_SAMPLE,
    history: COMMAND_HISTORY_SAMPLE,
    connected: true,
    mutationsLocked: false,
    textToHtml: true,
  },
};

export const LockedClient = {
  render: renderLine,
  args: {
    prompt: "",
    history: COMMAND_HISTORY_SAMPLE,
    connected: false,
    mutationsLocked: true,
    textToHtml: false,
  },
};

export const NoPrompt = {
  render: renderLine,
  args: {
    prompt: "",
    history: [],
    connected: true,
    mutationsLocked: false,
    textToHtml: true,
  },
};
