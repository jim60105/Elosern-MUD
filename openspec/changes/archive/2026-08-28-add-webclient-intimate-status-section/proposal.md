## Why

`docs/design/elosern-redesign/index.html`'s `#dr-status` drawer carries a collapsible `親密狀態`
(intimate-status) section (`index.html:1088-1100`) showing five level-word rows (興奮/濕潤/羞恥/露出/
高潮) plus a daily climax count, gated closed by default and prefaced with "詞彙封閉；數值依設定折線/
級別顯示" (vocabulary closed; values render per configured tier/level). `CharacterStatusDrawer.vue`
has no such section today, and its own code comment explains why: *"The 親密狀態 (intimate) block the
設計稿 shows has no backing field, so it is absent"* — a decision both roadmaps' non-goals also state
(`2026-08-25-webclient-hud-redesign-roadmap-design.md` §2.4/§3, migration roadmap §7): *"No new read
model, and therefore no ... 親密狀態 block ... each gets its own OOB change when its read model
lands."*

That premise is no longer true. `world/rules/sexual_state.py`'s `SexualState` handler already exposes
every level this section needs — `arousal` (derived from the `pleasure` gauge via
`PLEASURE_CONFIG`), `wetness`, `shame`, `exposure`, `climax_phase` (all `OrderedLevelTrait`s over the
fixed vocabularies in `world/lore/sexual_vocab.py`), and `climax_today` (a counter) — and
`world/rules/status_query.py` already has a no-create-safe reader for exactly this data: `_sexual_level()`
(used today to build the `status` panel's threshold-gated condition entries, e.g.
`high_arousal_agility_accuracy_penalty`, per `openspec/specs/webclient-status-presentation/spec.md`'s
"resolves the derived arousal level from stored pleasure" requirement). The read model this section
needs already exists; only its OOB exposure does not. Per both roadmaps' own governance rule ("if a
sub-change finds this roadmap wrong, it amends this roadmap rather than silently diverging"), this
proposal formally supersedes that specific non-goal clause rather than leaving it contradicted.

This is scoped separately from `fix-webclient-character-status-drawer-order` (section order and a
`屬性`/vitals duplication fix, no server change) because unlike that proposal, this one requires a new
bounded field in the `character` presenter — a small, additive server change, not a pure view-layer
edit.

## What Changes

- Add a new nullable `intimate` object to the `character` v4 panel payload (bumping
  `CHARACTER_SCHEMA_VERSION` 3 → 4), containing exactly `arousal`, `wetness`, `shame`, `exposure`,
  `climax_phase` (each one word from its fixed vocabulary tuple in `world/lore/sexual_vocab.py`) and
  `climax_today` (a non-negative integer). Never the raw `pleasure` percentage or any other raw
  numeric gauge — level words only, matching the existing "vocabulary closed" design already
  established for this domain (`SexualState.arousal`, the `high_arousal_agility_accuracy_penalty`
  condition, and the 設計稿's own "詞彙封閉" caption all already treat this state as word-level, never
  raw-number, presentation).
- Read this data through a new no-create-safe reader in `world/rules/status_query.py`, reusing the
  existing `_sexual_level()` function (already used by `status.py`'s condition-matching path) for the
  five ordered-level fields, plus a new `climax_today` counter reader following the same fail-closed,
  no-materialize pattern. `intimate` is `null` when no sexual-state record exists for the actor at all
  (baseline absent and handler never materialized); a present-but-malformed record fails the panel
  closed (`PanelUnavailableError`), matching every other section's existing degrade behaviour.
- Add a collapsed-by-default `親密狀態` section to `CharacterStatusDrawer.vue`, rendered last (after
  `偽裝`, before the trailing 錢包/背景 rows this drawer already carries — see design.md), using the
  設計稿's static hint copy verbatim and the same two-column stat-tile styling the drawer's other
  sections already use. Absent (`intimate: null`) renders no section at all — never a placeholder.
- Add Storybook stories to the existing `Data/CharacterStatusDrawer` story file covering: populated
  intimate state (collapsed by default, expandable), and `intimate: null` (no section rendered).
- Update the two openspec capabilities this touches (see below) and formally supersede the "no 親密狀態
  block" non-goal in the HUD redesign roadmap and the "no companion panel... no 親密狀態 block" line in
  the migration roadmap's §7, per each roadmap's own governance rule for a sub-change that finds the
  roadmap's premise outdated.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-exploration-menu`: "The character panel is an exact read-only version-3 panel"
  requirement bumps to version 4 and gains the `intimate` field.
- `webclient-contextual-hud`: the character-status drawer requirement's "The intimate block is absent"
  paragraph and scenario are replaced with a requirement that the intimate section renders when
  `character.intimate` is present, collapsed by default, and is absent (not placeholder-rendered) when
  `null`. (This delta is written against the drawer requirement's text as amended by
  `fix-webclient-character-status-drawer-order`, which this change depends on — see design.md.)
- `webclient-component-showcase`: the "full overlays / deferred surfaces / frozen manifest"
  requirement's deferred-surface list currently names "the intimate/adult status collapsible" as
  having no backing OOB read model. It is removed from that list and its "Deferred surfaces are absent,
  not mocked" scenario (Party panel, event-log Toasts, authored game-help browser, and the persistent
  objective tracker remain deferred and unchanged).

## Impact

- `world/rules/status_query.py` — a new `climax_today` no-create reader and a new `_read_intimate()`
  (or equivalent) building an `IntimateView`/`None`, wired into `CharacterReadModel`.
- `world/rules/tests/test_status_query.py` — coverage for the new reader (present/absent/malformed).
- `web/webclient/presentation/character.py` — `CHARACTER_SCHEMA_VERSION` 3 → 4, `_serialize()` gains
  `intimate`, `validate_character()` gains `_validate_intimate()` and the new required field in its
  exact-fields set.
- `web/webclient/presentation/tests/test_character_panel.py` — schema/validation coverage for
  `intimate` (present, `null`, and each malformed-shape rejection case).
- `web/webclient/presentation/tests/test_registry.py` — `test_character_unavailable_payload_stamps_the_registered_version`
  hardcodes schema version `3`; update to `4`.
- `web/webclient-app/components/CharacterStatusDrawer.vue` — new collapsible section + script wiring.
- `web/webclient-app/tests/data/character_status_drawer.test.js`,
  `web/webclient-app/stories/Data/CharacterStatusDrawer.stories.js`,
  `web/webclient-app/stories/fixtures.js` — new fixture fields, new assertions, new stories.
- `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js` — this file currently asserts the
  intimate block is absent; update it to drop that assertion (the remaining deferred surfaces —
  companion panel, event-log toasts, authored game-help browser, persistent objective tracker — stay
  asserted absent, unchanged).
- `docs/superpowers/specs/2026-08-25-webclient-hud-redesign-roadmap-design.md` §2.4/§3 and
  `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md` §7 — both amended to
  remove 親密狀態 from their "no backing read model" / deferred-surface lists, with a note dating and
  explaining the correction, per each roadmap's own governance rule.
