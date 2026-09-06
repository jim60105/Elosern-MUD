# Design: defeat-aftermath-core

Parent design: `docs/superpowers/specs/2026-09-06-defeat-aftermath-design.md`
(this change implements its §3.1 steps 1/4 and the defeat-line half of
step 6, §3.3 flag, §5, §6, plus the loader forward-compatibility seam the
adult layers need). Recovery arithmetic and the clock side-effect battery
moved to `defeat-aftermath-recovery` so this change lands inside one
working day. Source of truth remains the parent design document.

## Context

`settle_session()` (`world/rules/combat_session.py:1346`) settles the
round's clock for living survivors, writes the `settled_tick` marker, and
clears the session — all inside one `transaction.atomic()`. A 0-HP player
is excluded from settlement regen by design (kill semantics), so defeat
today leaves a 0-HP statue recoverable only through later clock-driven
regen with zero cost. Wilderness population monsters respawn on the next
coordinate activation unconditionally. The owner-approved parent design
replaces this with a consequential-but-continuable defeat.

## Goals / Non-Goals

**Goals:**

- Deterministic, offline, transaction-atomic defeat settlement: HP floor
  1 + knockout mark, violator departure with quest-retention precedence,
  weak-debuff mount, defeat EventLog kinds + zh-tw defeat lines, and the
  `DEFEAT_ADULT_SCENES` guard the adult layers hook.
- Zero-uncaused-write contract pinned by tests (clock causality excluded).
- A `defeat_aftermath.py` seam plus a rulebook loader that validates per
  section, so adult layers attach without touching this change again.

**Non-Goals:**

- No violation-sequence body, no sexual-state handling (adult changes); no
  Narrator prose beyond fixed template lines; no companion digest (digest
  change); no recovery clock arithmetic or regen scale
  (`defeat-aftermath-recovery` owns both).

## Decisions

**D-C1: HP floors at 1 plus knockout mark, not HP 0.**
Reuses the nonlethal floor precedent (companions, exams). `_terminal_outcome`
already detects `player_key in battlefield.knocked_out`, so defeat detection
is untouched; the aftermath treats "player is the knocked-out allied
member" as its trigger. The two never-revive regression tests are rewritten:
"the player settles at floor 1 and settlement applies no regen past it".
The 5% target arrives with `defeat-aftermath-recovery`; until then the
player wakes at 1 (playable — ordinary clock regen recovers from 1).
- Rejected alternative: revive via a special heal path — would need a new
  handler and violates the heal-effect-handler requirement.

**D-C2: The weak debuff is a shipped-surface marker buff; the regen tax is the recovery change's problem.**
`defeat_weak` rides the shipped effect surface (`bounds` ceilings on
atk_phys/agility/defense like `dark_curse`, duration in world seconds) and
is mounted here at settle time. The buff engine's `rate` modifier is an
absolute per-interval delta (`world/rules/buffs.py`), not a scale — scaling
regen through a buff would be a new effect kind, deliberately left to
`defeat-aftermath-recovery`, which owns the recovery math. This change
never scales regen.

**D-C3: Violator departure is defeat-writer-owned, not population-owned.**
`ensure_population` stays untouched. The aftermath despawns marker-carrying
(`db.population_key` present) living winners — pop from the wilderness
script's `itemcoordinates`, then `delete()`, the same primitive shape as
the population service's own despawn path (`world/maps/wilderness_population.py:121`).
Quest-bound monsters — pk in the settling player's persisted
`db.quest_log` records' `objective_target_ids` (`world/quests/runtime.py`
storage shape) — are never removed, and quest retention outranks the
population marker when one monster carries both. Foreign monsters stay
untouched. The "reconciliation never destroys an active-session
participant" invariant is preserved by ordering: departure runs inside the
same transaction after the terminal settlement, before the session record
is cleared.

**D-C4: `DEFEAT_ADULT_SCENES` is declared here as a pure guard.**
The settings flag (default `True`) exists in this change so the seam closes
atomically: the core wraps its violation hook point in
`if settings.DEFEAT_ADULT_SCENES:` and calls a registry entry that is a
no-op until an adult change registers a body. The core has no on-branch —
off-state is the shipped core behavior by construction, and the parent
design assigns the switch to core for exactly this reason.

**D-C5: The whole aftermath joins the existing atomic persistence unit.**
The delta extends `player-combat-session`'s atomic-unit requirement: the
aftermath (departure, buff grant, EventLog) runs inside the same
`transaction.atomic()` as `settled_tick` and the session clearing. The
state "marker durable, aftermath incomplete" is therefore unobservable; a
pre-commit crash rolls everything back and the existing recovery fallback
re-runs settlement once. This change rolls no dice, so its replay is
trivially identical; adult dice are state-derived (violation D-V4) and keep
the same property.
- Rejected alternative: a second transaction plus a "marker exists but
  aftermath missing" replay path — an impossible state under the shipped
  single-transaction writer, and dead test surface.

**D-C6: EventLog kinds are an open vocabulary addition, declared with their templates.**
`EventEntry.kind` is an open `str` (`world/rules/event_log.py`) — adding
`defeat_settle`, `violator_depart`, `weak_granted` needs no schema change,
but it is a vocabulary addition: this change authors each kind's zh-tw
offline template line and its observability/narrator registry entry. The
adult layers splice their violation kinds in-order later. Player-facing
defeat lines live in `player_messages.py` (zh-tw), replacing the bare
`"你被擊敗了。"` on the defeat path only. One `defeat_aftermath` info event
carries `{char, room, tick, hp_after}`.

**D-C7: The declared-write manifest lives in the test module and each downstream change extends it.**
The zero-uncaused-write battery pins a whitelist of record families
(affinity, wallet, inventory, quest progress, guild rank/merit, protected
bindings) and enumerates the clock's legitimate causal mutations inside
the settlement window (deadline failure, gauge daily decay/reset, merchant
restock, buff decay) as expected-in-window changes. Violation (act deltas +
counters + durations) and recovery (regen scale + advance) extend the
manifest in their own test additions and re-run the battery. The manifest
is code, not prose.

**D-C8: Rulebook loader is per-section and forward-compatible.**
`rulebook/defeat_aftermath.yaml` ships with only the core's sections
(`pg_lines`, `weak_debuff`). The loader validates sections it owns and
ignores unknown sections with one `log_warn`; each downstream change
registers its own section validator at load (the registry-extension
idiom). A malformed owned section fails closed at load like every other
rulebook; a foreign malformed section is that owner's problem. This keeps
one YAML file without any change needing to edit another's validation.

**D-C9: Archive order is explicit and rename-migration is in-archive work.**
This change archives first in the family; `defeat-aftermath-recovery`,
`defeat-aftermath-violation-sequence`,
`defeat-aftermath-companion-victims`, and
`defeat-aftermath-digest-narrative` follow in parent-design §8 order, each
writing deltas against the names this order produces. Every archive step
migrates the `covers_requirement` IDs of requirements it renames in the
same change.

## Risks / Trade-offs

- [Player wakes at HP 1 until the recovery change lands] → playable via
  ordinary rest/sleep regen; accepted intermediate state of the split.
- [A retained quest-bound winner blocks `skip_safety` rest in the room] →
  intended consequence: movement has no HP gate; the player moves and rests
  elsewhere. The recovery change's smoke test pins that exact route.
- [Despawned population winner leaves the room empty for a surviving
  companion] → intended; companions regen through ordinary clock progress.
- [Flee animation racing the terminal check at a defeat edge] → flee is
  itself a terminal outcome; the aftermath only runs on `outcome == "defeat"`.
