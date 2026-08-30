# Tasks: title-epithet-nomination

## 1. Ballot attribute + cooldown

- [ ] 1.1 `db.pending_title_ballot` attribute (+ snapshot-surface registration);
  cooldown bookkeeping (decline timestamp in ticks — decline is the only
  cooldown source, ballots never expire) as a plain derived
  field; `NOMINATION_COOLDOWN_DAYS = 2` in `world/lore/titles.py`.
- [ ] 1.2 Trigger hooks calling `maybe_nominate(entity)`: logout, clock
  day-boundary-while-resting, exam PASS settlement, quest-arc completion.
  Suppression: pending ballot ⇒ silent return; active cooldown ⇒ silent return.

## 2. Generative proposal stage (world/ai/, proposal-only)

- [ ] 2.1 Prompt: Director, recent EventLog summary, exactly 5 `{display,
  basis}` (basis ≤ 80 chars, zh-tw, 2–8 chars, noun phrase, no player name);
  collision rules NOT in prompt text.
- [ ] 2.2 Closed output schema in `world/ai/schemas`:
  `{candidates: [{display, basis}] x 5}`; malformed/overlong ⇒ whole round voids.
- [ ] 2.3 Deterministic filters in fixed order: form → fixed-registry display →
  live own-collection → in-batch dup (keep first); take first 3 survivors;
  1–3 ballot as-is; 0 void silently.
- [ ] 2.4 Synchronous bounded-timeout call via the existing options-service
  pattern; offline/degraded ⇒ stage does not fire. The module returns the
  filtered candidates and writes NO attribute; §3.3's rules-layer writer
  persists the ballot.

## 3. Rules-layer writers
- [ ] 3.1 `world/rules/titles.py::accept_epithet(entity, index)`: index check →
  bank (display, origin_quote=basis, granted_tick) → auto-equip if empty →
  clear ballot, one atomic transaction; out-of-range ⇒ stable reason.
- [ ] 3.2 Decline path: discard + cooldown start + EventLog entry naming
  declined displays.

- [ ] 3.3 Rules-layer nomination writer (in `world/rules/titles.py` beside
  `accept_epithet`): re-checks suppression after the proposal returns, then
  persists it into `db.pending_title_ballot` in one all-or-nothing step (a
  failed persist voids the round, leaving no partial proposal).

## 4. Surfaces

- [ ] 4.1 WebClient: OOB ballot menu (card + basis, 「接受 1／2／3」 + 「放棄」),
  re-rendered from `db.pending_title_ballot` on sync.
- [ ] 4.2 Telnet `title accept <1|2|3>` / `title decline` subcommands; docs trio
  updated in this change (the F entry's syntax list extends).

## 5. Tests (mocked client only)

- [ ] 5.1 Pure tests in `world/ai/tests/test_title_nomination.py` (new module —
  register in `.github/evennia-shards.json`, same change): pipeline matrix
  (5 good, 4/6 malformed, bad JSON, form rejects,
  fixed-registry collision, own-collection collision, deleted-name passes,
  in-batch dup, 3/2/1/0 survivor cuts); cooldown arithmetic (accept vs decline).
- [ ] 5.2 Integration tests EXTENDING F's `world/rules/tests/test_titles.py`
  and `commands/tests/test_title_command.py` (no new modules, no shard change):
  single pending ballot; triggers suppressed; cross-session
  accept equals in-session; accept atomicity (forced failure restores); decline
  EventLog content; trigger firing at each rest point (and never mid-combat);
  rules-layer persist all-or-nothing (failed persist leaves nothing).

## Verification

- [ ] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai world.rules commands web.webclient`
- [ ] V2 `uv run --locked python -m tools.spec_traceability check` (0 errors)
- [ ] V3 `uv run --locked python -m compileall -q world typeclasses commands server`
- [ ] V4 `openspec validate title-epithet-nomination --strict`
- [ ] V5 `git diff --check`

## Post-sync traceability (during archive/sync)

- [ ] P1 On sync, annotate the new `title-system` requirement IDs on the §5.1/
  §5.2 tests; re-check the `game-command-docs` title entry ID (same ID after F's
  sync, now covering the extended syntax).
