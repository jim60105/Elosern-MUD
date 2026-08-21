<script>
import { h, ref, watch } from "vue";
import NarrativeMarkup from "../lib/narrative_markup.js";
import { renderNarrativeTokens } from "./narrative-renderer.js";

// Command drawer (the bottom persistent command line, always one key away):
// defaults closed behind a real, focusable entry button, opens on activation
// or on `/`, and owns the input contract: Enter sends exactly one command,
// Shift+Enter adds a newline, Slash stays literal text inside the field,
// ArrowUp/ArrowDown walk the command-history slice, and Escape releases
// focus back to the parent surface.
//
// Preserved hooks: the `#inputfield` field inside its `.inputfieldwrapper`
// wrapper and the `.prompt` line (Phase-0 audit §2.3). The prompt line is a
// server-transformed stream and renders through the preserved NarrativeMarkup
// pipeline; typed commands render as echo lines through the feed, never here.
//
// Passive contract: the `open` state is a prop slice the parent (AppShell
// now, the store-backed shell later) owns; this component emits the user
// intents — `toggle` (entry button), `submit(text)` (one deliberate send),
// and `focus-parent` (Escape release). The row layout is dynamic (the field
// and prompt appear with the open state), so the component renders vnodes
// directly (setup returns the render function).
export default {
  name: "CommandDrawer",
  props: {
    open: { type: Boolean, default: false },
    prompt: { type: String, default: "" },
    history: { type: Array, default: () => [] },
  },
  emits: ["toggle", "submit", "focus-parent"],
  setup(props, { emit, expose }) {
    const field = ref(null);
    const draft = ref("");

    // Command-history walk state: null = not walking; otherwise the index
    // into `props.history`, with the draft preserved across the walk.
    let historyIndex = null;
    let draftBackup = "";

    function resetHistoryWalk() {
      historyIndex = null;
      draftBackup = "";
    }

    function promptNodes() {
      const text = props.prompt == null ? "" : String(props.prompt);
      if (text === "") {
        return [];
      }
      return renderNarrativeTokens(NarrativeMarkup.tokenize(text));
    }

    function submit() {
      const text = draft.value;
      if (text.trim() === "") {
        return false;
      }
      emit("submit", text);
      draft.value = "";
      resetHistoryWalk();
      return true;
    }

    function onKeyDown(event) {
      if (event.key === "Enter") {
        if (event.shiftKey) {
          return; // newline: the textarea's default behavior
        }
        event.preventDefault();
        submit();
        return;
      }
      if (event.key === "Escape") {
        event.preventDefault();
        resetHistoryWalk();
        emit("focus-parent");
        return;
      }
      if (event.key === "ArrowUp") {
        const history = props.history;
        if (!history.length) {
          return;
        }
        if (historyIndex === null) {
          draftBackup = draft.value;
          historyIndex = history.length - 1;
        } else if (historyIndex > 0) {
          historyIndex -= 1;
        }
        event.preventDefault();
        draft.value = history[historyIndex];
        return;
      }
      if (event.key === "ArrowDown") {
        if (historyIndex === null) {
          return;
        }
        const history = props.history;
        if (historyIndex < history.length - 1) {
          historyIndex += 1;
          draft.value = history[historyIndex];
        } else {
          draft.value = draftBackup;
          resetHistoryWalk();
        }
        event.preventDefault();
      }
    }

    function onEntryClick() {
      emit("toggle");
    }

    watch(
      () => props.open,
      (value) => {
        if (!value) {
          resetHistoryWalk();
        }
      },
    );

    // The shell opens the drawer with `/` and needs to move focus into the
    // field after the open state has rendered.
    function focusField() {
      if (props.open) {
        field.value?.focus();
      }
    }

    expose({ focusField });

    return () => {
      const nodes = [
        h(
          "button",
          {
            type: "button",
            class: "drawer-entry",
            "data-testid": "command-drawer-entry",
            "aria-expanded": props.open ? "true" : "false",
            onClick: onEntryClick,
          },
          "指令輸入（/）",
        ),
      ];
      if (props.open) {
        nodes.push(
          h("div", { class: "prompt drawer-prompt", "data-testid": "command-drawer-prompt" }, promptNodes()),
        );
        nodes.push(
          h("div", { class: "inputfieldwrapper" }, [
            h("textarea", {
              ref: field,
              id: "inputfield",
              class: "inputfield",
              "data-testid": "command-drawer-input",
              "aria-label": "指令輸入",
              spellcheck: "false",
              rows: 1,
              value: draft.value,
              onKeydown: onKeyDown,
              onInput: (event) => {
                draft.value = event.target.value;
              },
            }),
            h(
              "button",
              {
                type: "button",
                class: "inputsend",
                "aria-label": "送出指令",
                "data-testid": "command-drawer-send",
                onClick: submit,
              },
              ">",
            ),
          ]),
        );
      }
      return h(
        "div",
        {
          class: "elosern elosern-drawer",
          "data-testid": "command-drawer",
          "data-open": props.open ? "true" : "false",
        },
        nodes,
      );
    };
  },
};
</script>

<style>
.elosern-drawer {
  box-sizing: border-box;
  border-top: var(--line);
  background: var(--panel);
}

.elosern-drawer .drawer-entry {
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-500);
  background: transparent;
  border: none;
  padding: 6px var(--sp-5);
  cursor: pointer;
}

.elosern-drawer .drawer-entry:hover {
  color: var(--paper-100);
}

.elosern-drawer .drawer-prompt {
  max-width: 72ch;
  margin: 0 auto;
  padding: 0 var(--sp-6) 2px;
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  color: var(--paper-300);
  white-space: pre-wrap;
}

.elosern-drawer .drawer-prompt:empty {
  display: none;
}

.elosern-drawer .inputfieldwrapper {
  max-width: 72ch;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: var(--sp-2);
  padding: 0 var(--sp-4) var(--sp-3);
}

.elosern-drawer .inputfield {
  flex: 1 1 auto;
  resize: none;
  min-height: 38px;
  max-height: 120px;
  padding: var(--sp-2) var(--sp-3);
  font-family: var(--f-mono);
  font-size: var(--text-body);
  color: var(--paper-50);
  background: var(--ink-900);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.elosern-drawer .inputsend {
  font-family: var(--f-mono);
  font-size: var(--text-body);
  color: var(--paper-50);
  background: var(--seal-600);
  border: 1px solid var(--seal-400);
  border-radius: var(--radius-sm);
  width: 38px;
  height: 38px;
  cursor: pointer;
}

.elosern-drawer .inputsend:hover {
  background: var(--seal-500);
}
</style>
