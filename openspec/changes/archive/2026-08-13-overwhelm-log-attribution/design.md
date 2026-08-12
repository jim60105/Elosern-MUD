## Context

The player-combat session resolves a player-overwhelming encounter by running the player's single
preflight-valid action as their first turn and then deterministic `basic_attack` requests (lowest-HP
living enemy) for their subsequent turns inside a bounded `run_round()` loop
(`_overwhelm_provider`, `world/rules/combat_session.py`). `resolve_overwhelm()` then compresses the
raw per-round `EventLog`s: `compress_event_logs()` drops every `"roll"` entry whose
`data["hit"]` is truthy, keeps miss rolls and `"damage"` entries, and prepends one
`overwhelm_resolution` summary entry. This drop was designed as noise reduction ("the successful
outcome is duplicated by a paired damage entry"), but it breaks per-attack attribution in the
player-facing log: the damage entry survives while its attack line disappears, so in
`cast 基本攻擊=瑟芮雅` the reader sees the commanded self-attack's miss roll followed by a damage
entry against a different target with no visible attack line in between, and cannot tell the
commanded action from the compression's auto basic attacks.

Constraints that shape the design:

- Self-targeting a damage skill is legal by design (`FactionConstraint.ANY` accepts every relation);
  this change must not alter targeting or validation.
- `world/rules/event_log.py` dataclasses are frozen and must not change (existing spec invariant).
- The narrator consumes entry kinds as opaque strings; `world/ai/` has no kind allowlist.
- The webclient OOB channel never carries prose; all rendering paths go through
  `render_plain_text()`.
- The project has no released users; internal log-shape contract changes are acceptable without
  migration layers.

## Goals / Non-Goals

**Goals:**

- Every attack in a compressed overwhelm log keeps its visible roll line, so damage is always
  attributable to the attack that produced it — matching the game's ordinary per-round
  presentation.
- The player's commanded action is identifiable in the compressed log, distinct from the
  compression's auto basic attacks.
- Zero impact on combat math, resolution equivalence, auto-attack policy, summary aggregation,
  friendly-fire scanning, or the single-writer boundary.
- Keep the summary entry (`rounds` / `hits` / `total_damage`) exactly as it is.

**Non-Goals:**

- No change to self-targeting legality or any targeting/faction validation.
- No change to non-compressed (ordinary round) logs.
- No round-boundary markers or per-round headers in compressed logs.
- No change to the narrator prompt schema or the webclient OOB protocol.
- No change to the summary entry's content or semantics.

## Decisions

### D1: Preserve every `"roll"` entry instead of dropping successful ones

`compress_event_logs()` no longer filters by entry kind. Every `EventEntry` of every non-empty input
`EventLog` is preserved in original order (via `dataclasses.replace()` on the parent log, never a
live mutation); empty logs are still dropped as hygiene. The summary entry is prepended as before,
and its `hits` / `total_damage` are still computed from the preserved `"damage"` entries, so the
summary is bit-identical to today's for the same encounter.

Rationale: the roll line is the only visual anchor pairing a damage entry with its attack. In an
ordinary round, a hit always renders as `roll` + `damage`; compression silently dropped half of that
pair, which is precisely the readability failure reported. Restoring the pair makes compressed logs
consistent with the game's own ordinary presentation and dissolves the "wrong-target" illusion
without inventing new syntax.

Alternatives considered:

- **Keep dropping rolls, mark only the commanded action.** Rejected: the auto-attack damage against
  the goblin would still float with no attack line, so the log would still read as "my self-attack
  somehow damaged the goblin".
- **Drop rolls only for auto attacks, keep them for the commanded action.** Rejected: inconsistent
  presentation and requires identifying auto attacks (the harder direction) anyway.

### D2: Mark the commanded action with a prepended `commanded_action` entry

The compression receives the commanded action's actor key and skill key, and matches them only
within the encounter's round-1 log window (see D3). One `commanded_action`-kind entry is prepended
to the matching `EventLog`'s `entries`, rendered as:

```
你施展了「{data[skill]}」。
```

with `data["skill"]` set to the registry display label, resolved via `SKILL_REGISTRY.get(key)`
falling back to the raw key when unknown (read-only lookup; `world/rules/combat.py` already imports
`world.skills.registry`). `actor` is the player's key, `target` is `None`, `time_cost_seconds` of
the parent log is untouched. The rendered result places the marker immediately before the commanded
action's own roll/damage lines, so the reader sees exactly one "your choice" anchor and understands
that everything else in the compressed block is the deterministic auto resolution.

Rationale: this directly answers "which line is my command" — the other half of the reported
readability failure — with a single, cheap entry. Second person (`你施展了…`) is chosen because the
game is single-player (the only reader is the player) and the distinction from the third-person
auto-attack lines must be unmistakable. A third-person line (`瑟芮雅 施展了「基本攻擊」。`) would be
indistinguishable in form from the auto lines it is meant to contrast.

Alternatives considered:

- **Mark the auto attacks instead.** Rejected: multiple markers per encounter, and "auto" cannot be
  identified without the same actor/skill matching plus distinguishing companions' legitimate
  actions — more machinery for a worse reading experience.
- **Emit the marker as a separate facade-level announcement outside compression.** Rejected: splits
  the compressed-log shaping contract across two modules and loses the guarantee that unit-level
  compression tests cover it.
- **Rephrase the commanded action's existing roll template.** Rejected: requires per-entry template
  surgery on records owned by the action pipeline, not by compression.

### D3: Plumb the commanded identity through optional keyword arguments, matched within round 1 only

`resolve_overwhelm(battlefield, action_provider, max_rounds=12, commanded_actor=None,
commanded_skill=None)` forwards both, plus the encounter's **round-1 log slice** (`commanded_window`),
to `compress_event_logs(...)`. The facade's player-overwhelming branch passes `str(actor.key)` and
the submitted `skill_key`. Direct callers that pass nothing (the quest-planning integration, rule
tests) get exactly today's behavior minus the roll filtering.

Matching rule: the marker is looked up **only within `commanded_window`** — the `EventLog`s the first
`combat.run_round()` call returned — and applies to the **first** log in that window whose `actor`
and `skill_key` both match. This is both necessary and sufficient: the commanded request is always
used on the player's first turn, which is in round 1 (the player is living at submission), while
their auto basic attacks begin in round 2. Because round 2+ logs are outside the window, an
in-round invalidation of the commanded action (it produced no `EventLog` in round 1) can never
mislabel a later auto basic attack as commanded — the window simply contains no match and no marker
is emitted, even when the player commanded `basic_attack` itself. When `commanded_window` is omitted
or empty, no marker is applied.

Alternatives considered:

- **Match the first log with both fields across all rounds.** Rejected: if the commanded
  `basic_attack` was invalidated in round 1, the first matching log would be a round-2 auto basic
  attack, wrongly labeled as the player's command.
- **Match on actor only.** Rejected: weaker than actor+skill matching for the same invalidation case.
- **Ask the provider to tag its own request's log.** Rejected: the provider interface is a bare
  `Callable[[Any, Battlefield], ActionRequest | None]`; tagging would require threading state
  through every policy, a larger API change for a cosmetic marker.

### D4: Keep the summary aggregation unchanged

`rounds`, `hits`, and `total_damage` derive from `rounds_elapsed` and the preserved `"damage"`
entries; restoring roll lines does not change either input, so the summary sentence stays
byte-identical for the same encounter. The summary remains the tl;dr, and the restored roll lines
are the detail — the design-doc intent that compression "never skips damage or outcome entries"
extends to attack records.

### D5: Marker edge cases

- **Commanded action invalidated in round 1** → the round-1 window contains no matching log → no
  marker (graceful), including when the player commanded `basic_attack` itself.
- **Player commands `basic_attack`** → the commanded log is the first (and only possible) match
  inside the round-1 window; later auto basic attacks are outside the window and never match.
- **AREA skills** → marker shows only the skill label; the target list is already visible in the
  subsequent per-target entries.
- **Companions on the party team** → their logs carry their own actor keys and never match the
  player's key.
- **Unknown `commanded_skill` key** → the label lookup falls back to the raw key (`SKILL_REGISTRY`
  read via `.get()`), so pure presentation can never raise for a direct caller.
- **Empty input logs** → still dropped (pre-existing hygiene behavior, kept).

## Risks / Trade-offs

- **Compressed logs grow:** a long compression (up to 12 rounds, up to 16 participants per
  `combat_view.MAX_PARTICIPANTS`) now shows every roll line and can exceed the narrator's
  `MAX_ENTRIES`/`MAX_LOGS` prompt bounds. → Mitigation: the summary entry stays the aggregate tl;dr;
  the growth is exactly what an ordinary round-by-round play-through of the same encounter would
  show. Battle results are not currently narrated at all (no production call site of
  `narrate_event_logs`; combat rendering is deterministic `render_plain_text`), so the narrator
  bounds are a latent risk, not a present behavior change; a sanity test asserts that a
  maximum-size compressed log degrades gracefully to the deterministic renderer, which is already
  the game's offline behavior.
- **Tests and spec fixtures assert roll absence.** → Deliberate, in-scope: `test_overwhelm_compression.py`
  and the `event-log-compression` delta spec are rewritten; the removed main requirement is
  re-created as a preservation requirement and traceability annotations are updated before the
  `spec_traceability check` gate.
- **Marker misattribution in the invalidated-`basic_attack` corner case.** → Eliminated by the
  round-1 window: round-2 auto attacks can never match, so a round-1-invalidated command simply
  yields no marker. A regression test covers exactly this case.
- **Second-person prose inside a deterministic record.** → The game is single-player; the only
  renderer is `render_plain_text()`; the narrator treats `kind` as an opaque string. No other
  consumer exists today or is foreseen.
- **`_scan_friendly_fire` / quest planners depend on compressed logs.** → They scan `"damage"`
  entries and kill/defeat entries, which are preserved byte-for-byte; the friendly-fire overwhelm
  test keeps passing unchanged.

## Migration Plan

No released users, so no data migration or compatibility layer. Rollback is a revert of the two
modules and the test file. The archive workflow syncs the three delta specs into main specs and
updates the removed requirement's traceability annotations in the same change.

## Open Questions

None.
