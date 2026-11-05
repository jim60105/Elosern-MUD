# Design

## Context

See `proposal.md` for motivation. The approved design is `docs/superpowers/specs/2026-11-05-monster-individual-names-design.md`, and the approved visual treatment is the Storybook prototype `Design/MonsterIndividualNames` in `docs/design/monster-individual-names/`.

Current state:

- `construct_species_individual()` writes `key` as the caller's value or the variant's `display_name_zh`. Two boss sites pass an authored label, which leaves no record that it is a name.
- Player surfaces read `obj.key`. Exploration rows use `_bounded_display_name()`, and combat participants use `_build_participants()`.
- `exploration` is at schema 6 and `context_actions` at schema 7. Both are exact-field panels mirrored in `web/static/webclient/js/elosern/protocol/`.
- Evennia's `db_key` is NOT NULL and `search()` matches on it.
- `resolve_variant()` raises; `_registered_variant()` is its lenient half.
- The stage target step already adds a session token when two candidates share a name, so same-species foes stay distinct with no new logic.
- `world/lore/monster_species.py` validates every row during registry build, and `world/lore/monster_placement.py` validates site labels at publication.

## Goals / Non-Goals

**Goals:**

- One source for each name fact, with facts on the wire and display decisions in the client.
- Named and unnamed boxes share one geometry on every surface.

**Non-Goals:**

- Adding a quest bound to a named site, in-game codex entries, or variant text in `look` or the combat log.
- Migrating existing rows. The database is rebuilt.
- Pinning shipped names in specs or tests. Tests use synthetic fixtures.

## Decisions

### 1. `key` is a one-write search label

`individual_name` is an `AttributeProperty(default=None, autocreate=False)` beside `species_key`. Construction writes `key` once as `individual_name ?? species.display_name_zh`.

Alternative: stop using `key` for monsters and override `get_display_name()`. Rejected, because `search()` and many `.key` readers would need another path while the value stays required by the engine.

### 2. `individual_name=` replaces `key=`

Construction has no caller that needs a key separate from the name. `manual_campaign.py` and test fixtures move mechanically. Their technical labels become individual names, which is harmless because the length bound applies only to authored registries.

Alternative: keep both parameters. Rejected, because a caller could then produce a key that matches no fact.

### 3. One lenient read model

`monster_identity_view(entity) -> MonsterIdentityView | None` lives in `world/rules/monster_individual.py`, is built on `_registered_variant()`, and never raises. Presenters, the combat view and the LLM situation builder all call it, so a retired variant degrades to `key` rather than failing a panel.

### 4. Facts on the wire, not strings

`monster_identity` is `null | {individual_name, species_name, variant_name}`. `display_name` stays because every entity row uses it.

When the identity is non-null, presenters set `display_name` from the read model, not from `key`. A GM rename therefore cannot make a payload disagree with itself. Validators on both sides reject a disagreement.

Alternatives: a server-composed `variant_tag`, which puts a display decision on the server, or a generic `tags` array, which has no second use.

### 5. `monster-identity.js` owns the reading

`isNamedMonster(identity)` and `monsterDetailTag(identity)` are pure, and they are the only place that composes the tag. `exploration_menu.js` carries the identity onto presence entries, and `stage_targets.js` carries it onto member positions.

### 6. The named treatment is rank language

The approved treatment reuses `GuildRankCard`'s inner double rule on the medallion, and fading hairlines in the manner of `ChoiceCard`'s crest and the plate's crown. Gold corner brackets, outer rings, side rules, a single underline and a doubled crown were rejected, because each already means selection, focus, or acting in this client. Lozenges, a seal and new patterns were rejected in design review.

Each rule is an overlay or background layer. The name swaps only colour and family, with the name's line height fixed where the display family's metrics differ. `data-named` drives the styling.

### 7. Bounds live in registry validation

`MONSTER_NAME_MAX_CODE_POINTS = 5` is checked by `validate_monster_species_registry()` and `_check_individual_name()`. A data-contract test would pin shipped content, so none is added.

### 8. Panel version history stays in names

Requirement titles and the phrases "v7 party contract" and "v7 actor command envelope" name the contract introduced at that version. Only statements of the current registered version move to 7 and 8.

## Risks / Trade-offs

- [Same-species variants share a plate name, so a D-grade and an A-grade foe look alike at a glance] → The readout and target prompt show the tag. This is accepted.
- [`engage <variant name>` stops matching] → Accepted. Commands match the species or individual name.
- [A `key` goes stale if a registry name changes] → Display reads the registry, so only command search is affected, and the database is rebuilt.
- [The hairline could conflict with the plate's `target` and `acting` states] → The specs and tasks cover both states in the real component.
- [The hairlines are quieter than earlier candidates] → Accepted in review. The inner rule can move to `--gold-300` with no structural change.

## Migration Plan

Rebuild the development database after merging. There is no compatibility layer, and neither panel accepts its old version.

Rollback is a revert plus another rebuild.
