## 1. Renderer

- [ ] 1.1 Implement `display_stat_block(entity) -> str | None` in the new module `world/rules/displayed_stats.py`: fixed key order `atk_phys`, `agility`, `defense`, `magic_level`, `hp`, one `label：value` row per key with the canonical character-panel labels (`生命` / `攻擊` / `敏捷` / `防禦` / `魔法階級`), every value via `get_display_value()`; return `None` for non-living targets; omit (never raise on) missing or malformed trait rows
- [ ] 1.2 Add pure unit tests for `display_stat_block`: disguised entity shows disguised and true keys in fixed order, undisguised entity shows true values, non-living target returns `None`, missing-trait row omission, `hp` row shows the gauge's current value

## 2. Accessor hardening

- [ ] 2.1 Harden `get_display_value()` in `world/rules/traits.py`: treat a non-mapping `disguised_stats` record (e.g. integer, boolean) as "no disguise" and fall back to the true trait value instead of raising
- [ ] 2.2 Add a regression test for the non-mapping disguise record (accessor returns the true value; the block renders true values for that entity); keep existing `test_disguise_boundary` and `test_disguise_effect` tests green

## 3. Shared appearance integration

- [ ] 3.1 Add a `get_display_desc(looker, **kwargs)` override on `LivingEntity` (`typeclasses/entities.py`) that appends `display_stat_block(self)` after the description, following the `NPC.get_display_desc` affinity stage-line pattern; confirm the block appears for player, NPC, and monster targets and never for rooms or non-living objects
- [ ] 3.2 Verify the block ordering against the NPC affinity stage line (description → block → stage line) and that room look and the onboarding `at_look` arrival beat are unchanged; add/adjust integration tests accordingly (existing onboarding look-beat tests must stay green)

## 4. WebClient parity

- [ ] 4.1 Confirm `explore.look`'s target detail reaches the block through the shared appearance path (adjust the adapter only if the shared path does not already carry it); assert the action publishes no panel replacement and leaves the version-1 `exploration` payload untouched
- [ ] 4.2 Add a parity test: text 「看 <目標>」 and `explore.look` for the same living target produce identical appearance including the displayed-stats block, with no browser-side value computation

## 5. Contract and documentation

- [ ] 5.1 Update the `get_display_value()` docstring in `world/rules/traits.py` to state that appearance rendering (`look`) is implemented through the `look <target>` displayed-stats block while keeping the three-consumer wording (appearance rendering, guild registration records, appraisal items) and the combat/resolution/damage prohibition
- [ ] 5.2 Update the boundary contract test in `world/rules/tests/test_guild_registration.py` (the "appraisal" docstring assertion) to the implemented-consumers wording, and refresh its `covers_requirement` annotation to the canonical requirement ID
- [ ] 5.3 Update `docs/game/commands.md` and `docs/game/command-reference.md` for the documented `look <target>` output change (「看 <目標>」 now shows the displayed combat values), and keep `tests/test_command_docs.py` green
- [ ] 5.4 Record the master-design amendment in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (§5.2 / D2 note): the `look <target>` displayed-stats block is the implemented appearance-rendering consumer; appraisal items remain the forward-declared seam

## 6. Traceability and verification

- [ ] 6.1 Annotate the new main-spec requirements with `covers_requirement` (import from `tools.spec_traceability`) on the discoverable tests that establish them, using canonical IDs from `uv run --locked python -m tools.spec_traceability list`
- [ ] 6.2 Run `uv run --locked python -m tools.spec_traceability check` and `openspec validate displayed-stats-view --strict`; run the affected test domains (`world.rules` status/look/traits tests, `commands` localized look, `web.webclient` exploration actions) plus the onboarding and disguise-boundary regressions
