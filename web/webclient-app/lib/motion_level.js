// The motion level (OpenSpec change webclient-motion-level, design D1/D6;
// docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md
// §9.1/§9.2). Pure: no Vue, no DOM, no side effects.
//
// One resolved value the whole client reads. The store resolves it once and
// writes the effective level to `<html data-motion>`; the stylesheet's
// `--motion-*` token blocks and the script (the message window's typing, and
// later the combat beat player) both read that one value, so they cannot
// disagree.
//
// A stored level wins. While nothing is stored the operating system's
// `prefers-reduced-motion: reduce` preference decides: `reduced` when it
// requests reduced motion, `full` otherwise. A stored value outside
// `MOTION_LEVELS` is treated as nothing stored.
export const MOTION_LEVELS = Object.freeze(["full", "reduced", "off"]);

export function resolveMotionLevel(stored, osRequestsReduce) {
  if (MOTION_LEVELS.includes(stored)) {
    return stored;
  }
  return osRequestsReduce ? "reduced" : "full";
}
