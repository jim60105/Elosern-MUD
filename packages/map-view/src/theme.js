// The theme hook: which painted roles a map surface exposes and how a host
// supplies them. The package ships no stylesheet and never names a host
// token; a host resolves its own values (any CSS colour or `var(--token)`
// expression) into these roles and binds `themeVars(theme)` on its surface
// element, so a shared glyph can read `var(--map-view-<role>, <fallback>)`.
//
// Roles describe painted purpose, not a palette:
//   node         a regular node mark
//   paper        the current-position ring
//   current      the current-position dot
//   accent       a gate arch
//   accentMuted  a gate arch already seen
//   selection    any selected mark
//   halo         a travel/highlight halo

import { FREEZE } from "./values.js";

export const THEME_ROLES = FREEZE(["node", "paper", "current", "accent", "accentMuted", "selection", "halo"]);

/** Neutral default ink for a host that supplies no theme of its own. */
export const DEFAULT_THEME = FREEZE({
  node: "#e7e0d1",
  paper: "#f2ecdf",
  current: "#a52c31",
  accent: "#b99a60",
  accentMuted: "#8a7448",
  selection: "#d9c493",
  halo: "#8a7448",
});

/** The custom-property namespace `themeVars` publishes. */
export const THEME_PREFIX = "--map-view";

function requireCssValue(value, name) {
  if (typeof value !== "string" || value.trim() === "") {
    throw new TypeError(`map-view: ${name} must be a non-empty CSS value`);
  }
  return value;
}

function roleProperty(role) {
  return `${role.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}`;
}

/**
 * Completes a host theme: every role the host omits keeps the neutral
 * default, an unknown role or a non-string value is a programmer error.
 */
export function resolveTheme(input = {}) {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    throw new TypeError("map-view: theme must be an object of role values");
  }
  const out = { ...DEFAULT_THEME };
  for (const [role, value] of Object.entries(input)) {
    if (!THEME_ROLES.includes(role)) {
      throw new TypeError(`map-view: unknown theme role ${role}`);
    }
    out[role] = requireCssValue(value, `theme.${role}`);
  }
  return FREEZE(out);
}

/**
 * The custom properties a host binds on its map surface, e.g.
 * `{"--map-view-accent": "var(--gold-400)", …}`. A complete theme is
 * required, so a surface never publishes a half-filled namespace.
 */
export function themeVars(theme = DEFAULT_THEME, prefix = THEME_PREFIX) {
  requireCssValue(prefix, "prefix");
  for (const role of THEME_ROLES) {
    requireCssValue(theme?.[role], `theme.${role}`);
  }
  const out = {};
  for (const role of THEME_ROLES) out[`${prefix}-${roleProperty(role)}`] = theme[role];
  return FREEZE(out);
}
