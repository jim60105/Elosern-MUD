## Why

`_submit_request()` (`world/rules/combat_session.py:1163`) decides between one
ordinary round and a whole compressed encounter by asking
`classify_overwhelm(battlefield) == player_team` — and nothing else. It never
looks at what the player submitted or at whom.

So a self-buff, a heal, a disguise, a movement skill, or a healing potion all
collapse the fight by attack power, because `resolve_overwhelm()` runs the
commanded action for the player's first turn and then the default enemy policy
for every turn after it. A player who cast a buff against a weak monster
watches the monster die and never chose that. Once inside a session, any
submission can silently stop being the round the player asked for.

The fix is not a better condition at that branch — it is to take the branch out
of the ordinary flow entirely, and make compression something a caller must
explicitly ask for. This change makes "one submission is one round" the
default, and adds the narrow seam through which `field-combat-initiation` will
ask for the exception.

## What Changes

- `_submit_request()` loses its `classify_overwhelm()` branch and gains two
  keyword-only parameters: `opening: Literal["round", "overwhelm"] = "round"`
  and `first_actor: str | None = None`. The plain round is now the **default**,
  so "the ordinary flow has no compression" is the program's default behaviour
  rather than a convention held in place by a comment.
- `submit_player_action()` and `submit_player_item_use()` stop calling
  `classify_overwhelm()` and never pass `opening`. Every submission inside an
  existing session runs exactly one round, whatever the verdict.
  **BREAKING** for player-visible behaviour: an overwhelming matchup no longer
  resolves in one command; the player fights it round by round unless they
  opened the fight through the field entry.
- **BREAKING**: a consumable item can no longer trigger compression under any
  circumstance. The field entry accepts skills only.
- New `engage_group(actor, targets)` opens one session against several
  co-located hostile targets, pulling in companions exactly as `engage()`
  does. `engage(actor, target)` keeps its signature and semantics and delegates
  to it, so both existing call sites (`commands/combat.py:48` and the
  webclient's `_engage_adapter`) are untouched.
- New `submit_opening_action(actor, skill_key, targets, scale)` — the sole
  dispatcher of compression. It chooses `opening="overwhelm"` only when
  `classify_overwhelm()` returns the player's team **and**
  `commanded_damage_reaches_enemy()` says the submitted skill damages an enemy;
  otherwise `opening="round"`. Either way it passes `first_actor=<player key>`,
  so the opening action resolves before any enemy acts.
- The ordinary round's `combat_round_settled` boundary event stays bound to the
  `opening="round"` path, as it is today, because compression is not one
  ordinary round.

No backward compatibility and no migration: the project has no released users,
and no persisted session field encodes the old dispatch.

## Capabilities

### New Capabilities

None. This change modifies requirements in two existing capabilities and adds
requirements to one of them.

### Modified Capabilities

- `player-combat-session`: adds the ordinary-round default, `engage_group()`,
  and `submit_opening_action()` as the sole compression dispatcher granting
  first strike; modifies the four requirements that currently describe
  compression as something the ordinary submission path performs — "Overwhelm
  waits for one player choice before compressed resolver-backed outcome",
  "Overwhelm compression is player-direction only", "A round and its
  settlement form one atomic persistence unit", and "Player combat submission
  accepts one explicit target value".
- `single-shot-resolution`: modifies "The session never dispatches compression
  for the foe-overwhelming direction" so the sole production call site is named
  as the opening-action seam, and so the damage precondition is part of the
  dispatch contract rather than the verdict alone.

## Impact

- `world/rules/combat_session.py` — `_submit_request()`, `submit_player_action()`,
  `submit_player_item_use()`, `engage()`, plus the new `engage_group()` and
  `submit_opening_action()`.
- `world/rules/tests/test_combat_session_flow.py` and the overwhelm resolution
  tests — the equivalence and dispatch contracts move to the new seam, and the
  ordinary path gains an assertion that it never compresses.
- Depends on `combat-opening-seams` for `run_round(first_actor=...)`,
  `resolve_overwhelm(first_actor=...)`, and
  `commanded_damage_reaches_enemy()`.
- Unaffected: `world/rules/overwhelm.py` (consumed, not edited),
  `world/rules/combat.py`, the command surface, the webclient, the skill
  registry, and `settle_session()`'s own logic.
- `resolve_overwhelm(commanded_action_kind="item")` becomes unreachable from
  production. It is a log-marking argument belonging to the archived
  `event-log-compression` capability and stays as-is; only `"skill"` is passed.
- After this change `submit_opening_action()` has no production caller until
  `field-combat-initiation` lands — a deliberate forward-declared seam.
