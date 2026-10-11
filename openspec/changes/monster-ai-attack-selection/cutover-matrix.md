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
