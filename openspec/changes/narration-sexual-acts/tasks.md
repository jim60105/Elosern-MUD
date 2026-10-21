# Tasks

## 1. Act rows, first three lines

- [x] 1.1 Author `world/skills/narration/data_sexual_partner.py` (every 關係 act, one or two
  attempt variants, performer/participant counter clauses where the act declares them) and
  verify the validator accepts it and two acts of the line select different openings.
- [x] 1.2 Author `world/skills/narration/data_sexual_solo.py` (every 自慰 act, including the
  observer-gated `watched` counter clauses) and verify the performer clause is selected for the
  caster's own counter entry.
- [x] 1.3 Author `world/skills/narration/data_sexual_shame.py` (every 羞恥 act, exposure wording
  without humiliation-as-spectacle) and verify the validator accepts it.

## 2. Act rows, last three lines

- [x] 2.1 Author `world/skills/narration/data_sexual_combat.py` (every 戰鬥 act, urgency
  register) and verify a combat-line act and a partner-line act select different openings.
- [x] 2.2 Author `world/skills/narration/data_sexual_interspecies.py` (every 異種 act, unfamiliar
  anatomy as wonder and risk) and verify its pair-event names resolve to the transition pool.
- [x] 2.3 Author `world/skills/narration/data_sexual_divine.py` (every 神之秘法 act, invocation
  only, deferring the law-giving imagery to the existing `divine_*` pool) and verify the line's
  act keys are covered.

## 3. Verdict, role and derived coverage

- [x] 3.1 Implement the verdict composition for `sexual_resist` (resisted / auto_complied /
  complied) and verify, with one synthetic act row, that all three verdicts share the act clause
  and differ only in the verdict clause, and that a resisted target receives no pleasure or
  counter entry.
- [x] 3.2 Implement role-aware `pleasure_gain` and `sexual_counter` selection from the act's
  sidecar declaration and verify the caster-versus-participant split with a synthetic two-body
  cast.
- [x] 3.3 Implement the catalog-derived transition and counter pools and their import validation;
  verify a synthetic act that adds an unknown event name or an unknown counter fails to load,
  and that the shipped sets match exactly.

## 4. Close the last family and verify

- [x] 4.1 Import the six act modules, add the 27 shared pool clauses and empty the frozen
  pending-family set; verify import fails when any act's row is deleted and the pinning test
  asserts an empty set.
- [x] 4.2 Extend the coverage-contract slice to assert exact act, event and counter key sets,
  then run the focused catalog, selection, pipeline and sexual act-effect modules and the
  traceability check; verify every assertion in this delta has a matching annotated test.
- [x] 4.3 Verify the player-visible result by hand: the reported `cast 挑逗=悠奈` transcript now
  reads as one story (act attempt, verdict, both participants' pleasure, the recorded counter),
  with no digit anywhere in the prose.

## Workflow follow-up

- Archive the change after review and merge, syncing the added requirements into the
  `action-narration` main spec.
