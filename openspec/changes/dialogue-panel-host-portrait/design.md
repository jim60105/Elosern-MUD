## Context

See proposal.md (Why). The state below was checked in code, assuming C1 to C9 are archived (none of them touches the dialogue panel's schema; C9 only adds a session writer).

- `web/webclient/presentation/dialogue.py`:
  - `DIALOGUE_SCHEMA_VERSION = 1`, registered through `registry.py` (`name="dialogue", schema_version=DIALOGUE_SCHEMA_VERSION`).
  - `_validate_host` requires exactly `identity`, `display_name`, `portrait_ref`, and rejects any non-null `portrait_ref`.
  - `dialogue_presenter` degrades to `PanelUnavailableError` for a creation-pending puppet, a puppet with no location, no live session, and a race-lost re-resolve (`_resolve_live_host`). It writes `"portrait_ref": None`.
  - The panel is also rendered under combat mode (the engage update carries it; `test_engage_update_carries_the_dialogue_panel_under_combat_mode`).
- `world/rules/art_view.py`:
  - `build_art_view(actor)` returns `ArtView(scene_archetype, entities)`. Outside an active combat session the entities are `_exploration_entities(location, actor)`: the room's `is_dialogue_host` NPCs and characters with a named portrait policy, sorted by identity and capped at `MAX_PORTRAIT_CATALOG`. In a combat session they are the combat roster.
  - It raises `ArtViewError` on bound violations and for a missing combat session. It performs no writes and resolves no media. `web/webclient/presentation/art.py` `_serialize_catalog_entry` calls `resolve_entity` only when serializing.
  - `portrait_catalog_key(identity)` is the single key mapper, shared with `combat_view.py` (`portrait_ref=portrait_catalog_key(int(dbref))`).
- `web/webclient/presentation/art.py` is available in every mode except creation, so the `art` panel is committed in dialogue mode with the host's entry when the host is in the view.
- The combat participant's `portrait_ref` rule (`combat_panel.py` lines 191–198, JS `panels/combat.js` lines 126–133): `null` or a decimal string of at most `MAX_PARTICIPANT_REF = 32`.
- Client: `web/static/webclient/js/elosern/protocol/constants.js` `DIALOGUE_SCHEMA_VERSION = 1`; `panels/misc.js` validates the dialogue host (lines 253–266) with the null rule. `tests/test_panel_schema_version_parity_contract.py` checks that the Python and JS constants are equal.
- Consumers of `portraitRef`: after C6c, `MessageWindow`'s dialogue variant resolves `portraitFor(artPanel, vm.host.portraitRef)` (`components/party-helpers.js`), which returns the entry only when it has a `url`.

## Goals / Non-Goals

**Goals:**
- The dialogue panel names the host's art catalog entry whenever the committed `art` panel has one, with the client never constructing a key.
- Server and client validators agree on the new vocabulary.

**Non-Goals:**
- Any client presentation change (C10b draws the stage portrait).
- Changing the art catalog's membership (a pure `LLMNPC` without a portrait policy stays absent and gets the placeholder in C10b).
- The party panel's and the exploration descriptors' `portrait_ref`, which stay `null` in their schemas.

## Decisions

### D1. Derive membership from the same art view, not a new predicate
The presenter calls `build_art_view(actor)` and sets `portrait_ref = portrait_catalog_key(npc.pk)` when `int(npc.pk)` is one of `view.entities[*].identity`. When the host is absent from the view, or `ArtViewError` is raised, it sets `null`.

*Why the art view itself:* the requirement is "equals a key of the committed catalog in the same snapshot". Reusing the builder gets every membership rule right by construction: the dialogue-host and named-portrait filter, the actor exclusion, the `MAX_PORTRAIT_CATALOG` cap, and the combat roster when the panel renders under combat mode. A separate predicate would miss the cap and the combat branch and could drift.

*Alternative:* factor the exploration filter out as `in_exploration_catalog(entity)`, as the split proposal suggested. Rejected for the reasons above.

*Cost:* `build_art_view` iterates the room contents and classifies subjects; it resolves no media. The art presenter already does the same work in the same snapshot. The bound is `MAX_PORTRAIT_CATALOG` entities.

### D2. Same wire vocabulary as combat participants
`portrait_ref` is `null` or `^[0-9]+$` with at most 32 characters, on both sides. The Python validator reuses the combat rule's wording ("portrait_ref must be an opaque decimal catalog key or null", "portrait_ref exceeds its bound"). The dialogue module defines its own `MAX_DIALOGUE_PORTRAIT_REF = 32` rather than importing from `combat_panel.py`, which keeps the panel modules independent. A test pins the two values equal.

### D3. Version bump, no compatibility window
The field's allowed values widen, and the requirement pins the version, so the schema becomes 2. Server and client ship together and the client is unreleased, so no version-1 acceptance is kept. Every client fixture of the available form moves to version 2.

### D4. Consistency across pushes
The key is stable for a given NPC. Only the entry behind it changes when a portrait finishes generating, and that change travels in the `art` panel's own push (`art_push.py`). The dialogue push after an NPC departure (`dialogue_push.py`) renders the unavailable form, which carries no host. No new push path is needed.

### D5. Spec strategy and archive order
The requirement's title names the version, so it is REMOVED and ADDED (version-2), keeping every scenario title and adding two. The single annotation in `test_dialogue_panel.py` re-anchors. No other series change modifies `webclient-dialogue-session` "The dialogue panel is…"; C9 modifies "The dialogue session is deterministic-core-only character state" only.

**Archive order: C9 (`explore-talk-open-action`) → C10a (this change) → C10b (`webclient-dialogue-stage-actors`) → C10c (`webclient-dialogue-choices-overlay`).** C10b consumes the key. The implementation touches no hot-spot client file, so it may be built in parallel with earlier client changes.

## Risks / Trade-offs

- [The art view builder raises for a combat actor with no session record] → The presenter catches `ArtViewError` and ships `null`; the panel stays available. Pinned by a test.
- [The catalog cap drops the host in a crowded room] → `portrait_ref` is `null` exactly then, because membership comes from the same capped view. C10b shows the placeholder.
- [The dialogue avatar in the message window starts showing images before C10b] → Intended and truthful: that code already resolves the catalog entry and was only starved of a key.

## Migration Plan

None. The client and server ship together, and nothing persists the panel.
