# Design

## Context

See `proposal.md` for motivation. This is a pre-release presentation change on Evennia 6.1.0 / Python 3.13. It respects architectural decisions D3, D13 and D16 in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`: retain xyzgrid navigation, keep Telnet playable, and leave the graphical local map independent of text rendering.

### Observed code paths

Line references below were checked against the proposal checkout. Installed dependency paths are relative to `.venv/lib/python3.13/site-packages/`.

| Source | Observation |
|---|---|
| `typeclasses/rooms.py:101-138` | `GridRoom` inherits `XYZRoom` with the shared appearance mixins; `AnchorRoom` inherits `GridRoom`. Neither overrides `return_appearance`. |
| `evennia/contrib/grid/xyzgrid/xyzroom.py:277-280,395-518` | Upstream defaults `map_display = True`. `return_appearance` first computes `room_desc` at line 447, resolves the map at 451 and evaluates the display gate at 453. It calls `get_visual_range` at 502, sends `looker.msg(text=(map_display, {"type": "xymap"}), options=None)` at 516, then returns the separate `room_desc` at 518. Removing characters from the returned description cannot suppress this message. |
| `commands/localized/general.py:182-210` | `看`, with aliases `look`, `l`, `ls`, calls `caller.at_look(target)` and sends the returned description as text with `type: look`. It supplies no `map_display` override. |
| `web/webclient/actions/exploration_actions.py:457-474` | `explore.look` with `{"room": true}` resolves the current location, calls `actor.at_look(target)`, sends that appearance and returns success `looked` with the existing full refresh. It supplies no display override. |
| `web/webclient/presentation/local_map/grid.py:41-85,318-339` | The grid adapter reads `location.xyz`, `location.xymap`, `options.map_mode` and `options.map_visual_range`, then traverses node/link data. It never reads `map_display`, an ASCII string or text-message history. |
| `commands/localized/xyzgrid.py:72-103,124-234` | `CmdGoto` resolves coordinates and calls `xymap.get_shortest_path`, then follows real exits. The display gate does not participate in route computation or stepping. |
| `world/maps/altoria_capital.py:215-234`; `world/maps/village_ciaran.py:101-121` | Both authored maps declare only `map_visual_range` and `map_mode` in `options`, so the room-class display default governs normal look. |
| `typeclasses/tests/test_appearance.py:114-133` | `test_grid_room_keeps_the_map_display_and_renders_the_flavor_paragraph` uses `probe_map` without a loaded map and checks only the returned string. Despite its name, it establishes neither map presence nor map absence. Keep its flavor assertions and replace its misleading name and incomplete fixture. |

### Why the browser receives the map as narrative text

The map tuple's `{"type": "xymap"}` is message metadata, not a separate `xymap` protocol command and not a nested `options.type` field on the browser wire.

1. Installed `evennia/objects/objects.py:971-1026` retains the text tuple in `DefaultObject.msg` and forwards it through attached sessions.
2. Installed `evennia/server/sessionhandler.py:171-280,812-828` normalizes it into the `text` send instruction with positional `[map_string]` and keyword `type: xymap`; `options=None` becomes an empty `options` dict. The server sends that instruction to the portal.
3. Installed `evennia/server/portal/webclient.py:455-482` calls the negotiated codec. `wire_formats/evennia_v1.py:63-103` removes `options`, HTML-encodes the text and retains `type` in the keyword dict. The resulting JSON frame has shape `["text", [html_map], {"type": "xymap"}]`.
4. Installed `evennia/web/static/webclient/js/evennia.js:151-157,232-233,265-275` requests `v1.evennia.com`, parses that frame and emits `text` with its arguments and keyword metadata.
5. `web/webclient-app/transport.js:132-139` takes `args[0]` and appends it to console output and narrative text without inspecting the keyword metadata. This is why the separate map reaches the narrative window today.

## Goals / Non-Goals

**Goals.** Normal look in every project grid/anchor room emits only the ordinary appearance on all clients. Disable ASCII-map formatting at its existing server-side gate, while keeping the graphical map's available payload and navigation semantics unchanged.

**Non-Goals.** No browser-only setting, transport filter, replacement room formatter, map redesign, new OOB schema or typeclass migration. No change to terrain/wilderness, instance, plain room or Limbo appearance. The explicit builder `地圖`/`map` command remains available under its existing permissions. No cleanup of unrelated historical spec inconsistencies.

## Decisions

### D1. Set the shared GridRoom default

Add this ordinary, nonpersistent class attribute to `GridRoom` in `typeclasses/rooms.py`:

```python
map_display = False
```

Add a short explanation that the default disables the automatic text minimap for all clients while the webclient uses `local_map`. Adjust the existing MRO docstring's mention of map display so it describes the inherited, disabled-by-default gate accurately. `AnchorRoom` inherits the value without redeclaring it. Keep `XYZRoom.return_appearance`, its `super()` call and all caller hooks unchanged. No override method or monkey patch is needed.

Upstream precedence remains call-site `map_display` keyword > map `options["map_display"]` > room-class `map_display`. Neither normal look caller nor either shipped map overrides it. Thus all current normal grid looks stop emitting maps, including on Telnet; future maps using the same typeclasses inherit the same default without adding an option. This is a project default, not a new prohibition on Evennia's explicit developer rendering API. A deliberate call-site/map override can still request an ASCII rendering; no player toggle or exception is introduced. Acceptance fixtures use normal calls and map options without an explicit display override. Do not add `map_display: true` to authored maps.

The false gate skips ASCII `get_visual_range` formatting and the extra `msg` while retaining upstream map lookup and the returned localized appearance. Existing objects use the class value after normal code reload; no attributes, rooms or maps need rewriting.

### D2. Reject per-map options and frontend filtering

| Alternative | Reason for rejection |
|---|---|
| Add `"map_display": False` to each map's `options` | Repeats a project-wide presentation default per map and requires future authors to remember it. It also contradicts `sample-city-altoria`'s exact two-token options scenario at `openspec/specs/sample-city-altoria/spec.md:64-68`, demanding an unnecessary contract change. |
| Filter `type == "xymap"` in `transport.js` | Leaves Telnet and other text clients unchanged and still computes/sends unwanted maps. Correct filtering would need the callback's wire keyword metadata, not a guessed nested `options.type`. The server-side default handles every client without transport changes. |
| Override `return_appearance`, rewrite `at_look` or strip the returned string | Duplicates upstream logic or changes a shared hook. String stripping misses the separate message entirely. A class default already expresses the intended policy. |

### D3. Keep capability ownership narrow

Add one requirement to each of the three existing capabilities below. ADDED blocks express the new contracts without rewriting unrelated requirement/scenario bodies or changing existing canonical IDs.

| Capability / new requirement title | Observable contract | Planned substantive coverage |
|---|---|---|
| `grid-room-typeclasses` / `Grid rooms disable automatic text maps by default without disabling navigation` | Inherited default covers grid and anchor rooms; shortest paths and auto-walking survive. | `typeclasses/tests/test_rooms.py` default/inheritance assertions; a real synthetic loaded XYMap in appearance coverage; synthetic known-route cases in `commands/tests/test_localized/test_xyz_grid_and_help.py`. |
| `localized-appearance` / `Grid room look emits the ordinary appearance without an automatic ASCII map` | Text command and web action retain the same appearance without any extra map message. | `typeclasses/tests/test_appearance.py` tests real `CmdLook`, direct `at_look` and `_look_adapter` for both typeclasses, with all `msg` calls captured. |
| `webclient-local-map` / `The graphical grid map is independent of automatic ASCII map display` | Full payload equality when only the display default changes; successful look retains an available actionable map. | `web/webclient/presentation/tests/test_local_map/test_presenter.py` through the production registry, with fixed knowledge and world state for comparison. |

No delta for `sample-city-altoria` or `village-ciaran-map`; authored options, topology, coordinates and prototypes stay unchanged. Keep their existing map-data regression modules as verification inputs. No delta for general web transport or room-action dispatch; their APIs and refresh behavior stay unchanged. The stale `InstanceRoom is not forward-declared by this change` requirement in the grid spec is pre-existing and outside this change.

### D4. Test messages as well as the returned string

Reuse the repository's synthetic map fixture patterns. Construct a small loaded, connected XYMap containing a plain grid room and an anchor room, with a known traversable exit and no explicit `map_display` option. Test both typeclasses with and without `scene_flavor`. Keep the real upstream appearance and grid gate; do not mock `at_look`, `return_appearance`, the display flag or `get_map` to return `None` in suppression tests. Spies around real methods are acceptable for asserting that ASCII `get_visual_range` is never invoked.

For text `看` and its `look` alias, execute the actual command through the existing Evennia command fixture pattern. Inspect all captured `actor.msg` calls, accounting for positional and keyword `text` and `(text, metadata)` tuples. For `_look_adapter(actor, {"room": True})`, require success `looked`, a call through `at_look` and the ordinary appearance message. Compare appearance contents after normalizing the existing envelope difference (`type: look` versus the adapter's plain string). Both paths retain the room name, authored description, optional flavor paragraph, contents and exits in their current order. Assert no `type: xymap` message and no ASCII sentinel/separator content in any text call. Direct `at_look` must also cause no map side message. A real map fixture prevents a vacuous pass caused by a missing map.

In presenter tests, hold the same actor, map, exits, clock and knowledge fixed. Render the complete `local_map` through the production registry with a test-scoped true class default and with the production false default, without calling look in the true baseline. The two payloads must be deeply equal and available, including schema version, title, identities, coordinates, visibility, anchor/landmark flags, nodes, edges, legend and action descriptors. Separately perform the real web look with the false default, render again and assert equality with its immediately preceding payload and unchanged location/clock/knowledge. Assert at least one genuine adjacent move descriptor so two unavailable or empty payloads cannot satisfy the test. No new frontend code or browser harness is needed to establish that its unchanged input remains usable.

For `goto`, use a synthetic route with independently known directions and endpoint, execute the localized command and English alias, and assert the actual room reached. The `path` alias must report that known route without moving. Keep timer control deterministic using the existing delay seam. Assert automatic step appearances do not reintroduce an `xymap` message. Preserve existing movement-cost behavior and the explicit map command regressions; do not redesign scheduling or movement.

### D5. Traceability and documentation

`docs/development/spec-test-traceability.md` and `AGENTS.md` govern annotations. Active change deltas are outside the main-spec index. During implementation, obtain current IDs with `uv run --locked python -m tools.spec_traceability list`; obtain the three added IDs using the same tool against an equivalent spec tree with these deltas merged. Never hand-construct IDs or add unknown IDs to main-tree tests before sync. Add literal `covers_requirement` claims only to discoverable tests with matching assertions once those IDs are valid, preserving the existing localized-frame claim on the renamed flavor test. At normal later spec sync, associate all three added requirements and run the post-sync check; do not count a pre-sync pass as coverage of these additions. This proposal does not sync or archive specs.

Prefer existing test modules, so shard ownership stays unchanged. If implementation adds a module, register it exactly once in `.github/evennia-shards.json`. Add no browser methods or browser-shard changes for this backend default. Update the existing look descriptions in `docs/game/commands.md` and `docs/game/command-reference.md` to state map-free automatic room look; keep explicit builder maps and navigation documented unchanged. These documentation changes belong to implementation, not this planning-only commit.

## Risks / Trade-offs

- Telnet users lose the unsolicited ASCII minimap too. This is intentional global scope; room descriptions/exits and `goto` remain usable, and builders retain explicit maps.
- Higher-precedence developer overrides can re-enable an ASCII map. This proposal preserves that upstream API and tests the project default, rather than introducing a new forced-suppression wrapper.
- Testing only the returned appearance or an unloaded `probe_map` would miss the bug. Loaded-map fixtures, all-message capture and a no-ASCII-render assertion cover the actual side effect.
- A graphical-map test that asserts only `available` could miss dropped actions or changed visibility. Full payload equality and a real adjacent descriptor protect the widget input.

## Open Questions

None. Global suppression of automatic grid-look maps matches the stated request. No product decision or unavailable implementation prerequisite remains.
