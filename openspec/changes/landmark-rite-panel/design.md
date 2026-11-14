# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §12.1. Existing code, read on 2026-11-14:

- The closest precedent is the `sleep_handoff` panel: `web/webclient/presentation/sleep_handoff.py` (presenter, validator, `PanelUnavailableError` when the panel does not apply), its registration and validator attachment in `web/webclient/presentation/registry.py` (`build_production_registry` and `_attach_production_validators`), and its browser mirror `web/static/webclient/js/elosern/protocol/panels/sleep_handoff.js` with its constants in `protocol/constants.js`, its entry in the validator table of `protocol/envelope.js`, its re-exports in `protocol.js`, and its name in the panel list of `web/webclient-app/stores/elosern/shared.js`.
- `tests/test_panel_schema_version_parity_contract.py` lists `(panel name, python module)` pairs and compares each module's schema version with the browser allowlist in `constants.js`.
- Validator helpers: `web/webclient/presentation/protocol.py` (`_require_exact_fields`, `_require_int`, `_require_str`, `_require_bool`, `json_byte_size`, `ProtocolValidationError`, `MAX_SAFE_INTEGER`); browser `protocol/core.js` (`requireExactFields`, `requireInt`, `requireBool`, `requireString`, `isPlainObject`, `jsonByteSize`).
- Artwork descriptor validators: `web.webclient.presentation.artwork.validate_artwork` and browser `protocol/artwork.js` (the `travel_log` panel's `landmark_reached.artwork` already uses both).
- `PresentationContext.actor` is the active puppet. A successful move, wait and rite publish a full snapshot, so an eager panel is recomputed on arrival and after each rite.
- `web/webclient/actions/rite_actions.py` (`landmark-rite-action`): `landmark_rite_adapter`, `rite_delivery(result)`.
- `world.rules.map_district_lighting.lit_district_keys(character)` is the one lit-district read; it raises `world.rules.map_knowledge.KnowledgeError` on a corrupt knowledge record.
- `world.rules.landmark_rites`: `record_owner_for`, `rite_site_for`, `eligible_performers`; `world.rules.landmark_rite_record.seen_option_keys`; `world.rules.map_knowledge.node_id_for`.

## Goals / Non-Goals

**Goals**

- One validated panel on both sides of the wire, with the same bounds.
- The delivery survives a snapshot replay on the same node and never leaks to another node.

**Non-Goals**

- No Vue component, no store group beyond the panel name, no story (`landmark-rite-stage`).
- No artwork: `art` is always `None` here (`landmark-rite-art`).
- No persistence of the delivery. It is `ndb` state and is lost on a server restart; the player may perform the rite again.
- The panel never authorizes anything: the action re-validates the option and the performer.

## Decisions

### D1. Wire shape (schema version 1)

Available form, exactly these keys:

```json
{
  "schema_version": 1,
  "available": true,
  "kind": "rite",
  "district": {"key": "<district key>", "name": "<district name>", "landmark": "<landmark name>", "lit": false},
  "guardian": {"name": "<name>", "form": "<form>"},
  "art": null,
  "options": [{"key": "<option key>", "label": "<label>", "companion": true}],
  "performers": [{"member_id": null, "name": "<name>", "owner": true}, {"member_id": 7, "name": "<name>", "owner": false}],
  "delivery": null,
  "seen": ["<option key>"]
}
```

`delivery`, when not null, is exactly `{kind, delivery_id, scene_id, scene_revision, actor_name, guardian_name, lines}` as `rite_delivery` builds it.

Bounds, identical in Python and JavaScript (constants named `RITE_*` in `constants.js`, module constants in `rite.py`):

| Field | Bound |
| --- | --- |
| whole panel | at most 32768 canonical JSON bytes |
| `kind` | the literal `rite` |
| `district.key` | 1..64 ASCII characters |
| `district.name`, `district.landmark` | non-blank, 1..256 code points |
| `district.lit` | an exact boolean |
| `guardian.name` | non-blank, 1..32 code points |
| `guardian.form` | non-blank, 1..200 code points |
| `art` | null, or a value `validate_artwork` accepts |
| `options` | 1..3 entries; keys unique; `key` matches `^[a-z][a-z0-9_]{0,31}$`; `label` non-blank 1..32 code points; `companion` an exact boolean |
| `performers` | 1..16 entries; the first has `member_id` null and no other entry does; other `member_id` values are unique integers in `1..MAX_SAFE_INTEGER`; `name` non-blank 1..128 code points; `owner` an exact boolean, true on at most one entry |
| `seen` | 0..3 unique option keys, each one of `options[].key` |
| `delivery.kind` | the literal `formal` |
| `delivery.delivery_id` | 1..128 ASCII characters |
| `delivery.scene_id` | 1..96 ASCII characters |
| `delivery.scene_revision` | 1..32 ASCII characters |
| `delivery.actor_name`, `delivery.guardian_name` | non-blank, 1..128 code points |
| `delivery.lines` | 1..32 entries; each exactly `{kind: "narration", text}` or `{kind: "speech", speaker: "actor"|"host", text}`; `text` 1..2000 code points |

`district.lit` is not in the design's example; the arrival card of the design's §12.2 shows the district's lit state, so the panel must carry it. The design's example showed `art` as `{"subject", "attempts"}` and a performer name bound of 32. Both are superseded here: `art` reuses the one artwork descriptor the client already renders, and a performer name uses the member-name bound the `sleep_handoff` panel uses, because character names are not limited to 32 code points.

### D2. Presenter (`web/webclient/presentation/rite.py`)

```python
RITE_SCHEMA_VERSION = 1
RITE_UNAVAILABLE_REASON = ("rite_no_landmark", "這裡沒有可以進行儀式的地標")
DELIVERY_NDB = "landmark_rite_delivery"

def validate_rite(payload: Any) -> dict[str, Any]: ...
def rite_presenter(context: Any) -> dict[str, Any]: ...
def store_rite_delivery(owner: Any, delivery: dict) -> None: ...
```

`rite_presenter`:

1. `owner = record_owner_for(context.actor)`; `RiteRefused` -> `raise PanelUnavailableError()`.
2. `site = rite_site_for(owner)`; `None` -> `raise PanelUnavailableError()`.
3. `options`: one row per `site.archetype.options` in authored order: `key`, `label = label_zh`, `companion = option.watch_scene is not None`.
4. `performers`: from `eligible_performers(context.actor)`: the first row `{member_id: None, name: actor.key, owner: actor is owner}`, then `{member_id: body.id, name: body.key, owner: body is owner}` for each further body, truncated to 16 rows. `owner` marks the record owner's own body: only that body performs in the `self` perspective, so while the player possesses a companion the first row has `owner` false.
5. `seen`: `seen_option_keys(owner, site.district_key)` filtered to the keys of `options`, in option order. A `LandmarkRiteRecordError` -> `log_warn("landmark_rite_record_corrupt", exc=error, context={"char": owner.pk, "district": site.district_key})` and `seen = []`.
6. `delivery`: read `owner.ndb.landmark_rite_delivery`; when it is a dict whose `node` equals `node_id_for(owner.location)`, use its `delivery`; otherwise `None`.
7. `art`: `None`.
8. `district.lit`: `site.district_key in world.rules.map_district_lighting.lit_district_keys(owner)`; a `world.rules.map_knowledge.KnowledgeError` -> `False` (the map presenters already log that fault).
9. Return the dict of D1 and pass it through `validate_rite` before returning; a `ProtocolValidationError` propagates (the registry converts it to the unavailable form and logs it).

`store_rite_delivery(owner, delivery)` sets `owner.ndb.landmark_rite_delivery = {"node": node_id_for(owner.location), "delivery": delivery}`.

`validate_rite` enforces D1 exactly and raises `ProtocolValidationError`.

Register in `build_production_registry` after `travel_log`:

```python
registry.register(PresenterSpec(
    name="rite",
    schema_version=RITE_SCHEMA_VERSION,
    unavailable_reason=RITE_UNAVAILABLE_REASON,
    presenter=rite_presenter,
))
```

and add `"rite": validate_rite` to `_attach_production_validators`. `web/webclient/presentation/tests/test_combat_panel/test_presenter.py` `test_production_registry_contains_every_registered_panel` asserts the exact panel name set; add `rite` to it.

### D3. Adapter (`web/webclient/actions/rite_actions.py`)

In `landmark_rite_adapter`, on success and before returning, call `store_rite_delivery(owner, delivery)` with the same delivery dict placed in the result data. Import it inside the function.

### D4. Browser mirror

- `protocol/constants.js`: add the `RITE_*` bound constants and `RITE_SCHEMA_VERSION = 1`, the allowlist entry `rite: RITE_SCHEMA_VERSION`, and the exports, following the `SLEEP_HANDOFF_*` block.
- `protocol/panels/rite.js`: `validateRitePanel(panel)` enforcing D1 exactly, written in the style of `panels/sleep_handoff.js` (CommonJS, `"use strict"`), delegating `art` to `protocol/artwork.js` the way `panels/travel_log.js` validates `landmark_reached.artwork`. It throws on any violation and returns the panel.
- `protocol/envelope.js`: require the module and add `rite: rite.validateRitePanel` to the validator table.
- `protocol.js`: require the module and export `validateRitePanel` and `RITE_SCHEMA_VERSION`.
- `web/webclient-app/stores/elosern/shared.js`: append `"rite"` to the panel name list after `"travel_log"`.
- `tests/test_panel_schema_version_parity_contract.py`: append `("rite", "rite.py")` to the tuple of pairs.

### D5. Documentation

`docs/development/webclient-synchronization.md`: a short section for the `rite` panel stating its availability rule, the shape of D1 with its bounds, that `performers` and `options` are advisory presentation data, and that `delivery` is non-persistent and bound to the node.

### D6. Tests

`web/webclient/presentation/tests/test_rite_panel.py`:

- pure validator tests (`unittest.TestCase`) on a synthetic valid panel: accepted as is; then one mutation per row of the bounds table, each rejected (an extra key at every level, four options, a duplicate option key, a first performer with a non-null `member_id`, a second performer with null, seventeen performers, a `seen` key that is not an option, a delivery with zero lines, a speech line with an unknown speaker, an oversize panel);
- presenter tests (`EvenniaTest`, the synthetic landmark fixture and synthetic rite snapshot of `world/rules/tests/test_landmark_rites.py`): on the landmark the panel names the district with its lit flag false while `lit_district_keys` (patched) returns an empty set and true while it returns the district key, the guardian, both options with the right `companion` flags, the actor as the first performer and a present companion as the second, `seen` empty and `delivery` null; after one committed rite through `landmark_rite_adapter` the panel carries that delivery and the option in `seen`; after the owner moves to another node the presenter raises `PanelUnavailableError`; back on the landmark with the stored delivery bound to another node the delivery is null; a corrupt record yields `seen == []` and one warning; a sleeping companion is absent from `performers`; while the actor is a possessed companion the first row has `owner` false and the owner's row, when present, has `owner` true.

`web/static/webclient/js/tests/rite_panel.test.js` (the dependency-free Node gate, in the style of `travel_log.test.js`): the same valid panel accepted and the same mutation table rejected; the panel routed through the envelope's panel validator table under the name `rite`.

Register the Python module in `.github/evennia-shards.json` beside `web.webclient.presentation.tests.test_travel_log`.

## Risks / Trade-offs

- An eager panel adds one presenter run to every full snapshot. `rite_site_for` keeps that cheap off a landmark (`landmark-rite-settlement` design D3: a room-type check and a cached node lookup).
- A delivery is lost on restart. This is the design's accepted reconnect behaviour.
