# Design

Authors content inside the contract established by `narration-core-and-combat-prose`; read that
design first, especially D4 (action line rides the first entry), D5 (bands) and D8 (verdicts and
roles). Selection, bounds and pipeline integration are unchanged.

## D1. The act row authors the attempt; the verdict clause completes it

For a contested cast (a resistible act against another target) `sexual_resist` is the cast's
first entry and always carries a verdict. A row's `action` therefore describes what the caster
does and where the touch is aimed, ending on a turn that reads naturally before any of the three
verdict clauses:

```
<act attempt clause> + <verdict clause: comply | auto_comply | resist>
```

One row per act is enough for every verdict, and a resisted cast never claims contact it did not
have. The act's *failed* shape (every target resisted) is the resist clause on every resist
entry; the opening carries the attempt once and the later entries carry only the clause.

A self-target or non-resistible cast never stages a resist entry, so its opening composes the
same attempt line directly against its first outcome clause (the act's own pleasure line). The
attempt wording stays valid there because it still describes the act rather than a resolved
contact.

Rejected: authoring separate comply/resist sentences per act. It triples the rows to say the
same thing, and it lets the two halves drift (an act line that asserts contact plus a resist
clause that denies it).

## D2. Per-act overrides use facts the act already declares

- **Bodily focus**: each row voices its own `pleasure_gain` clause for the acting body and for
  the receiving body (`performer_lines`/`participant_lines`), because only the act knows where
  it is aimed. An act that declares no own clause — the divine mysteries, which narrate from
  the `divine_*` pools — still renders from the shared role pools, whose four bands supply the
  intensity. The band id stays part of the selection seed, so a row that authors more than one
  role variant still varies with intensity even though its own clause carries no numbers.
- **Counters**: `actor_counters` means the performer did something (`duo_act_count` for the
  acting body), `participant_counters` means both bodies recorded it. The row supplies one
  performer clause and one participant clause per counter it declares; the selector picks by
  whether the entry's participant is the caster and by which tuple declares the counter.
- **Events**: `sexual_events`, the event effects an act's skill row stages, and the
  `pair_events` values name the transition; the transition pool holds one clause per name.
  The three pair-event names (`first_vaginal_penetration`, `penetrative_sex_with_female`,
  `penetrative_sex_with_male`) each need a clause even though only two acts fire them today,
  because the selection happens at cast time from the participants' sexes.

## D3. Coverage is derived from the catalog, not hand-listed

At import:

- every key of `SEXUAL_ACT_REGISTRY` has a row;
- the transition pool's key set equals the union of every act's `sexual_events`, every event
  effect its skill row stages, and every `pair_events` value — 11 names today;
- the counter pool's key set equals the union of every act's `actor_counters` and
  `participant_counters` — 8 names today, each with both a performer and a participant clause.

Adding an act with a new event name or a new counter therefore fails at import until its prose
lands. Rejected: a hand-maintained "supported events" list, which is exactly the second source
of truth the registry discipline forbids.

## D4. Registers per line

| line | register |
| --- | --- |
| 關係 (partner) | intimacy, closeness, mutual attention |
| 自慰 (solo) | private, bodily, unhurried |
| 羞恥 (shame) | exposure and its heat; never humiliation-as-spectacle |
| 戰鬥 (combat) | urgency, adrenaline, the fight bleeding into touch |
| 異種 (interspecies) | unfamiliar anatomy as wonder and risk, never gore |
| 神之秘法 (divine) | law-giving authority; the existing `divine_*` pool already carries the imagery, so rows add only the invocation |

## D5. Verification

- Coverage: exact act-key set, exact transition-name set, exact counter-name set.
- Verdict: the same act under `comply`, `auto_comply` and `resist` yields the same act clause
  with three different verdict clauses, and the resist case emits no pleasure or counter entry
  for the refusing target.
- Role: the caster's own `pleasure_gain` and `sexual_counter` entries select the performer
  clause; another participant's select the participant clause.
- Bounds and the no-digit rule are inherited from the catalog validator.

## Traceability

The delta's requirements are covered by `world/skills/tests/test_narration_catalog.py` (verdict
composition, actor-versus-participant voice, role-aware counters — synthetic rows) and the
coverage-contract slice in `world/skills/tests/test_skill_registry/test_narration_coverage.py`
(exact act, event and counter key sets, tagged `Data-contract test:`). The pipeline-side
assertion that a resisted target receives no pleasure or counter entry lives in
`world/rules/tests/test_event_narration_pipeline.py`. All three modules already exist and carry
a shard owner, so no manifest entry and no new test module is added.

## Risks / Trade-offs

- **Content sensitivity and volume.** 66 rows plus 27 pool clauses in one day. Lines stay short
  (one clause), and the six act-line modules keep the authoring order identical to the registry,
  so review is a straight comparison against `world/skills/sexual_acts/*.py`.
- **Pair event names are symmetric.** The same event name may describe two orientations; the
  clause must not assume who penetrated whom. The row's own act supplies the perspective, the
  pool clause stays neutral.
- **Empty pending set is irreversible pressure.** Any future ACTIVE skill anywhere now needs a
  row before it can start the server; that is the intended fail-closed end state.
