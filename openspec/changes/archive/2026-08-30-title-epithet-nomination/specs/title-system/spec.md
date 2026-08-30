## ADDED Requirements

### Requirement: Epithet nomination fires only at rest points and is throttled
The nomination trigger (the composition-root
`server.title_nomination_service.schedule_epithet_nomination(entity)`; the
transport contract forbids `world/rules` and `commands` from importing
`world/ai`, so scheduling lives in the service and persisting in the rules
writer) SHALL fire only at the four narrative rest points — logout, a
world-clock day boundary while the entity is resting, an examination
pass, and a quest-arc completion — and never during combat settlement. While a
`db.pending_title_ballot` exists, every trigger SHALL return silently (one ballot
at a time; no replacement path). A declined ballot SHALL suppress
renomination for `NOMINATION_COOLDOWN_DAYS` (title-registry constant, initial
value 2) world-clock day boundaries — decline is the only cooldown source,
because ballots never expire; an accepted ballot SHALL NOT start a
cooldown. With the LLM offline, degraded, or past its bounded timeout, the stage
SHALL not fire and fixed titles SHALL be unaffected.

#### Scenario: A pending ballot suppresses every trigger
- **WHEN** any rest-point trigger fires for an entity with a pending ballot
- **THEN** no LLM call is made and the ballot is unchanged

#### Scenario: Decline cools down two day boundaries
- **WHEN** a ballot is declined and day boundaries pass
- **THEN** nominations resume only after the second boundary

#### Scenario: Offline LLM mints nothing
- **WHEN** a trigger fires while the options profile is degraded or absent
- **THEN** the round is void, no ballot is stored, and gameplay is unaffected

### Requirement: The nomination pipeline is 5 candidates through schema and collision filters
The generative stage SHALL ask the Director for exactly five `{display, basis}`
candidates from the recent EventLog summary and SHALL validate them through, in
this order: (1) the closed output schema `{candidates: [{display: str, basis: str}]
x 5}` — malformed JSON, wrong count, or overlong fields void the whole round;
(2) deterministic per-candidate filters, first survivor wins: zh-tw form (2–8
characters, no whitespace, no player-name substring), rejection on equality with
any `FixedTitleDef.display_name_zh`, rejection on equality with any epithet in
the entity's live collection, and in-batch duplicates keeping the first. The
first three survivors form the ballot; one to three survivors ballot as-is; zero
survivors void the round silently. Collision rules SHALL NOT appear in the prompt
text. The generative module SHALL be pure proposal — it returns the filtered
candidates (or nothing) and writes no attribute anywhere; persisting a ballot is
performed solely by the rules-layer nomination writer, which re-checks
suppression after the proposal returns.

#### Scenario: Malformed schema voids the round
- **WHEN** the model returns four candidates, six candidates, or unparseable JSON
- **THEN** no ballot is stored

#### Scenario: A nameless survivor survives deletion history
- **WHEN** a candidate equals an epithet previously deleted from the collection
- **THEN** the live-collection filter passes it (deleted names are renominable)

#### Scenario: Batch duplicates keep the first
- **WHEN** two candidates carry the same display
- **THEN** only the first is kept for the top-three cut

#### Scenario: The generative module persists nothing
- **WHEN** the proposer completes a round with survivors
- **THEN** no attribute outside the rules-layer writer's transaction changed during the proposal

### Requirement: The ballot persists unchanged until consent
The surviving candidates SHALL persist to `db.pending_title_ballot` as
`[{display, basis}]`, surviving logout/relogin and never expiring. The WebClient
SHALL present the OOB ballot menu (title card plus basis quote, buttons 「接受
1／2／3」 and 「放棄」); Telnet SHALL present the same list through the `title`
command family. A player answer arriving after relogin SHALL behave identically to
an answer given in-session.

#### Scenario: A cross-session answer behaves the same
- **WHEN** a player logs out with a pending ballot, returns, and accepts candidate 2
- **THEN** adoption proceeds exactly as an in-session accept

### Requirement: Ballot persistence, acceptance, and decline are rules-layer writers only
The rules layer SHALL own every ballot write: the nomination writer persists a
validated proposal into `db.pending_title_ballot` in its own all-or-nothing step
(a failed persist voids the round, leaving no partial proposal), and
`world/rules/titles.py` SHALL expose `accept_epithet(entity, index)` validating
`index` against the pending ballot, then within one atomic snapshot-registered
transaction: bank the epithet (display, `origin_quote = basis`, `granted_tick`),
auto-equip the epithet slot when empty (F's D8 discipline), and clear the ballot;
a repeated or out-of-range accept SHALL reject with a stable reason and change
nothing. A decline SHALL discard the batch, start the cooldown, record the
declined displays into a bounded per-entity decline log, and emit a
`title_epithet_declined` EventLog entry through the answering surface; the
nomination prompt SHALL digest that decline log as soft-learning context so the
Director's future summaries see what the player rejected, and no programmatic
blacklist SHALL exist anywhere (the decline log is prompt context only, never a
filter rule). No code path outside these three rules-layer writers SHALL change
title state from a ballot.

#### Scenario: Accept banks and auto-equips atomically
- **WHEN** a player accepts candidate 1 while the epithet slot is occupied
- **THEN** the entry banks without touching the slot, and a forced mid-transaction failure restores both attributes

#### Scenario: Decline records for the Director
- **WHEN** a player declines a ballot
- **THEN** a `title_epithet_declined` EventLog entry lists the declined
  displays, no collection entry is created, and the decline log persists them
  so the next nomination prompt digest carries what the player rejected
