# Tasks

Follow `design.md`. Tests use synthetic fixtures and never pin a shipped name, site or roster. Use `--env-file=<file>` with `MUD_TEST_SETTINGS=1` for Evennia tests.

## 1. Identity data and construction

- [x] 1.1 Add `Monster.individual_name`; replace `key=` with `individual_name=` in `construct_species_individual()`, defaulting the key to the species name and rejecting an invalid name before persistence. Update `manual_campaign.py` and every `key=` fixture. Replace the variant-label assertions in `world/rules/tests/test_monster_individual.py`. Check: construction tests cover the default, named and invalid cases, and `rg "construct_species_individual\(.*\bkey=" world tools` finds nothing.
- [x] 1.2 Add `MonsterIdentityView` and `monster_identity_view()` on the lenient path. Check: tests cover unnamed, named, tier-only, non-monster and retired-variant entities, with no raise.
- [x] 1.3 Add `MONSTER_NAME_MAX_CODE_POINTS` and enforce it in `validate_monster_species_registry()`. Rename `MonsterSite.individual_label_zh` to `individual_name_zh` and its check to `_check_individual_name()`, applying the bound. Pass the name through `world/maps/monster_sites.py`. Check: registry tests reject six code points and accept five, and the site test confirms the name on the individual and the marker fields equal an unnamed site's.
- [x] 1.4 Update `docs/development/adding-monsters.md` and `docs/development/monster-field-behaviour.md` for the renamed field and parameter. Check: `rg "individual_label" docs/development world tools` finds nothing.

## 2. Panels and protocol

- [x] 2.1 Add `monster_identity` to exploration targets and `look.entities`, and derive their `display_name` from a non-null identity. Move `EXPLORATION_SCHEMA_VERSION` to 7 with server validation. Check: exploration panel tests cover the identity cases, a changed key, and rejection of a mismatch.
- [x] 2.2 Add `monster_identity` to `ParticipantView` and the combat form with `display_name` from the identity, and move `CONTEXT_ACTIONS_SCHEMA_VERSION` to 8 with server validation. Check: combat view and panel tests cover the same cases, and the exploration and unavailable forms differ only in version.
- [x] 2.3 Mirror both versions, the identity validator and the `display_name` rule in `protocol/constants.js`, `panels/exploration.js` and `panels/combat.js`. Update Python, Node and Storybook panel fixtures. Check: `node --test web/static/webclient/js/tests/*.test.js` and the panel parity tests pass.

## 3. Client presentation

- [ ] 3.1 Add `components/monster-identity.js` with `isNamedMonster()` and `monsterDetailTag()`. Check: unit tests cover named, unnamed and null identity.
- [ ] 3.2 Carry the identity onto presence entries in `exploration_menu.js`. Add the `data-named` treatment to `PresenceRail.vue`, and the tag to `railReadout()` and `ExplorationReadout.vue` with a fixed lead line height. Add named states to the rail and readout stories. Check: Vitest confirms full DOM text for a five-code-point name, equal geometry against an unnamed entry, and readout lines that do not move.
- [ ] 3.3 Pass a named flag and tag to `FigurePlate.vue`, with the hairline, name treatment, and tag in `title` and `plateLabel()`. Add named, `target`, `acting` and fallen stories. Check: Vitest confirms equal geometry and full DOM text, and `agent-browser` shows each state keeping its cue at 1451x790 and 2560x1440.
- [ ] 3.4 Carry the identity onto `stage_targets.js` member positions, and add the tag to `ActionDock.vue`'s `summary.tags`, with the named name treatment. Check: tests cover unnamed, named, party member and null identity, and a repeated name still takes its session token.

## 4. Story and quest surfaces

- [ ] 4.1 Add `individual_name`, `species_name` and `variant_name` to `situation.py`, `ActionOptionsMonsterEntry`, its bounded mapping, and `prompt.py`. Check: action-options tests cover named, tier-only and over-long values, and the rendered prompt holds the facts.
- [ ] 4.2 Add `individual_name` to defeat data in `event_log.py` and `upkeep.py` when present. Check: event tests cover named and unnamed defeats, and kill accounting tests pass unchanged.
- [ ] 4.3 Render `討伐{name}` in `describe_objective_parts()` for a bound objective on a named site. Check: describe tests use a synthetic named site and an unnamed one, and no quest catalog data changes.

## 5. Integration checks

- [ ] 5.1 Run the focused suites from `design.md`'s capabilities, then `uv run --locked python -m tools.test_data_lint check`, `uv run --locked python -m tools.spec_traceability check`, `uv run --locked python -m tools.contract_gate`, `pnpm test` and `openspec validate monster-individual-names --strict`. Check: all exit zero, and new requirements have traceability annotations.
- [ ] 5.2 Rebuild a development database and confirm in the running client that a wilderness monster shows its species name, a boss site individual shows the named treatment, and `engage` matches both names. Check: record the result in the change notes.

## Workflow follow-up

- Archive the change after review, then sync its delta specs.
