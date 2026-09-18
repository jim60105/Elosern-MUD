## Context

`world/rules/skill_effects.py` owns the deterministic-core write behind 統御術.
`record_conferred_grant(entity, source_key, skill_key, scale)` validates the *shape* of the conferred
skill (`validate_conferrable_skill`: no gate-type effect, at least one continuous-valued effect) and
appends a `ConferredSkillGrant` to `entity.db.skill_grants`. Two consumers read the store:
`SkillHandler.effective_value()` folds `source_multiplier × grant.scale` into a trait multiplier, and
the `skill_owned` rule-table builder folds a scaled rule adjustment. `EffectPolicy` is already
index-aligned with `SkillDef.effects` (the registry pads it to match; `action.py` reads
`skill.effect_policies[ordinal]`), and `EffectPolicy.coefficient` is already validated as a finite
positive per-occurrence magnitude. See `proposal.md` — Why for motivation.

## Goals / Non-Goals

**Goals:**

- Make the conferral verb castable from the shipped cast paths with no new player input surface.
- Make the store idempotent per `(source, skill)` and tie every grant to something its source owns.
- Put the ladder's strength in node data, where the lore prices it.

**Non-Goals:**

- Revocation. `conferral-revocation` owns removing a grant.
- A player-facing picker for which skill to confer (see D3), and therefore no command-syntax change,
  no webclient action-option change, and no `docs/game/command-reference.md` change.
- Any change to how `effective_value()` or the rule-table builder fold a grant. The read side is
  correct; only the write side is not.
- Any expiry or duration on a grant. A grant stays until revoked, which is what the lore prices.

## Decisions

### D1: Replace by `(source_key, skill_key)`, not by `skill_key` alone

Two different elves conferring the same passive are two independent facts and both should count; the
same elf conferring it twice is one fact stated twice. Keying on the pair preserves the first and
collapses the second. The buff store already models exactly this with `conferred_growth_rate`'s
`stacking: unique_per_source`, so the two halves of the conferral vocabulary now agree.

*Alternative rejected:* keeping the append and de-duplicating at read time in `effective_value()`. It
would leave a growing list on disk and put the invariant in two consumers instead of one writer.

### D2: Source ownership is validated at the resolver boundary, not inside the core write

`record_conferred_grant` receives `source_key` as a string and has no entity to interrogate; the
handler has the actor. A `validate_source_owns_skill(actor, skill_key)` in
`world/rules/skill_effects.py` keeps the check in the same module as the write — one place to read the
whole conferral contract — while being called where the actor exists. Direct ownership is
`actor.skills.owned_keys()`, the predicate `_step1_ownership` already trusts, so a conferred grant can
never itself be re-conferred onward.

*Alternative rejected:* widening `record_conferred_grant`'s signature to take the source entity. It
invites callers to pass a stale entity for one check.

### D3: The conferred set is derived from direct ownership, not chosen

A conferral records one grant per directly-owned skill that passes `validate_conferrable_skill`. This
removes the only reason the handler ever needed `event_context`, needs no picker on any surface, and
makes the chain ladder read cleanly: the nodes differ by **scale and audience**, never by which power
gets lent. It also expresses boundary clause 2 structurally — the set is literally what the caster owns.

*Alternative rejected:* a player-chosen target skill. It costs a command-syntax extension plus a
webclient action-option surface plus preview plumbing — more than this change's budget, for a choice
the lore never asks the player to make.

*Consequence:* `docs/lore/skill-trees/divine-mystery.md` §7 item 2 currently says the conferred skill is
picked by the player. That sentence is amended in this change so the doc and the contract agree.

### D4: The scale is `EffectPolicy.coefficient` for that occurrence, and the validator must admit it

The field already means "this occurrence's magnitude", is already index-aligned, and is already the
dial every other magnitude-bearing effect reads.

**This does not work today and the change must fix it.** `SkillDef._validate_effect_policies()` in
`world/skills/registry.py` raises for any `coefficient != 1.0` unless the parsed effect is a
`DamageEffect`, a `HealEffect`, or a stat-basis `SelfHealEffect`. `ConferralEffect` and
`ConferGrowthRateEffect` are in neither list, so every conferral node — and every synthetic test
fixture built for this change — would raise at `SkillDef.__post_init__`, i.e. at registry import.
The two conferral effect classes are therefore added to that allow-list here, in the change that first
needs a non-identity coefficient on them.

Widening the allow-list *is* the codebase's mechanism for "this prefix supports a coefficient": the
same validator has explicit reject branches for the prefixes that must NOT carry one, and the
`skill-effect-model` spec already states the meaning per prefix (a transfer occurrence forbids it; a
`missing_fraction` self-heal forbids it). Conferral joins that table with its own meaning.

*Alternative rejected:* a dedicated `ConferralPolicy` sub-policy beside `DamagePolicy` and
`GaugeTransferPolicy`. Those exist because they carry several interacting fields that validate against
each other; a lone float would be duplicate vocabulary and a second place to look for one number.

### D5: An empty derived set rejects

If the caster owns nothing conferrable, the cast commits zero grants. Committing an action that does
nothing is exactly the silent no-op the shipped shape validation already refuses, so the empty set
raises `EFFECT_RESOLUTION_FAILED`. The lore reading is unchanged: a caster with nothing to lend cannot
perform the rite.

### D6: Preview parity is verified, not assumed

Removing the required keys should make `_skill_wide_failure` stop rejecting these prefixes for missing
context automatically, because the preview reads the same `_EFFECT_HANDLER_REQUIRED_CONTEXT` table.
The task list verifies that with a preview test rather than asserting it here; if the preview needs a
change, it is in scope.

## Risks / Trade-offs

- **A caster owning many conferrable passives writes many grants in one cast** → bounded by the
  caster's own owned set, deduped per `(source, skill)` by D1, and every write rides the existing
  `skill_grants` snapshot surface.
- **Replace-by-key silently weakens an existing target** if a source re-confers at a lower scale →
  intended: the grant must always describe the source's *current* intent, and the lore's ladder only
  ever raises the scale.
- **A source that loses ownership keeps old grants alive** → accepted. Ownership is checked when the
  grant is written, not continuously; a permanent grant is the priced behavior and revocation (next
  change) is the sanctioned removal path.
- **Conferral becomes reachable in combat, consuming a turn** → correct and intended; the skill is
  `usable_out_of_combat=True` and carries no cost, and the divine-mystery cadence brake governs how
  often it can advance progression.
- **`coefficient` now carries two meanings across prefixes (potency, conferral scale)** → accepted;
  the spec names the meaning per prefix, exactly as it already does for `gauge_transfer` and
  `self_heal:missing_fraction`.
- **Existing saved entities may already hold compounded grants** → not handled, and not a migration:
  the project has no released users (AGENTS.md), so the new semantics apply from first write.
