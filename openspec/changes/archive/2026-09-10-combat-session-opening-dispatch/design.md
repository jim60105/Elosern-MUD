## Context

The approved brainstorming design for this work is
`docs/superpowers/specs/2026-09-10-field-combat-initiation-design.md`; this
change implements its §5 `combat_session.py` table and D-4.

Current state:

- `_submit_request()` is the shared body behind both `submit_player_action()`
  and `submit_player_item_use()`. Inside one `transaction.atomic()` it picks
  either `resolve_overwhelm()` (when `overwhelming == player_team`) or one
  `run_round()`, then scans friendly fire and sexual coercion, updates the
  session record, and calls `_continue_or_settle()`.
- `_overwhelm_provider()` already implements "the commanded request for the
  player's first turn, deterministic `basic_attack` afterwards";
  `_round_provider()` implements the single-round equivalent.
- `engage()` validates a `PlayerCharacter`, a single living hostile `Monster`
  in the same room, and no active session; collects `combat_companions()`;
  builds a `CombatSessionRecord` with `enemy_ids=(one dbref,)`; reconstructs
  the battlefield; `_persist()`s; registers skip safety; clears any dialogue
  session; and returns the record plus an informational
  `classify_overwhelm()` value.
- The ordinary-round branch alone emits the `combat_round_settled` boundary
  event via `transaction.on_commit`; the compression branch deliberately does
  not, because it is not one ordinary round.
- `world/rules/combat_session.py` is 1697 lines. This change must not grow it
  with exploration-side routing; that belongs to `field-combat-initiation`'s
  own module.

## Goals / Non-Goals

**Goals:**

- Make one submission mean one round, structurally — not by convention.
- Reduce compression to one explicit, narrow entry point that a caller must
  ask for by name.
- Add the multi-enemy engagement and first-strike plumbing the field entry
  needs, without changing either existing `engage()` call site.

**Non-Goals:**

- Any exploration-side routing, target classification, reject reason, command
  change, or transaction wrapper around session creation. All of that is
  `field-combat-initiation`.
- Any change to `classify_overwhelm()`, `resolve_overwhelm()`,
  `run_round()`, or `commanded_damage_reaches_enemy()` — this change consumes
  them.
- Any change to `settle_session()`, `_continue_or_settle()`, the friendly-fire
  or coercion scans, or the defeat aftermath.
- Any change to the informational `overwhelming_team` value returned by
  `engage()` and `_continue_or_settle()`. It is a pure query and stays.

## Decisions

**D-1. The default parameter value carries the invariant.** `opening` defaults
to `"round"`, so every existing and future caller that does not opt in gets an
ordinary round. The alternative — keeping the branch and adding a condition to
it — was rejected because it leaves compression on the default path, one
careless edit away from firing again. Making the exception opt-in means a
reviewer sees `opening="overwhelm"` at the call site or knows it cannot happen.

**D-2. `submit_opening_action()` owns the two-part dispatch condition, not
`_submit_request()`.** `_submit_request()` is told what to do; it does not
decide. Keeping the verdict-plus-damage judgement in one named public function
means there is exactly one place to read to know when compression happens, and
`_submit_request()` stays a mechanism rather than a policy.

Alternative rejected: computing the condition inside `_submit_request()` behind
an `allow_overwhelm: bool` flag. It reads almost the same but scatters the
policy — the caller would pass permission while the body applied judgement, so
neither location would answer "when does compression happen" on its own.

**D-3. First strike is unconditional for the opening action.** Both branches
pass `first_actor=<player key>`, not just the compression branch. The player
chose to start the fight from outside it; that is the privilege, and it should
not depend on which branch the verdict selects. For the compression branch it
also keeps round one's ordering consistent with the ordinary branch, so the two
paths differ only in how many rounds they run.

**D-4. `engage_group()` is a new function and `engage()` delegates.** Widening
`engage()`'s own signature (a sequence parameter, or `*targets`, or an
`additional_targets` keyword) would touch both existing call sites and make the
single-target case read worse. A named group form plus a one-line delegation
keeps `engage(actor, target)` byte-identical for its callers and gives the
field entry a first-class multi-enemy path. Every validation, companion
collection, persistence, skip-safety registration, and dialogue-clearing step
moves into `engage_group()` and is reused unchanged.

**D-5. Item use loses compression outright rather than gaining a gate.** A
consumable's effect is not an attack, so `commanded_damage_reaches_enemy()`
would answer `False` for every item anyway; adding the plumbing to ask would be
dead code. `submit_player_item_use()` therefore simply stops asking about
overwhelm. The consequence — `resolve_overwhelm(commanded_action_kind="item")`
becomes unreachable in production — is accepted rather than removed: it is a
log-marking argument, fully tested, and part of the archived
`event-log-compression` capability, so deleting it would churn an archived spec
for no behavioural gain.

**D-6. The boundary event stays on the ordinary-round path only.** Unchanged
from today, and now expressible as "emitted when `opening == "round"`", which
is what the existing comment already means.

**D-7. The seam ships without a caller.** `submit_opening_action()` has no
production consumer until `field-combat-initiation` lands. `AGENTS.md`
sanctions a forward-declared seam with guarded tests over a fake
implementation, and its own tests drive it directly.

## Risks / Trade-offs

- **[Player-visible regression: an overwhelming matchup entered through
  `explore.engage` now takes many commands instead of one.]** → Intended, and
  the reason `field-combat-initiation` exists together with
  `skill-field-availability`'s `basic_attack` flag: a player who wants the
  one-shot opens the fight from exploration instead. Until that lands, clearing
  a trivial monster is genuinely more tedious. The sequence should land
  completely before the branch is considered done.
- **[Removing the branch could silently drop the policy forwarding
  (`simulated`, `nonlethal_keys`, `journal_sink`, `notifications_sink`) that
  the compression call site currently performs.]** → `submit_opening_action()`
  routes through the same `_submit_request()` body, so the forwarding lives in
  one place and is asserted for both `opening` values.
- **[`_submit_request()` gaining two parameters invites future callers to pass
  `opening="overwhelm"` from the ordinary flow.]** → `_submit_request()` is
  private; `submit_opening_action()` is the only sanctioned way in, and a test
  asserts the ordinary public entries never pass `opening`.
- **[Four archived requirements are reworded at once, risking lost detail.]**
  → Each is copied verbatim and edited in place, and the provider semantics,
  the log-marker contract, and the atomicity contract are preserved word for
  word except where they name the dispatcher.
- **[`engage_group()` widens what a session's `enemy_ids` may contain, and
  downstream code may assume one enemy.]** → `enemy_ids` is already a tuple and
  `reconstruct_battlefield()` already builds teams from it; the risk is in
  presenters and `_primary_opponent_id()`. A test opens a two-enemy session and
  asserts reconstruction, persistence, round resolution, and settlement all
  behave, so any single-enemy assumption surfaces here rather than in the field
  entry.
