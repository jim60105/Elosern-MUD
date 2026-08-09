## ADDED Requirements

### Requirement: Scene materialization exposes deterministic flavor context for fresh instance scenes
For a freshly spawned `instance`-layer scene (not an already-bound stage, not a permanent
destination), `materialize_stage` SHALL include in its `SceneMaterialization` result an optional
flavor context: a plain bounded dict with exactly the four keys `scene_sentence` (the requirement's
sentence or the archetype registry's), `quest_context` (the definition's `display_name` plus its
`quest_type`), `room_name` (the scene room's name), and `region` (the anchor placement display name
when the requirement declares `anchor_near`, else empty). A scene with neither a requirement sentence
nor a resolvable archetype sentence SHALL carry `None`. The context assembly SHALL reference no
generative module and no LLM profile (the deterministic-path ban stays green).

#### Scenario: A fresh instance scene carries the four-key flavor context
- **WHEN** a fresh instance scene materializes with a scene-sentence context and an `anchor_near`
  requirement
- **THEN** the result's flavor context is a bounded dict with exactly `scene_sentence`,
  `quest_context`, `room_name`, and `region` populated from deterministic sources

#### Scenario: An already-bound stage carries no flavor context
- **WHEN** `materialize_stage` returns an already-bound stage (idempotent re-entry)
- **THEN** the result's flavor context is `None` and nothing is scheduled

#### Scenario: A scene without a sentence carries no flavor context
- **WHEN** a stage's requirement has neither a scene sentence nor a resolvable archetype sentence
- **THEN** the result's flavor context is `None`

### Requirement: The scene flavor write is deterministic and never affects materialization
`world/quests/scene_builder.py` SHALL provide an `apply_scene_flavor(room, text)` helper as the sole
writer of `room.db.scene_flavor`: it SHALL verify the room's database row authoritatively
(`ObjectDB.objects.filter(pk=room.pk).exists()`) before any read-modify-write — a cached typeclass
is not proof of existence after reclamation — SHALL no-op (returning `False`) when the room is gone
or already carries a flavor, SHALL catch database and object-deletion exceptions and return `False`
for them, SHALL otherwise write the flavor and return `True`, SHALL never touch `room.db.desc`, and
SHALL never raise from a flavor context (a failure SHALL be a logged diagnostic with no state
change). The helper and its scheduling callers SHALL contain no reference to `world.ai` or any LLM
profile, keeping `world/quests` inside the deterministic-path ban.

#### Scenario: The sole writer applies once and only once
- **WHEN** `apply_scene_flavor` runs for an existing flavor-less room
- **THEN** it writes the flavor, returns `True`, and `room.db.desc` is unchanged

#### Scenario: Re-application is a no-op
- **WHEN** `apply_scene_flavor` runs again for a room that already carries the flavor
- **THEN** it returns `False` and keeps the existing value

#### Scenario: A vanished room is skipped without raising
- **WHEN** `apply_scene_flavor` runs with only a stale cached room reference after the instance
  room was reclaimed
- **THEN** the authoritative existence check fails (or the lookup raises and is caught), the helper
  returns `False`, and no state change occurs

#### Scenario: The deterministic path stays free of generative references
- **WHEN** the flavor-related source in `world/quests` is inspected
- **THEN** it contains no `world.ai`, `ollama`, or `llm_client` fragment, and the existing
  deterministic-path contract test passes without modification
