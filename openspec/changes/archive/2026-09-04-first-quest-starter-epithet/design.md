# Design: first-quest-starter-epithet

## Context

Authoritative semantics: `docs/superpowers/specs/2026-09-04-onboarding-removal-one-way-limbo-design.md` §6.

Current state (verified by reading the code):

- `world/lore/titles.py:120` — `STARTER_EPITHET = StarterEpithet("南門新客", "你在南門守衛的目送下踏入阿爾托利亞，成為公會的新面孔。")`.
- `world/rules/titles.py:657` — `grant_starter_pair(actor)` banks the F-rank
  fixed title (`grant_rank_title(actor, "F")` → `bank_fixed`) and the epithet
  (`bank_epithet(actor, STARTER_EPITHET.display, STARTER_EPITHET.origin_basis, tick)`),
  returning the notification lines 「獲得稱號：F級冒險者」/「獲得異名：南門新客」.
  `bank_epithet` dedupes on display and auto-equips an empty epithet slot.
- `world/rules/guild.py:227-231` — `register_adventurer` calls
  `grant_starter_pair` inside its `transaction.atomic()` and returns the lines
  in `parsed["title_notifications"]`; `commands/guild.py:150` and
  `web/webclient/actions/service_actions.py:279` echo those lines on the
  registration surfaces.
- `world/rules/guild.py:312-475` — `turn_in_quest` claim flow: reads
  `claims = parse_reward_claims(actor)` (:359), rejects an already-claimed ID,
  snapshots `("wallet", "inventory", "quest_log", "guild_reward_claims")`
  (:391-394), then in one `transaction.atomic()` the `writer()` appends
  `quest_id` to `actor.db.guild_reward_claims` (:432), applies copper/merit/
  inventory/ACQUIRE/cap-breaks/affinity; on exception `restore()` puts every
  snapshot back. The result dict (:469-475) carries
  `"onboarding_completed"`, echoed by `commands/guild.py:329`,
  `commands/talk.py:157`, `web/webclient/actions/service_actions.py:347` —
  the onboarding hook at :441-446 that the sibling change deletes.

## Goals / Non-Goals

**Goals:**

- Registration grants the F-rank fixed title only.
- The first-ever guild reward claim grants 「南門新客」 inside the claim
  transaction, with rollback parity and dedupe idempotence.
- Clean cutover: `grant_starter_pair` deleted, no aliases, no migrations.

**Non-Goals:**

- The title machinery itself (`bank_epithet`/`bank_fixed`, dedupe, equip slots,
  removal gate) — untouched, per design doc §10.
- The `set_onboarded` hook and welcome line (sibling `remove-onboarding-tutorial`).
- `introductory_hunt` quest data (survives unchanged; the grant is NOT keyed
  to it).

## Decisions

**D1 — Trigger: first-ever claim, defined inside the transaction.**
`turn_in_quest` captures `first_claim = not claims` where `claims` is the
parsed list read at :359 *before* `writer()` appends the new ID. The grant
fires when `first_claim` is true. Not `definition_key`-specific: the epithet
narrates "you turned in your first quest", any quest — keying it to
`introductory_hunt` would resurrect onboarding-flavored special-casing the
design doc explicitly retires (the quest survives only as ordinary data).
Checking the *pre-append emptiness* (rather than post-append length) reuses
the already-parsed list — zero extra reads — and makes the trigger
independent of the JSON list's stored order.

**D2 — New writer `grant_first_quest_epithet(actor)` in `world/rules/titles.py`.**
Same module as its predecessor, same regular-writer discipline: it calls
`bank_epithet(actor, STARTER_EPITHET.display, STARTER_EPITHET.origin_basis, get_world_clock().tick)`
and returns `(f"獲得異名：{STARTER_EPITHET.display}",)` when `bank_epithet`
returns `True`, `()` on the dedupe no-op. It does NOT grant the rank title —
`grant_rank_title(actor, "F")` stays called by `register_adventurer` in place
of `grant_starter_pair`. `bank_epithet`'s display dedupe is the designed
second guard: even if the trigger somehow re-fired (relog, replayed claim,
future code paths), the second call is a silent no-op.

**D3 — Grant lands inside the claim transaction; rollback removes it.**
`writer()` calls `grant_first_quest_epithet(actor)` when `first_claim`,
collecting lines into a `title_notifications` local. Because
`bank_epithet` writes `db.title_collection`/`db.title_equipped`, those two
attribute keys join the existing `snapshot_attributes(...)` tuple and the
`restore()` loop so a failed claim restores title state alongside
wallet/inventory/quest log/claims (matching the existing restore-every-surface
pattern); the `transaction.atomic()` rollback covers the DB rows. The result
dict gains `"title_notifications": list(...)` — replacing the key the
registration payload already uses, so both claim surfaces already have an
echo idiom to reuse.

