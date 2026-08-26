import { h } from "vue";
import CommandLine from "../../components/CommandLine.vue";
import { COMMAND_HISTORY_SAMPLE, PROMPT_SAMPLE } from "../fixtures.js";

// CommandLine (H5, webclient-hud-05-overlays-and-command-line, tasks 2.6/8.1):
// the persistent command line — always rendered, no open/closed state. The
// stories below cover the exploration mode (the 看/拿/說/交談/等待 chip set),
// the combat mode (the 說/施法 set), and a locked client (a rejected send
// preserves the typed speech).

const renderLine = (args) => ({
  render: () =>
    h("div", { style: "border-top: 1px solid var(--ink-700);" }, [h(CommandLine, args)]),
});

export default {
  title: "Core/CommandLine",
  component: CommandLine,
};

export const Exploration = {
  render: renderLine,
  args: {
    mode: "exploration",
    prompt: PROMPT_SAMPLE,
    history: COMMAND_HISTORY_SAMPLE,
    connected: true,
    mutationsLocked: false,
    textToHtml: true,
  },
};

export const Combat = {
  render: renderLine,
  args: {
    mode: "combat",
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
    mode: "exploration",
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
    mode: "exploration",
    prompt: "",
    history: [],
    connected: true,
    mutationsLocked: false,
    textToHtml: true,
  },
};
