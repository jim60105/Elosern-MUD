# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [x] 1.1 Implement the shared agility contest and eligibility/no-pursuer/no-acting-allies branches; test slowest ally, fastest pursuer and ignored accuracy/Dodge.

## 2. Bounded implementation and evidence (1.5h)

- [x] 2.1 Commit all-party success with carried downed members, no invented destination/healing and one elapsed round; test enemy inactivity and terminal cleanup/time once.

## 3. Bounded implementation and evidence (1.5h)

- [x] 3.1 Implement failure as consumed allied opportunities plus enemy initiative/upkeep, without tactical benefits; test defeated pursuers, invalid enemy capability and fresh next draft.

## 4. Bounded implementation and evidence (1h)

- [x] 4.1 Exercise rollback after flee/session/time writes, double confirm and normal-round race; prove no subset escape or duplicate settlement.

## 5. Bounded implementation and evidence (0.75h)

- [x] 5.1 Document party versus enemy flee contracts, update canonical IDs, test annotations and shard ownership.

## 6. Integration gate (0.75h)

- [x] 6.1 Run focused retreat/disengage/provider/settlement tests plus tools.contract_gate and observability lint/focused event tests.

## Annotation timing

This change's own three new requirements (the retreat contest, the carried
all-party success, and the consumed-opportunity failure) have no identifier in
`openspec/specs/` until the archive step syncs the delta, and
`tools.spec_traceability check` rejects unknown identifiers. The new tests
therefore annotate only the existing main-spec requirements they genuinely
establish (`player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes`,
`...::combat-time-settles-once-at-terminal-session-outcome`,
`...::round-revisions-execute-at-most-once-across-retries-and-stale-requests`);
the added requirements' annotations must be attached during the archive sync,
exactly as the sibling changes in this batch did — the contest tests for
`retreat-contests-the-slowest-acting-ally-against-the-fastest-pursuer`, the
carried-party success tests for
`successful-retreat-carries-the-entire-present-party-and-counts-one-round`, and
the failure tests for
`failed-retreat-consumes-all-allied-actions-and-runs-one-ordinary-enemy-upkeep-round`.

## Shard ownership

No test module was added, renamed or moved: the new evidence lives in the
already-registered `world/rules/tests/test_combat_party.py`, and
`world/rules/tests/test_confirmed_surrender.py` only had one obsolete test
replaced in place. `.github/evennia-shards.json` and
`.github/browser-shards.json` therefore need no change, and no browser class or
method was touched. `tests.test_command_docs` stays green because no command
key, alias, syntax or availability context changed — only the two command
documents' prose.

## Local verification recorded

- Focused Evennia suites (focused labels only, never the full suite):
  `world.rules.tests.test_combat_party` (50), `world.rules.tests.test_confirmed_surrender`,
  `test_disengage`, `test_disengage_integration`, `test_combat_result`,
  `test_combat_round_record`, `test_combat_session_persistence` (126 together);
  `test_combat_session_flow`, `test_guild_exams`, `test_skip_safety`,
  `commands.tests.test_combat_exit_commands`, `commands.tests.test_combat_actions`,
  `commands.tests.test_command_branch_behaviour`,
  `web.webclient.actions.tests.test_combat_actions`, `test_combat_dispatcher`,
  `tests.test_command_docs`, `tests.test_evennia_test_optimization_contract`
  (205 together).
- Gates: `tools.contract_gate` passed (traceability 2242/2242 covered, 0 errors;
  observability 0 violations; test-data 0 violations; manifests; contracts);
  `tools.observability_lint check` 0 violations. No logging behaviour changed:
  the retreat reuses the ordinary round's `combat_round_settled` boundary (its
  elapsed round emits it like any round) and the settlement's existing
  `settlement_done`, so no new event or catalog row was added.
- The browser flee row is still deliberately rejected (`combat_actions.py`,
  `PARTY_EXIT_UNAVAILABLE`) until `webclient-party-exit-confirmation` ships the
  confirmation window; this slice's retreat acceptance is the text-command path.