**D4 — Notification routing.** `commands/guild.py::CmdGuildTurnIn`,
`commands/talk.py::_turn_in_quest`, and `web/webclient/actions/service_actions.py`
each echo the `title_notifications` lines after their existing success line
(same loop idiom as their registration handlers). 「獲得異名：南門新客」 thus
appears on both CLI turn-in surfaces and the webclient claim action. When the
sibling change's `onboarding_completed` branch is removed, the notification
loop is the only extra echo on the claim path.

**D5 — Flavor rewrite (`world/lore/titles.py`).** New
`origin_basis` (exact text, player-facing zh-tw prose, no 守衛/目送):

> 「你在公會完成第一次任務回報，成為阿爾托利亞冒險者中的新面孔。」

`StarterEpithet`'s class docstring ("The deterministic onboarding epithet")
is reworded to the first-turn-in framing; the constant name `STARTER_EPITHET`
and display 「南門新客」 stay (registry requirement block truthfully still
names them).

**D6 — `grant_starter_pair` retirement.** Deleted, not deprecated. The 10 test
modules importing it (grep-verified: `test_titles.py`, `test_title_view.py`,
`commands/tests/test_title_command.py`, `typeclasses/tests/test_appearance.py`,
`test_npc_dialogue.py`, `server/conf/tests/test_title_nomination_service.py`,
`web/webclient/actions/tests/test_title_actions.py`,
`web/webclient/presentation/tests/test_character_panel.py`,
`test_title_codex_panel.py`) migrate per-site: fixture helpers that wanted
"player has both titles" call `grant_rank_title(actor, "F")` +
`grant_first_quest_epithet(actor)`; tests specifically exercising
`bank_epithet` dedupe keep calling `bank_epithet` directly.

**D7 — Delta shape.** MODIFIED copies of the two `title-system` blocks and the
one `guild-registration` block (from `/tmp/epithet-blocks.md`, grant-timing
wording only); ADDED requirement under `quest-reward-settlement` instead of
MODIFY-ing the exactly-once / atomic-payout blocks — their text remains true
without mentioning the epithet, and the ADDED block carries its own atomicity
and rollback scenarios. Registry block untouched (reads confirmed: it names
only the constant + display, both surviving).

**Sibling ordering.** This change edits the same `turn_in_quest` writer
closure where `remove-onboarding-tutorial` deletes the `set_onboarded` hook
(:441-446), and the collision is WIDER than that closure — four jointly-owned
files, verified: `world/rules/guild.py` (claim transaction + result dict),
`commands/talk.py` (echo at :157-160), `web/webclient/actions/service_actions.py`
(echo at :347-349), and `commands/guild.py` (the `CmdGuildTurnIn` claim-response
echo at :325-332, whose `onboarding_completed` welcome at :329-332 the sibling
deletes at exactly the position where this change appends the
`title_notifications` loop). **`remove-onboarding-tutorial` lands FIRST and this
change rebases onto the post-removal result shape**: `turn_in_quest`'s dict no
longer carries `onboarding_completed`, no echo site still has the welcome
branch, and implementing against that shape means the notification loop is the
ONLY claim-path echo line diff in all four files. The `talk`/CLI/webclient echo
edits likewise assume the `onboarding_completed` branch is gone.

## Risks / Trade-offs

- [Two changes edit `turn_in_quest` concurrently] → declared ordering in
  proposal Impact; if parallel, one owner lands both hunks in the transaction
  closure.
- [Existing dev databases hold 「南門新客」 granted at registration] → zero
  migrations policy: dev DBs are reset, no cleanup shim (design doc §3).
- [Tests that assumed registration→full composed title 「F級冒險者　南門新客」
  now see only 「F級冒險者」 until a claim] → expected behavioral delta;
  affected assertions updated in the test sweep, first-claim tests assert the
  composed title instead.
- [Rollback fidelity: title attributes written outside the snapshot list] →
  mitigated by D3: both `title_collection`/`title_equipped` join
  snapshot/restore; rollback-revoke is a dedicated scenario/test.
- [Grant fires for the very first claim even if it is a re-run of an older
  quest] → intended: trigger is first-ever claim by definition; `bank_epithet`
  dedupe makes any duplicate inert.
