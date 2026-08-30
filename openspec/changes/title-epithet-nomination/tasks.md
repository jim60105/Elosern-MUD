# Tasks: title-epithet-nomination

## 1. Ballot attribute + cooldown

- [x] 1.1 `db.pending_title_ballot` attribute (+ snapshot-surface registration
  in `world/rules/action.py` and `world/rules/cast_settlement.py` next to
  `title_collection`) and the bounded decline log
  `db.title_nomination_declines` (`[{tick, displays}]`, newest first, cap 3 —
  the decline timestamp is the only cooldown source, ballots never expire, and
  the log doubles as the Director soft-learning feed);
  `NOMINATION_COOLDOWN_DAYS = 2` in `world/lore/titles.py`.
- [x] 1.2 Rest-point triggers call the composition-root service
  `server/title_nomination_service.schedule_epithet_nomination(entity)`
  (the transport contract forbids rules/commands importing `world/ai`):
  logout (`PlayerCharacter.at_post_unpuppet`), the resting day boundary
  (typed `rest`/`sleep`/`wait` and the WebClient `explore.wait` adapter,
  gated on the `daily_reset` advance event), exam PASS (observer inside
  `settle_exam_outcome`), quest-arc completion (observer on the quest
  runtime's COMPLETED transition; both settlement observers defer via
  `transaction.on_commit`). Suppression: pending ballot ⇒ silent return;
  active cooldown ⇒ silent return.

## 2. Generative proposal stage (world/ai/, proposal-only)

- [x] 2.1 Prompt: Director, recent EventLog summary + bounded declined-epithet
  digest (soft learning context only), exactly 5 `{display, basis}` (basis
  ≤ 80 chars, zh-tw, 2–8 chars, noun phrase, no player name); collision rules
  NOT in prompt text. New `prompts/title_nomination.yaml` + `PROMPT_SPECS`
  keys; `title_nomination` added to `world/ai/profiles.LAYER_NAMES` with a
  bounded default profile.
- [x] 2.2 Closed output schema in `world/ai/schemas` (registered via the
  layer's `register_title_nomination()` startup seam):
  `{candidates: [{display ≤ 64, basis ≤ 80}] exactly 5}`; malformed JSON,
  wrong count, or overlong basis ⇒ whole round voids.
- [x] 2.3 Deterministic filters in fixed order: form (2–8 code points, every
  char CJK, no whitespace, no player-name substring) → fixed-registry display →
  live own-collection → in-batch dup (keep first); take first 3 survivors;
  1–3 ballot as-is; 0 void silently.
- [x] 2.4 Fire-and-forget scheduling through the service (mirrors
  `option_proposal_service`: function-local `world.ai` imports, never raises,
  never blocks); disabled/offline profile ⇒ the stage does not fire at all.
  The module returns the filtered candidates and writes NO attribute; §3.3's
  rules-layer writer persists the ballot.

## 3. Rules-layer writers

- [x] 3.1 `world/rules/titles.py::accept_epithet(entity, index)`: index check →
  bank (display, origin_quote=basis, granted_tick) → auto-equip if empty →
  clear ballot, one atomic transaction; out-of-range / no-ballot ⇒ stable
  `TitleBallotReason`.
- [x] 3.2 Decline path `decline_epithet_ballot(entity)`: discard + decline-log
  record (starts the cooldown) + `title_epithet_declined` EventLog entry naming
  the declined displays, returned for the answering surface to render.
- [x] 3.3 Rules-layer nomination writer (`world/rules/titles.py::
  persist_nomination_ballot`, beside `accept_epithet`): re-checks suppression
  after the proposal returns, then persists it into `db.pending_title_ballot`
  in one all-or-nothing step (a failed persist voids the round, leaving no
  partial proposal).

## 4. Surfaces

- [x] 4.1 WebClient: `title_ballot` panel (exact-shape presenter + validator +
  JS protocol mirrors + Vue ballot menu with 「接受 1／2／3」 + 「放棄」 via
  `title.accept`/`title.decline` UI actions), re-rendered from
  `db.pending_title_ballot` on sync and pushed through the epoch-guarded
  `publish_panel_update` when the service persists a new ballot.
- [x] 4.2 Telnet `title accept <1|2|3>` / `title decline` subcommands (bare
  `title accept` lists the ballot); docs trio updated in this change (the F
  entry's syntax list extends).

## 5. Tests (mocked client only)

- [x] 5.1 Pure tests in `world/ai/tests/test_title_nomination.py` (new module —
  already owned by the `world.ai` package shard label; no explicit entry):
  pipeline matrix (5 good, 4/6 malformed, bad JSON, basis 80 ok/81 voids,
  form rejects, fixed-registry collision, own-collection collision,
  deleted-name passes, in-batch dup, 3/2/1/0 survivor cuts); disabled profile
  ⇒ no transport. Service tests in `server/conf/tests/
  test_title_nomination_service.py` (owned by the `server` package label):
  fire-and-forget never raises; suppression short-circuit; cooldown arithmetic
  (accept vs decline, boundary + multi-day jump); on_commit gating;
  panel push.
- [x] 5.2 Integration tests EXTENDING F's `world/rules/tests/test_titles.py`
  and `commands/tests/test_title_command.py` (no new modules, no shard change):
  single pending ballot; triggers suppressed; cross-session accept equals
  in-session; accept atomicity (forced failure restores); decline EventLog
  content + decline-log persistence; trigger firing at each rest point (typed
  and Web rest routes, logout, exam PASS, quest completion incl. rolled-back
  outer transaction) and never mid-combat; rules-layer persist all-or-nothing
  (failed persist leaves nothing); observer wrappers never alter quest/exam
  settlement (raising observer isolated).

## Verification

- [x] V1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.ai world.rules commands web.webclient server.conf.tests.test_title_nomination_service`
- [x] V2 `uv run --locked python -m tools.spec_traceability check` (0 errors)
- [x] V3 `uv run --locked python -m compileall -q world typeclasses commands server`
- [x] V4 `openspec validate title-epithet-nomination --strict`
- [x] V5 `git diff --check`
- [x] V6 JS gates: `node --test web/static/webclient/js/tests/*.test.js`,
  `npm test`

## Post-sync traceability (during archive/sync)

- [ ] P1 On sync, annotate the new `title-system` requirement IDs on the §5.1/
  §5.2 tests (delta-only IDs cannot be annotated before sync — the checker
  parses `openspec/specs` only); re-check the `game-command-docs` title entry
  ID (same ID after F's sync, now covering the extended syntax).
