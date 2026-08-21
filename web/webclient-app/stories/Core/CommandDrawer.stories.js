import { h } from "vue";
import CommandDrawer from "../../components/CommandDrawer.vue";
import { COMMAND_HISTORY_SAMPLE, PROMPT_SAMPLE } from "../fixtures.js";

// CommandDrawer: the persistent bottom command line. Props: open (the
// drawer-state slice), prompt (server prompt slice, rendered through the
// preserved NarrativeMarkup pipeline), history (command-history slice).
// Events: toggle (entry button), submit(text) (one deliberate send — Enter
// or the send button, never empty/whitespace-only), focus-parent (Escape
// release). The `#inputfield` field inside `.inputfieldwrapper` and the
// `.prompt` line are preserved DOM contract.

const renderDrawer = (args) => ({
  render: () =>
    h("div", { style: "border-top: 1px solid var(--ink-700);" }, [
      h(
        "div",
        { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 13px;" },
        "（上方為敘事區域）",
      ),
      h(CommandDrawer, args),
    ]),
});

export default {
  title: "Core/CommandDrawer",
  component: CommandDrawer,
};

export const Closed = {
  render: renderDrawer,
  args: {
    open: false,
    prompt: PROMPT_SAMPLE,
    history: COMMAND_HISTORY_SAMPLE,
  },
};

export const Open = {
  render: renderDrawer,
  args: {
    open: true,
    prompt: PROMPT_SAMPLE,
    history: COMMAND_HISTORY_SAMPLE,
  },
};

export const OpenNoPrompt = {
  render: renderDrawer,
  args: {
    open: true,
    prompt: "",
    history: [],
  },
};
