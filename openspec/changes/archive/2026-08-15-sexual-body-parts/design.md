## Context

`docs/superpowers/specs/2026-08-15-sexual-act-resolution-design.md` §1 and
`docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md` D-8 already decided the
shape: a flat, ten-member body-part vocabulary for humanoid targets, plus one sentinel constant any
`Monster` target collapses to, so no per-monster-archetype anatomy table is ever needed. This change
implements only the vocabulary half of that decision — the constants — not the collapsing logic
itself, which needs `isinstance(entity, Monster)` and therefore cannot live in this dependency-free
module.

`world/lore/sexual_vocab.py` already exists and already exports `SENSITIVITY_LEVELS`, the ordered
tuple of sensitivity intensities (`普通`/`高`/`極高`/`敏感異常`). `SexualState.sensitivity` is
already a lazily-populated `dict[part_name, OrderedLevelTrait]` keyed by an arbitrary string — the
schema and the handler both accept any body-part key today, with no canonical vocabulary backing it.
This change supplies that vocabulary.

## Goals / Non-Goals

**Goals:**
- Give the future act catalog a fixed, canonical set of body-part names to declare
  `actor_part`/`target_part` against, with one owner for the value set.
- Give `Monster` targets a designated collapse target that structurally cannot collide with a real
  body part (enforced by tuple non-membership, not convention).
- Keep the addition inert: no behavior, no new dependency, no change to any existing tuple's value
  or any existing consumer's behavior.

**Non-Goals:**
- Implementing `resolve_part()` (the function that actually performs the `Monster` collapse). That
  function needs `isinstance(entity, Monster)`, and this module's own existing spec requirement
  (unchanged by this proposal) forbids any dependency on `world/rules/` — `Monster` lives in
  `typeclasses/`, one layer this module must not reach into either. `resolve_part()` ships in the
  later `sexual-act-effects` proposal (`B5`), which already owns the file it will live in
  (`world/rules/sexual_acts.py`).
- Constraining `CHARACTER_SCHEMA_V1`'s `sexual_baseline.sensitivity` property to `BODY_PARTS` keys.
  Two independent reasons: (1) `world/imports/schema.py` is exclusively owned by the
  `entity-sex-field` proposal in this same parallel batch — editing it here would create the exact
  merge conflict the batch's disjoint-file-ownership plan exists to prevent; (2) even setting
  ownership aside, retroactively constraining an existing schema property's key space is a separate,
  independently-scoped decision (it would reject the shipped example record's own `"general"` key)
  that this change does not need to make in order to deliver the vocabulary.
- Any act-catalog content. This change ships zero acts and zero references to any specific body
  part in a rule.

## Decisions

**D1: The new constants extend `world/lore/sexual_vocab.py` — they do not get a separate module,
despite `BODY_PARTS` not being an ordered-level vocabulary. This is a deliberate widening of the
module's scope, not the discovery of a rule that was silently in force all along.**

This deserves an explicit justification, because the sibling `entity-sex-field` proposal makes the
opposite call for a superficially similar case: `sex` gets its own new module
(`world/lore/sex.py`) rather than joining `sexual_vocab.py`, on the reasoning that it is not an
ordered level and belongs outside this module's stated purpose. Up to that decision, "ordered
level-name vocabulary" genuinely was the module's scope — both its current spec title and its
current requirement text say so, and `BODY_PARTS` fails that exact test too (there is no meaningful
intensity ordering among body parts).

This proposal widens the scope rather than reapplying the old test, and picks a specific, narrower
replacement rather than "any sexual-domain vocabulary": **"a vocabulary `SexualState`'s own fields
are built from."** `BODY_PARTS` passes that test — it is the key space `SENSITIVITY_LEVELS` values
are indexed by inside `SexualState.sensitivity`, a mapping that already exists and already imports
from this exact module. `sex` would still fail it even under the new, wider rule — it has no
relationship to any `SexualState` field; it is a general entity-identity property that a later,
unrelated mechanic happens to branch on. So the two sibling decisions remain compatible after the
widening, but that compatibility is confirmed against the new rule, not read backward into the old
one. The spec delta below states the widened scope explicitly, so a future addition is held to
"built from `SexualState`'s own fields," not to whatever criterion retroactively justifies it.

Alternative considered: a new `world/lore/sexual_body_parts.py`. Rejected on the coherence argument
above, and because it would leave `SENSITIVITY_LEVELS` (the values) and `BODY_PARTS` (the keys they
attach to) split across two modules for no structural reason — a future reader of
`SexualState.sensitivity` should find both halves of that mapping's vocabulary in one place.

**D2: `GENERIC_BODY_PART` is a bare string constant, not a member of `BODY_PARTS`.**

Non-membership is what turns "no act may declare the generic channel as its own part" into a
structural test (`GENERIC_BODY_PART not in BODY_PARTS`, checked once) rather than a convention every
future act author has to independently remember. This mirrors `DEFAULT_SEX`'s relationship to
`SEX_VALUES` in the sibling `entity-sex-field` proposal in shape (a named default/sentinel value
distinct from the enumerable set) but for a different reason there — `DEFAULT_SEX` **is** a member
of `SEX_VALUES` (it's the class-level default, meant to be selectable), whereas `GENERIC_BODY_PART`
is deliberately excluded from `BODY_PARTS` (it's a distinct out-of-band channel, never meant to be
selectable as an ordinary part).

**D3: `尾巴` (tail), present in an earlier draft as an example of an arbitrary monster body part, is
dropped rather than included as an eleventh `BODY_PARTS` member.**

The whole point of `GENERIC_BODY_PART` is that monsters no longer need a plausible-sounding body
part at all — a slime has no tail either. Keeping `尾巴` around as a `BODY_PARTS` member would imply
some monsters get a real part and others get the generic fallback, which is exactly the
per-archetype special-casing D-8 exists to avoid. If a future non-human *player* race needs a real,
selectable extra part, `SexualState.sensitivity`'s existing lazy-default behavior (any unseen key
resolves to `SENSITIVITY_LEVELS[0]` without raising) means adding one string to `BODY_PARTS` is a
complete, non-migrating change when that need actually arises — there is no cost to leaving it out
now.

## Risks / Trade-offs

- **[Risk] Widening `sexual_vocab.py`'s stated scope could invite unrelated future additions,
  eroding the module's coherence over time.** → **Mitigation**: D1 states the widened scope
  precisely ("vocabularies `SexualState` is built from," not "sexual-domain vocabularies
  generally") and this change's own spec delta updates the module-level requirement text to say so
  explicitly, giving a future reviewer a clear line to hold a later addition to.
- **[Risk] Shipping a vocabulary with zero current consumers could look like dead code to someone
  auditing the module without the design-doc context.** → **Mitigation**: the updated module
  docstring states directly that there is no current consumer and names the future proposals that
  will be — the exact same posture the six original tuples shipped under before `sexual-state`
  existed (their own requirement already documents "a future `sexual-state` change is expected to
  import these tuples"), so this is a repeated, not novel, pattern for this module.
- **[Risk] `BODY_PARTS`'s ten members might not match what the later act catalog actually needs**
  (too many, too few, wrong names). → **Mitigation**: accepted. Changing a tuple element or adding
  a member later is a one-line, non-migrating edit — `SexualState.sensitivity` has no fixed-key
  storage to migrate, per D3's reasoning — so getting this exactly right on the first attempt is not
  load-bearing.

## Migration Plan

None needed: purely additive constants, zero runtime consumers, zero persisted data affected.

## Open Questions

None. This change's scope is narrow enough that no material ambiguity remains after the design
docs' D-8 and §1 decisions.
