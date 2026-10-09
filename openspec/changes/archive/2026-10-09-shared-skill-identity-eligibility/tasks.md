# Tasks

## 1. Shared declarative qualification

- [x] 1.1 Add frozen eligibility metadata to registry/vocab.py and builders.py and the pure record/runtime query in world/skills/eligibility.py; verify deterministic player/NPC/monster kind, race/subrace/parent, missing identity, valid/invalid species-variant and capability cases in a new synthetic world.rules.tests.test_skill_identity_eligibility module, registered exactly in rules-c (index 3).
- [x] 1.2 Extend registry validation for unknown/empty/contradictory restrictions and parent consistency without import cycles; add authoring cases to world.skills.tests.test_skill_registry and document lists/AND/capability semantics in docs/development/adding-spells.md; verify load failures precede any runtime action and existing unrestricted registry entries retain behavior.

## 2. Clean divine and authored ownership cutover

- [x] 2.1 Replace the old divine skill field and all builder arguments/declarations in registry data, sexual_acts and synthetic data_skills.py; migrate family invariants and the pleasure-ratio exception to declared required capability; update registry-contract/sexual structure tests and docs/development/adding-player-presets.md, verifying the old field and aliases are absent while RaceProfile.can_use_divine_arts and its values remain unchanged.
- [x] 2.2 Replace the mastery blanket exclusion in sexual_acts/__init__.py with the required-capability classification, preserving ownership_gated/counter acquisition and category-based daily cadence; update test_sexual_unlock, divine catalog tests and test_divine_digestion_cadence, verifying eligible races still cannot acquire divine acts through mastery and rollback releases daily/tick claims.
- [x] 2.3 Integrate authored intended identity into world/imports/validate.py, player_presets/validation.py and closure/grant ownership acceptance; update import/preset tests and docs/development/adding-npcs.md and adding-player-presets.md, verifying ineligible declared or closure-added skills/passives name their fields and reject before persistence without constructing entities; preserve degraded registry reporting.

## 3. Runtime containment and presentation

- [x] 3.1 Compose identity qualification into can_use_skill and remove the independent divine action gate; update action/gates.py, action_preview.py and submission/reason mappings with existing rejection tests and synthetic ineligible-root tests, verifying preflight/final resolution reject identity separately from unmet edges before dice/cost/effect/practice writes and unrestricted eligible character/monster use remains intact.
- [x] 3.2 Enforce identity on owned/conferred passive reads and grant writes through handler/restriction, combat modifier, movement and status breakdown consumers; extend handler/conferral/movement/combat-modifier tests and the existing authoring guide, verifying an ineligible stored passive/grant contributes nothing while a new incompatible grant is rejected and reads create no handlers/state.
- [x] 3.3 Filter player skill catalogs and lineage_query.py by the same identity query, preserving consumption-root and topological/count semantics; extend test_lineage_query, status grouping and character/lineage presenter tests, verifying monster trees/catalog entries are absent, eligible racial nodes remain discoverable and identity does not duplicate ownership/MP/proficiency checks; document the filtering in adding-spells.md with no command/payload redesign.

## 4. Integration acceptance

- [x] 4.1 Run focused affected Evennia test labels with the repository-approved test settings/environment file, including new identity tests, lineage, import/preset, passive/conferral, sexual/divine, preview and presenter suites; record results proving the standalone cutover works without either other batch change. Add requirement coverage markers for future synchronized requirements and retain existing stable marker names.
- [x] 4.2 Run uv run --locked python -m tools.contract_gate, relevant observability lint if rejection logging changes, data lint and openspec validate shared-skill-identity-eligibility --strict; verify exact shard ownership and registered data-contract tests for any shipped assertions, document actual evidence without runtime/balance claims not exercised, and keep both command docs unchanged unless command syntax/availability changed.

## Workflow follow-up

- After review/verification, archive this standalone prerequisite before applying the crocodile integration; serialize shared-file work with skill-hit-dependent-effects as recorded in proposal.md. Proposal creation performs no apply/archive/sync.
