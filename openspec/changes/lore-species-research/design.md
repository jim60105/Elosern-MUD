# Design: lore-species-research

## Context

Source of truth: `docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md` §4.1, D5 and D6.

Current state (observed):

- `world/rules/lore_knowledge.py` is the sole writer of `db.lore_discovered`. Its `CODE_CATEGORIES["monster"]` is `CodexCategory(_constant(MONSTER_TIER_REGISTRY), ("display_name_zh", "description", "example_monsters_zh"))`. `record_lore_reveal` validates the stored record strictly (`_validated_record(current)`), appends, and calls `_schedule_lore_codex_push(player)` only for a new entry. `schedule_lore_reveal_best_effort` wraps `reveal_lore_best_effort` in `world.rules.presentation_events.on_publication_commit`, which runs nothing on rollback.
- The only monster reveal today is `world/quests/planner.py::quest_event_effect_planner`. It builds one `PendingEffect` per registered tier in the defeat event log, applying `_make_defeat_lore_apply(character, tier)`.
- Every hostile session is created by `world/rules/combat_session/lifecycle.py::_create_hostile_session(actor, targets, …)`. Its entry points are `engage`, `engage_group` (also used by `combat_initiation.initiate_field_combat`) and `create_hostile_contact_session` (authored contact, `world/rules/field_contact.py`). The record is persisted in `with transaction.atomic(): _persist(actor, record)`.
- Every resolved round goes through `rounds.py::_finalize_resolved_round`, which calls `_record_round_defeats(new_record, battlefield, round_hp_before, round_hp_after, completed_round)`. That function returns early when `record.population_cell is None` or when no live wilderness exists, and only then computes the live-to-dead crossings of enemy `Monster`s.
- `typeclasses.monsters.Monster.species_key` is the persistent species identity. It is `None` for a non-species individual.
- Guild examinations use `record.mode == "guild_exam"` (`battlefield._session_policy`). Hostile sessions use `"hostile"`.
- The synthetic kit (`world/tests/synthetic_data`) provides the `monster_species` and `monster_tiers` logicals, with one invented species `t_whisper_quail` and variants. `make_monster_species(key, **overrides)` builds more.

## Goals / Non-Goals

**Goals:** the behavior in `specs/lore-knowledge/spec.md` with the smallest edits to the five files listed in the proposal.

**Non-Goals:**

- No `lore_codex` schema change. The v1 presenter keeps calling `lore_card`, and its stage-aware fields arrive in `lore-codex-schema-v2`.
- No counts (design D6), no per-variant research, no sighting from look, examine or presence, and no sighting for exam opponents.
- No migration or repair of stored `monster:<tier>` identifiers.
- No change to quest DEFEAT progress. `_defeated_targets` and the progress planning stay as they are.

## Decisions

### D1. Category re-point

In `lore_knowledge.py`, replace the `MONSTER_TIER_REGISTRY` import with `from world.lore.monster_species import MONSTER_SPECIES_REGISTRY`, and set:

```python
"monster": CodexCategory(
    _constant(MONSTER_SPECIES_REGISTRY),
    ("display_name_zh", "published_appearance_zh"),
),
```

Both card fields are plain string attributes of `MonsterSpecies`, so `lore_card` keeps working unchanged. The author-private fields are never declared. Update the module docstring.

### D2. Writers and reader (verbatim contracts)

```python
DEFEATED_ATTR = "lore_species_defeated"

def _validated_species_record(record: Any, *, tolerant: bool = False) -> set[str]:
    """A set of non-empty str keys without ':'; strict mode requires each to resolve in
    CODE_CATEGORIES["monster"].registry. Anything else raises LoreRecordError. Returns a copy."""

def list_species_defeated(player: Any, *, tolerant: bool = False) -> tuple[str, ...]:
    """Sorted defeated species keys; None reads as (); corrupt raises LoreRecordError."""

def record_species_sighting(player: Any, species_key: str) -> None:
    """Validate the key (LoreKeyError), then record_lore_reveal(player, "monster", species_key)."""

def record_species_defeat(player: Any, species_key: str) -> None:
    """Validate the key (LoreKeyError); validate the stored defeated record strictly
    (LoreRecordError) BEFORE any write; record_species_sighting(...); then, when the
    key is new, assign a fresh set to player.db.lore_species_defeated and call
    _schedule_lore_codex_push(player)."""
```

Key validation: `isinstance(species_key, str) and species_key in CODE_CATEGORIES["monster"].registry`, else `LoreKeyError(f"no lore entry {species_key!r} in category 'monster'")`. Each record keeps its own one-push-per-change rule, so a first defeat of an unseen species schedules two pushes. The causal publication group coalesces them, as the existing `_schedule_lore_codex_push` docstring states. Alternative considered: one combined push. Rejected because it would bypass `record_lore_reveal` and break the existing sole-writer requirement for `lore_discovered`.

Best-effort schedulers, mirroring `schedule_lore_reveal_best_effort`:

```python
def schedule_species_sighting_best_effort(player: Any, species_key: str | None) -> None
def schedule_species_defeat_best_effort(player: Any, species_key: str | None) -> None
```

