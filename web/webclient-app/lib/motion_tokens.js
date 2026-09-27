// The script-side reader of the client's motion tokens (docs/superpowers/specs/
// 2026-09-23-webclient-avg-stage-redesign-design.md §10.2; OpenSpec change
// webclient-combat-beat-queue, design D1; the reader C11a's
// webclient-motion-level contract promised).
//
// The stylesheet's `:root[data-motion="…"]` blocks own the whole motion
// vocabulary, and the store writes the EFFECTIVE level to `<html data-motion>`
// (webclient-motion-level design D1). This module reads one `--motion-*` custom
// property back out of the resolved style, so a script wait measures the same
// value the styles use and a level change applies from the next wait.
//
// 0 is the answer to every unusable input — no document (a Node gate, an SSR
// pass, an unmounted root), an empty property, or a value the token blocks
// would never declare. A missing token must never hold anything (the
// "Presentation timing never gates committed state or input" contract,
// rule 1): the caller's wait then resolves at once.
export function readMotionMs(name, root = globalThis.document?.documentElement) {
  if (!root || typeof getComputedStyle !== "function") {
    return 0;
  }
  const raw = getComputedStyle(root).getPropertyValue(name).trim();
  const m = /^(\d*\.?\d+)(ms|s)$/.exec(raw);
  return m ? Number(m[1]) * (m[2] === "s" ? 1000 : 1) : 0;
}
