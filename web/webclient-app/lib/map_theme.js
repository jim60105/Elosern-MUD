// The game map's theme: the painted roles the shared glyphs read, expressed
// with this game's own design tokens. The package ships no stylesheet and
// knows none of these names; a map surface binds `GAME_MAP_THEME_VARS` so the
// shared glyph's `var(--map-view-<role>)` hooks resolve to the game ink.
// Every role maps to the token the surface already used, so binding or not
// binding the theme paints the same colours.

import { resolveTheme, themeVars } from "@elosern/map-view";

export const GAME_MAP_THEME = resolveTheme({
  node: "var(--paper-200)",
  paper: "var(--paper-50)",
  current: "var(--seal-deep)",
  accent: "var(--gold-400)",
  accentMuted: "var(--gold-500)",
  selection: "var(--gold-300)",
  halo: "var(--gold-500)",
});

export const GAME_MAP_THEME_VARS = themeVars(GAME_MAP_THEME);
