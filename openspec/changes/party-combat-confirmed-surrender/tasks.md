# Tasks

Total estimate: **6 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [x] 1.1 Add bounded revision/session/operation confirmation tokens and atomic admission; test cancel, stale, cross-account/session/operation tokens and round-vs-surrender races.

## 2. Bounded implementation and evidence (1.5h)

- [x] 2.1 Implement confirmed surrender through existing settlement with receipt/draft cleanup; test hostile aftermath, exam FAIL, zero added round and once-only accumulated time.

## 3. Bounded implementation and evidence (1h)

- [x] 3.1 Remove direct public unconfirmed forfeit/allied-flee bypasses, route existing text aliases to explicit token prompts and preserve enemy flee; test forged calls and confirmation replay.

## 4. Bounded implementation and evidence (0.75h)

- [x] 4.1 Inject technical failure during settlement and test draft/cache restoration and retry; document confirmation protocol and existing command syntax.

## 5. Bounded implementation and evidence (0.75h)

- [x] 5.1 Update both command docs, command manifest expectations, traceability and shard registration for changed availability/confirmation.

## 6. Integration gate (0.5h)

- [x] 6.1 Run focused exit/aftermath/exam/command tests plus tools.contract_gate and observability lint/focused boundary-event tests.

## Annotation timing

This change's own new requirement (the session/round/operation-bound party exit and its surrender settlement) has no identifier in `openspec/specs/` until the archive step syncs the delta, and `tools.spec_traceability check` rejects unknown identifiers. The new tests therefore annotate only the existing main-spec requirements they genuinely establish (`player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes`, `...::combat-time-settles-once-at-terminal-session-outcome`, `...::round-revisions-execute-at-most-once-across-retries-and-stale-requests`); the added requirement's annotations must be attached during the archive sync, exactly as the sibling changes in this batch did.

## Local verification recorded

- Focused Evennia suites (focused labels only, never the full suite): `world.rules.tests.test_confirmed_surrender` (13), `commands.tests.test_combat_exit_commands` (3), `world.rules.tests.test_guild_exams`, `test_combat_view`, `test_combat_party`, `test_combat_session_persistence`, `test_combat_round_record`, `test_combat_session_recovery`, `test_combat_session_flow`, `test_combat_session_targeting`, `test_skip_safety`, `commands.tests.test_combat_actions`, `commands.tests.test_command_branch_behaviour`, `web.webclient.actions.tests.test_combat_actions`, `test_combat_dispatcher`, `tests.test_evennia_test_optimization_contract`, `tests.test_command_docs`.
- Gates: `tools.contract_gate` passed (traceability, observability, test-data, manifests, contracts); `tools.spec_traceability check` 0 errors; `tools.observability_lint check` 0 violations; no logging behaviour changed, so the existing `settlement_done` boundary event is the only observability surface a confirmed surrender emits.
- Browser: the three affected methods (`web.tests.browser.test_browser_combat_menu.CombatMenuBrowserTest.test_self_skill_submits_no_target_field`, `web.tests.browser.test_browser_combat_scales.CombatMenuBrowserTest.test_panel_advertises_scales_only_for_the_mastered_element`, `...test_panel_groups_skills_by_category_in_enum_order`) pass as short standalone runs (2 + 1 tests, ~124 s total) **after building the worktree's own `web/static/webclient/app/dist` bundle** (`pnpm install --frozen-lockfile && pnpm run build`; the bundle is git-ignored and absent in a fresh worktree, which is what made the earlier attempts fail at login with `connected: False`). No browser test was added, renamed or moved, so `.github/browser-shards.json` is unchanged.
