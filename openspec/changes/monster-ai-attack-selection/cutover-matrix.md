# Legacy policy contract cutover

This change modifies existing policy requirements without retiring their headings or canonical IDs. IDs must be generated against the equivalent delta-applied tree. Every retained legacy assertion continues to establish permanent legacy behavior; utility has separate requirements.

| Existing requirement or affected assertion | Role | Updated establishing behavior | Test owner |
| --- | --- | --- | --- |
| Complete drop-in provider and no round edits | Synthetic mechanism / production smoke | Two-argument provider, real normal/overwhelm context and actual slot/round scope with resolver-only settlement | test_monster_ai_selection plus existing overwhelm/session tests |
| Zero-action source token prohibition | Synthetic mechanism | Provider skipped by ordinary capability gate and direct utility inspection excludes illegal actions with no writes | test_monster_ai_selection and test_monster_ai_snapshots |
| Offline source-import scan and shared RNG assertion | Synthetic mechanism | Disabled network/model access; stable legacy dice and independent utility selection dice | test_monster_ai_selection and existing determinism tests |
| Target selection and target randomness source inspection | Synthetic mechanism | Permanent legacy metric/order/one tie-break draw, displacement and unchanged following dice | Existing test_monster_behaviour_policy and test_monster_behaviour_determinism |
| Skill selection and estimate source inspection | Synthetic mechanism | Permanent legacy ownership/cost/identity, no estimate dice except established tie, no effects during choice | Existing policy/determinism tests |
| Expected damage tie, AREA-first shape and authored first-owned fallback | Synthetic mechanism | Existing behavior qualified to legacy, while utility plans score legal candidates and preserve shape/scale | Existing policy and resource-skill mechanism tests |
| Tier golden fixture | Synthetic mechanism | Existing distinct legacy target decisions replay under fixed seed; utility intelligence is independent of tier | Existing test_monster_behaviour_golden |
| Non-monster delegation requirements | Synthetic mechanism | Intentionally unchanged and still directly compared with delegated policy | Existing delegation tests |

Source-text assertions cannot establish runtime behavior and are replaced within the implementing change. Retained meaningful scenario coverage must not be weakened. Review MODIFIED annotations individually; avoid blanket identifier replacement, source-layout expectations, shipped tuning approval tables or exact prose checks.

## Assertion ledger

Canonical requirement IDs were generated with `tools.spec_traceability list`
against the equivalent delta-applied spec tree (the delta spec merged into
`openspec/specs/`) and never hand-derived from titles.

The three `monster-action-policy` requirements this change modifies keep their
current canonical IDs, and the behavioral evidence attached under them in this
change is:

| Requirement ID | Establishing test |
| --- | --- |
| `monster-action-policy::monster-behaviour-policy-is-a-complete-drop-in-action-provider` | `test_monster_ai_selection.UtilityAdapterTests.test_the_adapter_preserves_the_shorthand_and_settles_committed_state`, `test_monster_ai_selection.LegacyRetentionTests.test_a_late_rejection_is_never_reselected` |
| `monster-action-policy::no-llm-or-generative-layer-involvement-anywhere-in-monster-decision-making` | `test_monster_ai_selection.LegacyRetentionTests.test_a_legacy_variant_keeps_the_legacy_body_and_one_dice_draw`, `test_monster_ai_selection.LegacyRetentionTests.test_a_decision_completes_with_network_access_disabled` |
| `monster-action-policy::a-monster-with-zero-actions-per-turn-is-skipped-by-the-existing-gate-with-no` | `test_monster_ai_selection.LegacyRetentionTests.test_the_zero_action_gate_never_invokes_the_provider` |
| `monster-action-policy::target-selection-differs-by-archetype-and-is-deterministic-under-a-fixed-seed` | `test_monster_ai_selection.LegacyRetentionTests.test_the_legacy_body_still_consumes_no_selection_rng` |

The replaced source-only assertions are gone: the zero-action token
prohibition is now the gate-and-inspection behavior above, and the offline
source-import scan is now the disabled-network decision above plus the
independent selection dice established by
`test_monster_ai_selection.UtilityInspectionTests.test_selection_dice_are_independent_of_the_combat_dice`.

The new capability's own five requirement IDs are
`monster-ai-utility-selection::utility-attack-score-reflects-continuous-intelligence`,
`monster-ai-utility-selection::selection-uses-stable-independent-softmax`,
`monster-ai-utility-selection::actual-execution-identity-distinguishes-every-decision`,
`monster-ai-utility-selection::production-adapters-preserve-decision-semantics`
and
`monster-ai-utility-selection::invalid-state-fallback-is-narrow-and-observable`.
Their establishing tests already exist with substantive assertions
(`ScoreArithmeticTests`, `SamplingTests`, `PreferenceTests`,
`ExecutionScopeTests`, `UtilityInspectionTests`, `UtilityAdapterTests`,
`InvalidStateTests`, `TraceTests` in
`world/rules/tests/test_monster_ai_selection.py`), but the annotations are
attached in the archive/sync commit rather than here: the traceability index
reads `openspec/specs/` only, so a delta-only ID reports
`unknown-requirement-id` and fails `tools.contract_gate` until the delta is
synced (the same deferral the previous monster-AI slices recorded).
