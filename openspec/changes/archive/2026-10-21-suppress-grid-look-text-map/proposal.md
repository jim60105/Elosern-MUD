# Proposal

## Why

Room look currently sends an ASCII minimap as a separate text message in addition to the room description. The webclient already has an independent map widget, so the duplicate text map interrupts the room narrative.

## What Changes

- **BREAKING (pre-release)** Disable automatic ASCII minimaps for normal `GridRoom` and `AnchorRoom` look output on every client, including Telnet and the browser. Keep the room name, description, scene flavor, contents and exits.
- Set the shared grid-room text-map default once, inherited by anchors and future maps using these typeclasses. Preserve Evennia's appearance pipeline and its existing explicit override precedence.
- Specify and test parity across localized `看` (and `look`), `at_look`, and browser `explore.look`. Capture every emitted message so a separate `xymap` message cannot escape the assertions.
- Preserve the version-1 `local_map` payload and its actionable adjacent exits, plus shortest-path lookup and `前往`/`goto` auto-walking. Leave authored map options and the frontend transport unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `grid-room-typeclasses`: add the inherited disabled text-map default and navigation-preservation contract.
- `localized-appearance`: add map-free grid-room look across text and browser entry paths without changing the shared zh-tw frame.
- `webclient-local-map`: add an explicit independence contract between the graphical payload and automatic ASCII-map output.

Each capability receives an ADDED requirement. Existing requirement names and scenario bodies remain intact. `sample-city-altoria` needs no delta because the chosen mechanism preserves its exact two-token `options` contract.

## Impact

The implementation is one class attribute and a short explanatory comment/docstring adjustment in `typeclasses/rooms.py`, with focused additions or updates in existing room, appearance, command and local-map presenter test modules. The misleading appearance test name that claims to keep the map must be replaced with a real no-map regression. Update the existing player command documentation to state the new output behavior without changing command keys, aliases, syntax or availability.

No runtime dependency, wire schema, frontend source, authored map data, setting, database migration or compatibility layer changes. Ordinary non-grid rooms and the explicit builder `地圖`/`map` command are outside the suppression scope. This is one engineer-day of implementation and focused verification.

## Batch:

```text
depends-on: none
```

| Change | Depends on | Code-conflict notes |
|---|---|---|
| `2026-10-21-suppress-grid-look-text-map` | none | Owns the GridRoom default, existing appearance/room tests, focused look/goto and local-map presenter regressions, and the two command documents. Serialize concurrent edits to those files. No active change existed when proposed. |
