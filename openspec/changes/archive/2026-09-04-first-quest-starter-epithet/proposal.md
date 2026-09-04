# Proposal: first-quest-starter-epithet

## Why

The 「南門新客」 starter epithet is currently granted at guild registration
inside `grant_starter_pair` (`world/rules/titles.py:657`, called from
`register_adventurer` at `world/rules/guild.py:227`). Per the approved
onboarding-removal design
(`docs/superpowers/specs/2026-09-04-onboarding-removal-one-way-limbo-design.md` §6),
registration-time granting is a residue of onboarding semantics: the epithet
should describe the player's *first completed quest turn-in*, not the act of
registering. Its current `origin_basis` flavor also references the 南門守衛
seeing the player into the city — an NPC the sibling change deletes.

## What Changes

- **BREAKING** Guild registration no longer grants the starter epithet; it
  grants only the F-rank fixed title (「F級冒險者」) via `grant_rank_title(actor, "F")`,
  which stays called at registration.
- **BREAKING** `grant_starter_pair` is retired (no alias, no shim, zero
  migrations). Test fixtures across 10 modules that call it are migrated to
  `grant_rank_title` / `grant_first_quest_epithet` / `bank_epithet`.
- NEW `grant_first_quest_epithet(actor)` in `world/rules/titles.py` — a
  regular `bank_epithet` writer — called INSIDE the guild reward-claim
  transaction (`turn_in_quest`, `world/rules/guild.py`). Trigger: the actor's
  `guild_reward_claims` list is empty *before* this claim is appended (the
  first-ever reward claim, any quest definition — not quest-key-specific).
  `bank_epithet` display dedupe is the second guard against double grants.
- The grant notification line 「獲得異名：南門新客」 merges into the claim
  response payload (`title_notifications`) and is echoed by every claim
  surface (CLI `guild turnin`, the `talk 回報` keyword path, the webclient
  claim action). A rolled-back claim removes the epithet (same transaction,
  plus title-attribute snapshot/restore alongside the existing surfaces).
- `STARTER_EPITHET` display 「南門新客」 is KEPT; `origin_basis` is rewritten
  to a guard-free first-turn-in narrative (exact new text in design.md).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `title-system`: two requirement blocks change —
  "Guild registration and rank promotion grant paired titles atomically"
  (registration grants the rank fixed title only; epithet grant moves to the
  first reward claim) and "Slot non-empty is an invariant with auto-equip and
  no unequip" (mutator list wording 「starter pair」 → 「first-quest epithet
  grant」; the epithet slot's empty-window now ends at the first claim, not at
  registration). The registry requirement block is NOT modified: it names the
  `STARTER_EPITHET` constant and its display, both of which survive unchanged;
  it does not name the grant purpose, so no truthful rewording is forced.
- `guild-registration`: "Guild registration grants the paired starter titles
  atomically" — the registration transaction grants the F-rank fixed title
  only; the epithet leaves this capability's scope.
- `quest-reward-settlement`: one ADDED requirement covering the first-claim
  epithet grant inside the claim transaction (with rollback and dedupe
  scenarios). The existing "claimed exactly once per quest ID" and
  "atomic payout transaction" blocks are NOT modified — their text does not
  need to mention the epithet, and the new behavior is cleanly expressed as an
  added requirement (deliberately chosen to avoid delta churn; the atomicity
  of the epithet write is covered normatively by the ADDED requirement's own
  rollback scenario).

## Impact

- Code: `world/lore/titles.py` (`STARTER_EPITHET.origin_basis` + docstring),
  `world/rules/titles.py` (retire `grant_starter_pair`, add
  `grant_first_quest_epithet`), `world/rules/guild.py`
  (`register_adventurer` title call; `turn_in_quest` claim transaction:
  first-claim detection, in-transaction grant, title-attribute
  snapshot/restore, `title_notifications` in the result payload).
- Claim-surface echoes: `commands/guild.py` (`CmdGuildTurnIn`),
  `commands/talk.py` (`_turn_in_quest`), `web/webclient/actions/service_actions.py`
  (guild claim adapter). No new modules → `.github/evennia-shards.json`
  unchanged.
- Tests: `world/rules/tests/test_titles.py`, `test_title_view.py`,
  `world/rules/tests/test_guild_registration.py`, `test_guild_rewards.py`,
  plus the mechanical `grant_starter_pair` fixture sweep in
  `commands/tests/test_title_command.py`, `typeclasses/tests/test_appearance.py`,
  `test_npc_dialogue.py`, `server/conf/tests/test_title_nomination_service.py`,
  `web/webclient/actions/tests/test_title_actions.py`,
  `web/webclient/presentation/tests/test_character_panel.py`,
  `test_title_codex_panel.py`.
- **Sibling dependency**: `remove-onboarding-tutorial` deletes the
  `set_onboarded` hook at `world/rules/guild.py:441-446` inside the *same*
  `turn_in_quest` writer closure this change edits, and this change surfaces
  title notifications through the same claim-response echo sites the sibling
  strips its `onboarding_completed` welcome from — the jointly-owned files are
  therefore FOUR, verified: `world/rules/guild.py` (the `turn_in_quest` claim
  transaction: sibling deletes the `set_onboarded`/`onboarding_completed` hook
  at :441-446 and the result-dict key at :474; this change adds first-claim
  detection, the in-transaction grant, snapshot/restore keys, and the
  `title_notifications` result key in the same closure),
  `commands/talk.py` (the `onboarding_completed` echo at :157-160 the sibling
  deletes; this change's `title_notifications` echo occupies the same
  post-success-line position in `_turn_in_quest`),
  `web/webclient/actions/service_actions.py` (the `onboarding_completed` echo
  at :347-349 the sibling deletes; this change appends the notification lines
  at the same seam), and `commands/guild.py` (the `CmdGuildTurnIn` claim
  response echo at :325-332 — the sibling deletes its `onboarding_completed`
  welcome branch at :329-332; this change adds the `title_notifications` echo
  at the same position — a file this proposal's echo list already names, now
  declared as a collision site too). **Ordering: `remove-onboarding-tutorial`
  lands FIRST; this change rebases onto the post-removal result shape** —
  `turn_in_quest`'s result dict no longer carries `onboarding_completed`, none
  of the three echo sites still has the welcome branch, and the
  `title_notifications` key is the only new echo. Alternative (parallel
  landing) requires the single owner of the claim path to apply both changes'
  hunks together in all four files.
