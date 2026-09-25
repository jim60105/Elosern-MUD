// Controls reference (H5, webclient-hud-05-overlays-and-command-line,
// task 6.6): the client's own key and command reference, rendered as the
// help overlay's control section. This is the single client-owned source of
// truth for what the client binds; the help overlay renders only what the
// client implements — no authored game-help content, no placeholders. The
// game's own `help` command output is reached by typing `help` into the
// command field (the client knows this path, and states it).
export const CONTROLS_REFERENCE = [
  {
    key: "/",
    label: "Open the command line",
    detail: "Expands the collapsed line and focuses its field; no literal slash is inserted.",
  },
  {
    key: "Enter",
    label: "Send the command",
    detail:
      "A single send path; a successful send collapses the line and returns to the dock; Shift+Enter inserts a newline without sending. Enter or Space on the focused message window first shows a typing page in full, then advances a page.",
  },
  {
    key: "↑ / ↓",
    label: "Walk the command history",
    detail: "The unsent draft is preserved across the walk.",
  },
  {
    key: "Esc",
    label: "Close the topmost open surface",
    detail:
      "Precedence: open overlay → open drawer → focused command field (collapses the line) → dock menu level.",
  },
  {
    key: "Tab",
    label: "Complete the command draft",
    detail:
      "Inside the command field: complete against history and the room's exits and targets; several matches cycle (Shift+Tab reverses), and focus never leaves the field (Escape returns it). Inside a focus-trapped surface it cycles focus; hidden and disabled controls are skipped.",
  },
  {
    key: "1-4",
    label: "Pick a dock row by position",
    detail:
      "Moves the dock focus to the first four rows of the current frame (in rendered order) and runs it like Enter; a slot beyond the row count does nothing.",
  },
  {
    key: "日誌",
    label: "Open the complete log",
    detail: "Opens the complete log at its latest line.",
  },
];

// The single line stating how the game's own help output is reached (task
// 6.6: one line, not a placeholder for the absent authored guide).
export const GAME_HELP_PATH = "Type `help` into the command field to reach the game's own help output.";

export function controlsReferenceSection() {
  return {
    entries: CONTROLS_REFERENCE,
    gameHelpPath: GAME_HELP_PATH,
  };
}
