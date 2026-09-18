## Context

`entity.db.disguised_stats` is a display-only mapping from a subset of trait keys to override values,
read through the single sanctioned accessor `get_display_value()` and written by five classified
production sites, of which exactly one — `world/rules/skill_effects.py` — is a runtime cast write. The
attribute is already registered in the snapshot lists in `world/rules/cast_settlement.py` and
`world/rules/clock.py` and in the entity-state snapshot behind the `traits` surface. `divine-veil-
cast-path` (a dependency) makes the runtime write actually produce a veil. See `proposal.md` — Why for
motivation.

## Goals / Non-Goals

**Goals:**

- Make "only a divine mystery can pierce a divine veil" a rule the engine enforces rather than a
  sentence in a lore page.

**Non-Goals:**

- Writing or storing the provenance record. `divine-veil-cast-path` owns it; this change reads it.
- Any contest, roll, or success chance. The lore is explicit that this is a class boundary, not a
  probability (`docs/lore/skill-trees/utility.md`).
- Revealing anything other than the disguise layer — no true-stat readout, no identity reveal, no
  persona exposure.
- Changing what the mundane appraisal lineage can do. `true_sight_appraisal` keeps its current
  behavior and keeps failing against a divine veil.

## Decisions

### D1: Provenance is consumed, not defined, here

`divine-veil-cast-path` writes the record and registers it in every snapshot path, because its
provenance-scoped self-toggle needs it first. This change reads it and nothing else, so the two
strengths have a source of truth that already exists by the time they land.

### D3: Exactly two strengths, encoded in the prefix grammar

The bare prefix clears a mundane veil only; `reveal_disguise:true_name` clears any veil. Two closed
forms, validated at parse, so an authoring mistake fails at registry load rather than at cast. A
numeric ladder would invite a third strength nobody has designed.

### D4: A reveal that cannot pierce is a no-op, not a rejection

Rejecting would leak information — the caster would learn "there is a divine veil here" from the
rejection reason without piercing it. A clean no-op keeps the action's cost paid and the information
boundary intact. It also matches the lore's framing: you looked, and you did not see through.

### D5: The write stays in the classified writer module

Both the provenance write and the reveal's clear route through `world/rules/skill_effects.py`, so the
disguise boundary's writer ledger and its regression scan need no new entry, and the "no combat module
reads the layer" boundary is untouched.

## Risks / Trade-offs

- **Provenance drifting out of sync with the mapping** → both are written in the same staged effect by
  the same module; a test asserts a reveal that clears the veil also clears the provenance.
- **The no-op reveal reading as a bug to players** → the resolver reports the attempt; the distinct
  narrative for "nothing was hidden here" versus "you could not see through" is a presentation concern
  outside this change's contract, and the task list only requires that both outcomes be reported
  distinctly enough to test.
