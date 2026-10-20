# Design

This change authors content inside the engine and catalog contract established by
`narration-core-and-combat-prose`; read that change's design before this one. No decision here
changes the selection algorithm, the bounds, the band tables, or the pipeline integration.

## D1. One authored row per skill, keyed by the registry's own key

Each of the 42 non-elemental ACTIVE skills gets exactly one `NarrationRow` in the data module
of its family, keyed by the shipped skill key. Rows carry one or two `action` variants (the
attempt, not the result — the outcome clause is shared, so a miss and a hit read correctly from
the same opening) and, only where the skill's identity is the point, `kind_lines` overrides.

Rejected: authoring full hit/miss/defeat sentence sets per skill. It multiplies the content by
four for no story gain, because the shared outcome pools already carry the beat-specific
information, and it would make the line count impossible to review in one day.

## D2. Register per family

- **Martial arts (16)**: steel and shadow — footwork, blade arcs, the body's discipline; no
  wuxia vocabulary (no 內力/真氣/江湖 register).
- **Holy rites (14)**: liturgical light — consecration, shelter, absolution; the line names the
  rite's act, never a mechanic.
- **Divine mysteries (11)**: the authority of the divine speaking through the caster; the
  existing `divine_*` kind pools already carry the law-giving imagery, so rows add only the
  invocation.
- **Enhancement (1)**: the body answering its own training.

Each family module mirrors the registry's `data_*.py` shape: a module docstring naming the
family and its register, then one contiguous in-order tuple of rows. Order is authoring order,
not a behavioural input.

## D3. Coverage and distinctness verification

- The coverage contract slice asserts exact key-set equality between the four families' ACTIVE
  skills and the authored rows, so a missing or extra row fails.
- A mechanics test asserts that two different skills in the same family select different
  opening lines for the same target and scope inputs (distinctness by construction, not by
  reading the prose back).
- Bounds, the no-digit rule and the slot budget are already enforced by the catalog validator;
  these rows inherit that check with no new validation code.

## Traceability

The delta's requirement is covered by the coverage-contract slice in
`world/skills/tests/test_skill_registry/test_narration_coverage.py` (exact key-set equality for
the four families, tagged `Data-contract test:`) plus the distinctness assertions in
`world/skills/tests/test_narration_catalog.py`. Both modules already exist and already carry a
shard owner (`world.skills`), so this change adds no manifest entry and no new test module.

## Risks / Trade-offs

- **Tone drift between families.** The register list in D2 is the review checklist; the catalog
  validator cannot check taste.
- **Pending-set shrink is a hard gate.** Once these four families leave the pending set, any
  new skill in them without a row breaks server start by design. That is the intended
  fail-closed behavior, and the pinning test names it.