Each returns silently for a non-str or empty key. Otherwise it registers `on_publication_commit(lambda: _species_best_effort(player, species_key, stage))`. That callback calls the writer inside `try` and on any exception calls `log_warn("lore_reveal_failed", exc=exc, context={"char": …, "category": "monster", "key": species_key, "stage": stage})` with `stage` set to `"sighted"` or `"defeated"`. A registration failure is logged the same way.

### D3. Sighting hook

Add to `world/rules/combat_initiation.py`:

```python
def schedule_session_sightings(participants: Iterable[Any], targets: Iterable[Any]) -> None:
    """Schedule one post-commit sighting per (player character, distinct hostile species)."""
    from typeclasses.characters import PlayerCharacter
    from world.rules.lore_knowledge import schedule_species_sighting_best_effort

    players = [entity for entity in participants if isinstance(entity, PlayerCharacter)]
    if not players:
        return
    seen: list[str] = []
    for target in targets:
        key = getattr(target, "species_key", None) if isinstance(target, Monster) else None
        if isinstance(key, str) and key and key not in seen:
            seen.append(key)
    for player in players:
        for key in seen:
            schedule_species_sighting_best_effort(player, key)
```

Call it from `lifecycle.py::_create_hostile_session` inside the existing `with transaction.atomic():`, directly after `_persist(actor, record)`, as `schedule_session_sightings((actor, *companion_entities), targets)` (`companion_entities` is the local list the body already builds for `initial_sleep_ids`). Sighting is credited to the same set of player characters that D4 credits with defeats, so a defeat never lands on a character that has not sighted the species. Use a deferred import (`from world.rules.combat_initiation import schedule_session_sightings`), because `combat_initiation` imports `combat_session`. The design's §4.1 names `combat_initiation.py`, and the helper lives there. The call site is the shared creation body so that `engage`, `engage_group`, skill openings and authored contact all record a sighting. Alternative considered: calling it only from `initiate_field_combat`. Rejected because `engage()` (the `engage` command and `explore.engage`) and authored contact would then never sight anything. Confirm the actual `PlayerCharacter` import path with `git grep -n "class PlayerCharacter"` before writing the import.

### D4. Defeat hook

Restructure `rounds.py::_record_round_defeats` without changing its population behavior:

```python
crossings = [
    entity for entity in battlefield.roster.values()
    if isinstance(entity, Monster)
    and int(entity.pk) in set(record.enemy_ids)
    and hp_before.get(int(entity.pk), 0) > 0
    and hp_after.get(int(entity.pk), 0) <= 0
]
if record.mode == "hostile":
    _schedule_round_species_defeats(record, battlefield, crossings)
if record.population_cell is None:
    return
… existing wilderness / cell checks, then the existing transition loop over `crossings` …
```

Move the `from typeclasses.monsters import Monster` import above the new block. `_schedule_round_species_defeats` credits every `PlayerCharacter` entity in `battlefield.roster.values()` whose `int(pk)` is in `record.player_ids`. For each crossing whose `species_key` is a non-empty str it calls `schedule_species_defeat_best_effort(player, key)`, deduplicating `(player.pk, key)` within the round. Update the docstring. The loop body for population transitions is unchanged apart from iterating `crossings`.

### D5. Retire the tier reveal

Delete `_make_defeat_lore_apply` and the `if crediting_player is not None:` block that builds the tier `PendingEffect`s in `world/quests/planner.py`. Also delete `crediting_player` if nothing else reads it (check with grep). In `world/rules/tests/test_lore_deterministic_reveals.py`:

- Delete `test_make_defeat_lore_apply_factory_binds_correctly` and `test_defeat_lore_reveal_failure_does_not_raise`.
- Keep the three `_defeated_targets` tests and `test_unregistered_tier_not_in_monster_registry`, but drop their `lore-knowledge::defeating-a-monster-reveals-its-tier` annotations, because they test quest parsing.
- Change `test_offline_play_fills_codex_without_external_calls` to reveal a synthetic species through `record_species_defeat` and assert both records.

## Risks / Trade-offs

- [Not every committed monster defeat passes through `_record_round_defeats`. `world/rules/upkeep.py::_stage_casualties` (between-round upkeep casualties) and `world/rules/action/transaction.py::_record_population_crossings` (out-of-combat action resolution) also emit `target_defeated` events, and the quest planner reads those events, not this hook] → The user explicitly placed the defeat hook in `_record_round_defeats`, and in-session rounds are where defeats happen in play. Out-of-round kills credit no species defeat in this change. A test pins that boundary (task 2.2). A later change can re-point the planner's `target_defeated` path (whose `_defeat_identities` already carries `species_key` and `simulated`) if those kills must count.
- [A stale `monster:<tier>` in `lore_discovered` makes the strict `record_lore_reveal` reject every later reveal of any category, not only monster] → Called out here and in the PR notes. The failure is logged as `lore_reveal_failed` with the offending record. The GM raw console clears it.

- [Accepted no-migration consequence of the stale tier record above] → The tolerant presenter keeps the codex readable.
- [Two pushes for a first defeat] → They coalesce through the causal group, and no new push path is added.
- [Crediting by `record.player_ids` could credit a possessed body] → Only `PlayerCharacter` entities are credited, and the codex is keyed on the same object the other reveals use.

## Migration Plan

None. Pre-release, so no data migration and no compatibility layer.
