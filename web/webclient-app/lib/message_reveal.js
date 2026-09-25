// The message window's typewriter reveal (docs/superpowers/specs/2026-09-23-
// webclient-avg-stage-redesign-design.md §6.3–§6.4; OpenSpec change
// webclient-typewriter-reading-prefs, design D2/D4/D7). Pure: no Vue, no
// DOM. It works on the page and fragment shapes of `message_pages.js`.
//
// A reveal unit is one code point of text or one hard break, the same unit
// the page fragments' `start` / `end` offsets count. A page's units are the
// sum of its fragments' `end − start`; offsets may skip a dropped leading
// break at a page cut, so `last.end − first.start` is NOT the unit count.

export const TEXT_SPEEDS = Object.freeze(["slow", "normal", "fast", "instant"]);

// Characters per second; `instant` has no rate (see `cpsFor`).
export const TEXT_SPEED_CPS = Object.freeze({ slow: 20, normal: 45, fast: 90 });

export const AUTO_ADVANCE_BASE_MS = 1200;
export const AUTO_ADVANCE_PER_UNIT_MS = 60;

// The typing rate of a speed: `Infinity` for `instant` and for any value
// outside `TEXT_SPEEDS` that is not a known rate (callers validate first).
export function cpsFor(speed) {
  return Object.prototype.hasOwnProperty.call(TEXT_SPEED_CPS, speed)
    ? TEXT_SPEED_CPS[speed]
    : Infinity;
}

function fragmentsOf(page) {
  return page && Array.isArray(page.blocks) ? page.blocks : [];
}

function fragmentLength(fragment) {
  const length = fragment ? fragment.end - fragment.start : 0;
  return Number.isFinite(length) && length > 0 ? length : 0;
}

function clampCount(page, n) {
  const total = pageUnits(page);
  if (typeof n !== "number" || !(n > 0)) {
    return 0;
  }
  return Math.min(total, Math.floor(n));
}

export function pageUnits(page) {
  let total = 0;
  for (const fragment of fragmentsOf(page)) {
    total += fragmentLength(fragment);
  }
  return total;
}

// A box-drawing map fragment is revealed whole: a count that falls inside
// one moves to its end.
export function snapUnits(page, n) {
  const count = clampCount(page, n);
  let before = 0;
  for (const fragment of fragmentsOf(page)) {
    const length = fragmentLength(fragment);
    if (count > before && count < before + length) {
      return fragment.mapArt ? before + length : count;
    }
    before += length;
  }
  return count;
}

// The revealed count of each fragment, in page order, each in [0, length].
export function fragmentReveal(page, n) {
  let remaining = clampCount(page, n);
  return fragmentsOf(page).map((fragment) => {
    const length = fragmentLength(fragment);
    const shown = Math.min(length, remaining);
    remaining -= shown;
    return shown;
  });
}

// The response offset of the page-local count `n`: the offset of the next
// unit to reveal, or the page's end offset once every unit is revealed.
export function offsetAtUnits(page, n) {
  const fragments = fragmentsOf(page);
  if (fragments.length === 0) {
    return 0;
  }
  let remaining = clampCount(page, n);
  for (const fragment of fragments) {
    const length = fragmentLength(fragment);
    if (remaining < length) {
      return fragment.start + remaining;
    }
    remaining -= length;
  }
  return fragments[fragments.length - 1].end;
}

// The page-local count of the units before the response offset `offset`.
// An offset in a dropped-break gap counts as the start of the next fragment;
// an offset before the page is 0; an offset at or past its end is the
// page's unit count.
export function unitsAtOffset(page, offset) {
  const target = typeof offset === "number" && Number.isFinite(offset) ? offset : 0;
  let before = 0;
  for (const fragment of fragmentsOf(page)) {
    const length = fragmentLength(fragment);
    if (target < fragment.start) {
      return before;
    }
    if (target < fragment.start + length) {
      return before + (target - fragment.start);
    }
    before += length;
  }
  return before;
}

// How long a fully shown page waits before auto-advance: 1.2s plus 60ms per
// reveal unit.
export function autoAdvanceDelayMs(page) {
  return AUTO_ADVANCE_BASE_MS + AUTO_ADVANCE_PER_UNIT_MS * pageUnits(page);
}

// Oversize pages need scrolling and maps need study the character formula
// does not model: neither auto-advances.
export function autoAdvanceAllowed(page) {
  if (!page || page.oversize) {
    return false;
  }
  return !fragmentsOf(page).some((fragment) => fragment && fragment.mapArt);
}
