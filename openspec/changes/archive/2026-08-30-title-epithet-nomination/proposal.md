# Proposal: title-epithet-nomination

## Why

`title-fixed-core` shipped the two-kind title storage with deterministic
grants; the epithet kind still has no acquisition path. Design
`docs/superpowers/specs/2026-08-30-title-system-design.md` §7 (D4) defines it:
at narrative rest points the Director proposes five candidate epithets from the
recent EventLog, a deterministic pipeline (closed schema → collision filters →
first three survivors) turns them into a persisted ballot, and only the player's
explicit consent (`title accept`) writes state — through the rules layer, keeping
the single-writer boundary intact and the deterministic-offline invariant whole
(the whole stage silently no-ops when the LLM is offline).

## What Changes

- The nomination trigger (composition-root
  `server/title_nomination_service.schedule_epithet_nomination(entity)` — the
  transport contract forbids rules/commands importing `world/ai`) fires only at
  narrative rest points: logout, a world-clock day boundary while resting,
  exam pass, quest-arc completion — never mid-combat. At most one pending
  ballot per entity; a decline starts a `NOMINATION_COOLDOWN_DAYS`
  (registry constant, 2) day-boundary cooldown
  (decline is the only cooldown source — ballots never expire); an accepted
  ballot does not.
- Proposal pipeline in `world/ai/` (proposal-only, writes nothing): Director
  prompt over the recent EventLog summary asks for exactly 5
  `{display, basis}` candidates; closed output schema (wrong count / malformed
  JSON / overlong fields void the round); deterministic collision filters in
  fixed order (form 2–8 chars, no player-name substring, no whitespace; reject
  on any fixed-title display; reject on the entity's own collection; in-batch
  duplicates keep the first); first three survivors form the ballot. Zero
  survivors voids the round silently.
- Ballot persists to `db.pending_title_ballot` (`[{display, basis}]`), survives
  logout, never expires; while pending, every trigger is suppressed. WebClient
  shows the OOB menu (title card + basis, 「接受 1／2／3」 + 「放棄」); Telnet gets
  `title accept <1|2|3>` / `title decline`.
- Rules-layer-only writes: the nomination writer persists the validated
  proposal into `db.pending_title_ballot` (all-or-nothing; a failed persist
  voids the round); consent writes via `accept_epithet(entity,
  index)` banks the entry (display, origin_quote = basis, granted_tick) and
  auto-equips an empty epithet slot in one atomic transaction; decline records
  the rejected displays into a bounded per-entity decline log and emits a
  `title_epithet_declined` EventLog entry through the answering surface (soft
  learning for the Director — the nomination prompt digests the decline log;
  no programmatic blacklist exists). Deleted-then-renominated names are legal
  again because collision filtering reads the live collection.

## Capabilities

### New Capabilities

(None — lands as added requirements of `title-system`.)

### Modified Capabilities

- `title-system`: nomination triggers/throttle, proposal pipeline, persisted
  ballot, consent-gated adoption.
- `game-command-docs`: `title accept` / `title decline` syntax coverage.

### Removed Capabilities

(None.)

## Impact

- Code: `world/ai/` nomination module (prompt + schema + filters — pure
  proposal, zero attribute writes), `world/rules/titles.py` (ballot persist,
  `accept_epithet`, decline EventLog), trigger
  hooks (logout, clock day-boundary stage, exam settlement, quest completion),
  `db.pending_title_ballot` attribute + snapshot registration, WebClient OOB
  ballot menu, Telnet `title` subcommands.
- Tests: nomination pipeline pure tests (mocked LLM client — never a live
  call), trigger/cooldown integration tests; new modules registered in
  `.github/evennia-shards.json` in this change.
- No backward-compatibility or migration work: the project is unreleased with
  zero users.
