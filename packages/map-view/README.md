# @elosern/map-view

Host-neutral map view primitives, shared by the game's area/world maps and
the standalone map editor. One source for the geometry both need, so a shape
is never copied and never approximated differently in a second implementation.

## What it owns

| Module | Values |
| --- | --- |
| `values.js` | `view {cx, cy, span}`, `frame {width, height}`, `point {x, y}`, `rect {left, top, right, bottom}`, `bounds {minX, minY, maxX, maxY}`, `unit {key, metres}`, `stop {key, label, span}`, and their validation |
| `projection.js` | one uniform scale `k = frame.width / view.span`, north-positive source coordinates, screen-only north inversion, exact `project`/`unproject` inverses |
| `navigation.js` | pixel pan, pointer-anchored zoom (also under clamped span limits), wheel factor, whole-map fit, recentre, host-inset rectangle, edge clamp |
| `units.js` | metre/kilometre/provider-cell units, distance captions, scale bar |
| `cells.js` | provider cell rect, cell centre, cell lookup |
| `bounds.js` | metric bounds/points, no fabricated coordinate, neighbourhood bounds |
| `stops.js` | stop ordering/dedupe, nearest stop, plus/minus stepping, continuous-zoom limits |
| `labels.js` | text-width estimate, box overlap, road crossing, greedy priority placement |
| `lattice.js` | scale-true dot lattice (geometry only; the caption is the host's) |
| `glyph.js` | painted glyph metrics, gate arch path, footprint of a glyph input at a surface scale |
| `theme.js` | theme roles, defaults, `resolveTheme`, `themeVars` |

## Host inputs

A host supplies everything that is its own policy:

- **Unit and stops.** Coordinates stay in the host's unit; the host states its
  unit (`UNITS.m`, `UNITS.km`, `cellUnit(metres)`) and builds its own stop
  table with `createStop`/`orderedStops` — the spans and their labels are
  host content, never package content.
- **Chrome.** The host measures its own floating controls and detail panel and
  passes a rectangle in (`insetRect` with `reservedRight`). No function here
  queries the DOM.
- **Glyph input.** `glyphFootprint({ state, gateway, haloTarget }, size)`
  takes an explicit descriptor; the package never reads a payload node.
- **Theme.** `resolveTheme(roles)` completes a host theme and
  `themeVars(theme)` returns `--map-view-*` custom properties for the host to
  bind on its surface. The package ships no stylesheet and names no host token.

Every function returns a frozen value and never mutates its input. Invalid
programmer input (non-finite numbers, non-positive frame/span/scale) throws
`TypeError`/`RangeError` instead of leaking `NaN` into view state.

## Boundary

The package MUST NOT contain, and the boundary test enforces:

- no import of a game/editor store, OOB protocol, transport, route or command;
- no import of host shell CSS, no CSS file, no game design token
  (`--gold-*`, `--paper-*`, `--seal-*`, `--map-*` outside the package's own
  `--map-view-*` namespace);
- no DOM/global access (`document`, `window`, `globalThis`, `fetch`,
  `WebSocket`, `localStorage`) and no timers;
- no fabricated player: nothing here invents a current node, a lane, a
  visibility state, a fog rule or a travel descriptor;
- only relative `./x.js` imports inside `src/` (no bare specifiers at all).

Those concerns belong to the hosts: the game area map owns fog, the current
player, quest markers and travel actions; the editor owns selection and its own
document state. Both consume the same primitives.

## Tests

`node --test tests/*.test.js` (no Vitest, no dependencies). The suite covers
synthetic round-trip/anchor/scale behaviour of the primitives plus the static
boundary rules above. Consumer behaviour stays with the consumers' own
component suites.
