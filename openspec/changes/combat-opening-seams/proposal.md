## Why

Overwhelm resolution currently fires from inside the ordinary combat loop
(`world/rules/combat_session.py:1163`), gated only on the power verdict. It
therefore settles a whole encounter by attack power no matter what the player
actually did — a self-buff, a heal, a disguise, or a consumable all trigger it —
and no matter who was targeted, because the dispatch never inspects the
request's targets. Meanwhile the exploration side has no way to open a fight
with the skill the player chose, because nothing can force one combatant to act
first in a round.

Fixing either problem needs two primitives the engine does not have: a
first-actor override for one round, and a pure query answering "will this
commanded action damage an enemy". This change adds exactly those two seams and
nothing else, so the behavioural rewiring in
`combat-session-opening-dispatch` and `field-combat-initiation` lands against
primitives that are already specified and tested on their own.

## What Changes

- `world/rules/combat.py`'s `run_round()` gains a keyword-only
  `first_actor: str | None = None`. `roll_initiative()` still rolls exactly as
  today; the named key is then moved to the head of the resulting sequence with
  every other position's relative order unchanged. Passing `None` — every
  existing call site — is byte-identical to current behaviour.
- `world/rules/overwhelm.py`'s `resolve_overwhelm()` gains the same
  keyword-only `first_actor`, forwarded to **round one only**
  (`_resolve_overwhelm_raw`'s `rounds == 0`); every later round uses ordinary
  initiative. It changes turn order alone, never damage, verdicts, round
  counts, or reported time.
- New pure query
  `world/rules/overwhelm.py::commanded_damage_reaches_enemy(battlefield,
  actor_key, skill_key, target_keys) -> bool`: true when the skill definition's
  parsed `effects` carry a `DamageEffect` **and** at least one of the supplied
  concrete target keys sits on the team opposing `actor_key`. Rolls no dice,
  writes nothing, and is recomputable at any time, matching
  `classify_overwhelm()`'s existing purity discipline.
- No existing call site changes. No player-observable behaviour changes.

Not backward compatibility: this is a forward-declared seam. The project has no
released users, so the additive signatures exist to be consumed by the two
follow-up changes rather than to preserve any old caller.

## Capabilities

### New Capabilities

None. This change adds requirements to three existing capabilities.

### Modified Capabilities

- `combat-resolution`: adds the `run_round(first_actor=...)` reorder-only
  override contract — it must reorder the rolled sequence, never re-roll it,
  never grant an extra action, and never skip a combatant.
- `single-shot-resolution`: adds `resolve_overwhelm(first_actor=...)` applying
  to round one only, with an explicit requirement that it cannot influence
  damage, verdicts, `rounds_elapsed`, or `total_seconds`.
- `overwhelm-threshold`: adds `commanded_damage_reaches_enemy()` as a pure
  query — the static `DamageEffect` read, the enemy-team target condition, and
  the exclusion of indirect HP movement such as `SexualDrainEffect`.

## Impact

- `world/rules/combat.py` — `run_round()` signature and the initiative
  reordering step.
- `world/rules/overwhelm.py` — `resolve_overwhelm()` /
  `_resolve_overwhelm_raw()` signatures and the new pure query.
- `world/rules/tests/` — first-actor ordering coverage, round-one-only
  forwarding coverage, and the predicate's truth table.
- `.github/evennia-shards.json` — only if a new test module is added; extending
  existing modules avoids touching it.
- Unaffected: every current caller of `run_round()` and `resolve_overwhelm()`,
  the session facade, the command surface, the webclient, and the skill
  registry.
