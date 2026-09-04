// The quickbar chip table (webclient-align-02-quickbar-shortcuts): one
// shared source for the chip sets AND the bound-letter table, so the badge,
// the inserted text, and the client keybinding cannot drift apart (the
// badge ⇔ alias ⇔ keybinding contract). Every letter here is simultaneously
// (a) the chip's rendered badge, (b) the text the chip inserts, (c) the
// client's keybinding, and (d) an installed server command key or alias —
// pinned server-side by commands.tests.test_localized
// (QuickbarLetterPinningTests). Inserted text is the badge letter plus a
// trailing space: a complete, playable command word on every transport.
//
// The table is a plain module because `<script setup>` components cannot
// export named bindings, and three surfaces consume it: QuickWordChips.vue
// (render + click), AppShell.vue (the global letter router), and
// CommandLine.vue (Tab-completion candidates).

// The exploration chip set: 看 l / 拿 g / 說 s / 交談 t / 等待 w.
export const EXPLORATION_CHIPS = [
  { verb: "看", letter: "l" },
  { verb: "拿", letter: "g" },
  { verb: "說", letter: "s" },
  { verb: "交談", letter: "t" },
  { verb: "等待", letter: "w" },
];

// The combat chip set: 說 s / 施法 c.
export const COMBAT_CHIPS = [
  { verb: "說", letter: "s" },
  { verb: "施法", letter: "c" },
];

// The bound letters per committed mode (creation binds nothing). Derived
// from the chip sets so a letter is only ever bound where its chip renders.
export function boundLetters(mode) {
  if (mode === "exploration") {
    return EXPLORATION_CHIPS.map((chip) => chip.letter);
  }
  if (mode === "combat") {
    return COMBAT_CHIPS.map((chip) => chip.letter);
  }
  return [];
}

// The mode's chip badge letters (Tab-completion candidates).
export function chipLetters(mode) {
  return boundLetters(mode);
}
