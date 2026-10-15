# Design: context_actions v6 — participant conditions and skill polarity

## Context

- Combat participants (`world/rules/combat_view.py` `ParticipantView`) carry identity, token, display name, team
  (`party`/`foes`), state, HP and `portrait_ref`, but no conditions. The status panel derives conditions for its
  actor through `build_status_read_model(entity)` (`web/webclient/presentation/status.py`).
- Skill effects are typed (`SkillDef.parsed_effects`), with parallel `effect_policies` carrying an `audience`
  (`SELECTED` default, `SELF`, `ALLIES`, `ENEMIES`; `world/skills/effects/policies.py`). Buff definitions declare
  `polarity` `buff`/`debuff` (`world/rules/buffs/definitions.py`). No other effect kind declares a direction.
- Schema convention:
  - Required additions to `context_actions` bumped the version: v1→v2 added `portrait_ref` (`0d25c3ea`), v2→v3
    grouped skills (`ffacd0ec`), and v4→v5 added `suggestions`.
  - Only the optional `freeform_scales` was added without a bump.
  - The client mirror and the server validator are exact-field, and
    `tests/test_panel_schema_version_parity_contract.py` pins the versions.

## Decisions

### D1. Bump to version 6 (follows the convention)

Both additions are required fields, so the panel moves to v6, as every earlier required addition did. The accepted
cost: three requirement headers carry the version number, so they are renamed and their tests are re-annotated with
the new IDs. The suggestions requirements of `webclient-options-surface` that say "v5" name the version that
introduced the envelope, so they stay as written.

### D2. Participant conditions

`ParticipantView.conditions: tuple[ConditionRow, ...]` holds `code`, `label` and `severity` from the status read
model of the participant entity: the first 8, in its order. If the read model raises `StatusQueryError` for an entity
(an object type it does not model), that participant's list is `[]` and the panel stays available. A missing
condition list is not worth making the whole panel unavailable. Severity vocabulary and code bounds reuse the status
panel's validators.

Disclosure: these rows reach the opposing player. The implementation checks whether the status read model carries
any hidden or owner-only condition (a flag, a severity or a code family meant only for the owner); if it does, such
rows are filtered out of participant `conditions` and a test pins the filter. If it does not, the design records
that finding in the module docstring.

### D3. Effect-kind classification

`world/skills/effects/polarity.py` holds two things:

- `EFFECT_TARGET_POLARITY: dict[type, str]`, covering every effect dataclass re-exported from `world.skills.effects`,
  each with a one-line reason comment.
- `skill_target_polarity(skill) -> tuple[bool, bool]`, returning `(hostile, beneficial)` over the effects whose policy
  audience is `SELECTED` and whose parsed recipient is not `"actor"`.

Anchors the spec pins:

- **Hostile:** damage, gauge transfer (drain), debuff-polarity buff application, and the sexual stimulus/pleasure kinds.
- **Beneficial:** heal, cleanse, buff-polarity buff application, and restore-purity.
- **Neutral:** movement, flavor, and session stamps.

For a SELF skill, the `SELECTED` effects whose recipient is the target land on the actor, so they count (a hostile SELF
skill is possible and is pinned by a synthetic fixture). This change classifies the remaining kinds by their
docstrings. The exhaustiveness test lists the
`world.skills.effects.__all__` dataclasses and fails on any kind missing from the table.

### D4. Mirrors

- Server: `_serialize_participant` adds `conditions` and `_serialize_skill` adds `hostile`/`beneficial`. The validators
  require them: `conditions` is a list of at most 8 rows with exactly `code`/`label`/`severity`, and both flags are
  booleans.
- Client: `validateParticipant` and `validateSkill` mirror the same rules, and `constants.js` gains
  `MAX_PARTICIPANT_CONDITIONS` and version 6.

## Risks / Trade-offs

- [Every combat fixture must change] → the shared builders get defaults; the focused runs in the tasks find the rest.
- [A long-open tab with the old bundle rejects v6] → the same as any version bump: the player reloads. There is no
  compatibility layer (pre-release).
- [A misclassified effect kind asks too often or too rarely] → the table is one reviewable file with reasons.

## Migration Plan

Pre-release; no stored data changes. Rollback is reverting the commits.

## Open Questions

None.
