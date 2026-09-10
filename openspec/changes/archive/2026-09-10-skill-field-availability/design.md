## Context

The approved brainstorming design for this work is
`docs/superpowers/specs/2026-09-10-field-combat-initiation-design.md`; this
change implements its D-7 and D-8.

Current state of the flag, measured rather than assumed:

- `SkillDef.usable_out_of_combat` is a required field with default `False` at
  both registry construction helpers (`world/skills/registry.py:270` and
  `:308`).
- Ten registry entries declare `True`: `flight`, `flash_step`,
  `status_disguise`, `dominion_art`, `divine_sexual_arts`,
  `divine_time_dilation`, `divine_space_distortion`,
  `divine_matter_transmutation`, `divine_life_extension`, and the generated
  `_body_multiplier` tiers.
- The whole sexual-act catalog declares `True` at
  `world/skills/sexual_acts/_builder.py:304`.
- `flee` declares `False` at `world/rules/disengage.py:38`.
- 54 damage-effect declarations exist across `registry.py`; none is `True`.
- The flag is consumed at exactly two sites, `world/rules/action.py:310` and
  `world/rules/action_preview.py:141`, and after `out-of-combat-damage-gate`
  those two sites also carry the damaging-action gate.

The owner's instruction is explicit: review the catalog, mark `False` only what
is genuinely unsuitable, accept that the answer may be "all of them are
suitable", and keep the field because content authoring is unfinished.

## Goals / Non-Goals

**Goals:**

- Replace a default with a decision for every skill in the catalog.
- Write the decision rule into the spec so a future author applies the same
  judgement instead of re-deriving one.
- Make an undecided new skill a test failure rather than a silent `False`.

**Non-Goals:**

- Any routing, gating, or resolution behaviour. This change edits data and adds
  a test; it introduces no branch.
- Rebalancing costs, targets, elements, categories, or prerequisites.
- Deciding whether an out-of-combat cast opens combat. That is
  `field-combat-initiation`.
- Touching item use.

## Decisions

**D-1. The rule: `ACTIVE` skills are `True` by default judgement, `False` only
by exception.** A skill is `False` when casting it with no fight in progress is
meaningless (nothing for the effect to act on) or would bypass a subsystem that
owns that outcome. Everything else is `True`.

Alternatives rejected:

- *Keep `False` as the conservative default and flip skills as features need
  them.* Rejected by the owner's direction, and it is the status quo that
  produced an unexamined distribution.
- *Derive the flag from `SkillCategory`.* Rejected: categories group by flavour
  (`ELEMENTAL_MAGIC`, `MARTIAL_ARTS`, `MOVEMENT`, `UTILITY`, `ENHANCEMENT`),
  not by whether an effect makes sense outside a fight, and a derived value
  could not be overridden per skill without reintroducing the same field.
- *Derive it from the effect list.* Rejected for the same reason plus a
  concrete counterexample: `DamageEffect` skills are `True` under this policy,
  so an effect-derived rule would have to encode the very exception it was
  meant to avoid.

**D-2. `flee` stays `False`.** There is nothing to disengage from outside
combat, `flee` is reserved away from the ordinary cast surface
(`RESERVED_FLEE_KEY` in `web/webclient/actions/combat_actions.py`), and
`disengage-action` already owns its contract. Declared at its own construction
site in `world/rules/disengage.py`, consistent with that capability's rule that
`flee` declares its own metadata there.

**D-3. `basic_attack` becomes `True`, and the archived clause is amended
honestly.** `universal-action-ownership` says "unusable outside combat". After
this change the flag permits *selection* from exploration, while
`out-of-combat-damage-gate` still refuses *resolution* without a battlefield —
so the skill remains unusable outside combat in the sense the original clause
cared about. Rewording rather than silently contradicting it keeps the archived
requirement true.

Rationale for the flag change itself (brainstorming D-7): without it, clearing
a trivial monster from exploration would force the player to spend MP or SP on
a real damage skill, because `explore.engage` deliberately performs no action.

**D-4. Damage-carrying skills become `True`.** Their only out-of-combat use is
opening a fight, and that use is confined by the damaging-action gate. Leaving
them `False` would mean `field-combat-initiation` has nothing to open combat
with — the gap that motivated this whole sequence.

**D-5. `PASSIVE` skills get a deliberate value even though the flag is inert
for them.** The capability step rejects a passive with `SKILL_NOT_ACTIVE`
before the out-of-combat gates can matter, so the value is unobservable today.
Two of them (`flight`, `flash_step`) nevertheless already declare `True`, and
the generated `_body_multiplier` tiers do too. Rather than leave a field whose
value is arbitrary for a third of the catalog, the audit records a deliberate
value for every entry and the inventory test pins it, so the field cannot rot
into noise.

**D-6. The contract is a frozen inventory of the `False` set, not a per-skill
requirement.** The test asserts that the set of keys declaring `False` equals
an explicit literal set. This works *because* the dataclass default is
`False`: a newly authored skill falls outside the pinned set and fails, forcing
its author to either justify an addition to the set or declare `True`.

Alternatives rejected:

- *Pin the `True` set instead.* Rejected: a new skill defaults to `False`, so
  pinning `True` would let it land undecided and green.
- *Assert only that damage skills are `True`.* Rejected: it would leave the
  rest of the catalog unpinned and the field would drift again.
- *A shrink-only allow-list file like `tools/observability_freeze.json`.*
  Rejected as heavier than needed; the `False` set is small and belongs beside
  the assertions that explain it.

## Risks / Trade-offs

- **[A wrong judgement makes a skill castable in exploration where it makes no
  sense.]** → Nothing damaging can resolve outside a battlefield, so the worst
  case is a harmless or self-affecting cast. The inventory test makes each
  judgement visible in one place for later correction, and content is
  explicitly unfinished.
- **[The frozen inventory becomes a chore every time a skill is authored.]** →
  That is the intended cost: one deliberate line per new skill, in exchange for
  the field never silently defaulting again. The failure message names the
  undecided key.
- **[This change is behaviourally inert on landing, so tests prove data, not
  behaviour.]** → Accepted and stated. The behaviour it enables is verified in
  `field-combat-initiation`; here the assertions are about the policy and the
  inventory, which is exactly what this change owns.
- **[Amending an archived requirement about `basic_attack` could look like
  weakening it.]** → The amended clause is strictly more precise: it separates
  selectability from resolvability and names the gate that enforces the latter.
- **[`world/skills/registry.py` is large and the edit touches many lines.]** →
  The edit is one keyword per construction site with no logic change, and the
  elemental-spell families are edited at their shared builder rather than per
  row wherever the judgement is uniform.
