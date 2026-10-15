# Proposal: context_actions v6 — participant conditions and skill polarity

## Why

Two client changes in the combat batch need facts the combat panel does not send:

- `webclient-combat-figure-plates` replaces the participant roster with a plate on each stage figure, and a plate shows
  conditions as glyphs. The combat participants carry no conditions today.
- `webclient-combat-cross-side-confirm` asks before a cast that is aimed across sides, deciding only from declared facts.
  Skill descriptors carry no effect direction today. The user asked that debuffs, drains, sexual effects and
  beneficial buffs count too, using the registry's own classification.

## What Changes

- Each combat **participant** gains `conditions`: up to 8 rows of `code`, `label`, `severity`, derived by the same
  read model the status panel uses for its actor (`build_status_read_model(entity).conditions`), in that order; an
  entity without condition state carries `[]`.
- Each combat **skill descriptor** gains two required booleans, `hostile` and `beneficial`: whether an effect routed to
  the chosen targets (`EffectAudience.SELECTED`, recipient not actor-bound) is classified hostile or beneficial.
- A static **effect-kind classification** (`world/skills/effects/polarity.py`): every effect dataclass the parser can
  produce is classified `hostile`, `beneficial`, `neutral`, or `buff-definition` (a buff application takes its buff
  definition's declared `polarity`: `debuff` hostile, `buff` beneficial). An exhaustiveness test fails on an
  unclassified kind. No amounts or formulas.
- `context_actions` moves to **schema version 6**. This touches the server registry and validator, the client
  `PANEL_ALLOWLIST` and its mirror, and the version-parity contract. The mirror rejects version-5 payloads.
- This change replaces the `harms`/`restores` pair that `webclient-combat-cross-side-confirm` proposed earlier with
  `hostile`/`beneficial`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-combat-menu`: "Combat context actions are an exact read-only panel" (v6), "Combat presentation
  enumerates complete deterministic choices" (participant `conditions`, skill `hostile`/`beneficial`, classification).
- `webclient-context-actions`: renames and amends "context_actions is an exact read-only version-6 panel".
- `webclient-context-actions-suggestions`: renames and amends the version-6 envelope and v6 mirror requirements.
- `webclient-component-showcase`: the action-dock family and skill-surface requirements name v6.

## Impact

- Server: `world/skills/effects/polarity.py` (new), `world/rules/combat_view.py` (`ParticipantView.conditions`,
  `SkillDescriptorView.hostile`/`.beneficial`), `web/webclient/presentation/combat_panel.py` (version, serializer,
  validator, bound `MAX_PARTICIPANT_CONDITIONS = 8`).
- Client wire: `web/static/webclient/js/elosern/protocol/constants.js` (version, bound),
  `protocol/panels/combat.js` (participant and skill validators).
- Fixtures and tests that build combat panels (Python `_support.py` helpers and `world/rules/tests/test_combat_view.py`
  keyword constructions; JS `protocol_fixtures.js`, webclient-app and Storybook fixtures).
- Traceability: the three renamed requirements get new IDs; tests annotated with the old IDs are re-annotated.
- No client presentation change; telnet unchanged.

## Batch: webclient combat stage

Final apply/archive order: 1 `webclient-combat-panel-v6` → 2 `webclient-combat-formation-engine` →
3 `webclient-combat-formation` → 4 `webclient-combat-figure-plates` → 5 `webclient-combat-defeated-foes` →
6 `webclient-combat-command-card-centred` → 7 `webclient-combat-stage-target-picking` →
8 `webclient-combat-cross-side-confirm`.

- depends-on: none
- Code conflicts: every later change's tests share fixture files with this change (`stories/fixtures/combat_stage.js`,
  `web/static/webclient/js/tests/protocol_fixtures.js`), so later changes rebase on the v6 fixtures. No code conflict with
  `webclient-combat-formation-engine` (a pure client module), so the two may be implemented in parallel worktrees;
  archive this one first.
