# Design: companion-possession-rules

Ratified: R1 design D1/D2/D5/D6/D8 + §3 state machine (minus the puppet mechanics, which the
transition change threads through the same seams). Local implementation choices only.

## Context

`world/rules/party.py` is the writer template: mirrored attributes, `_write_binding`'s
snapshot/restore inside `transaction.atomic()`, `restore_membership_surfaces` for the
idmapper-cache-after-rollback problem, stable reason constants. `commands/leave.py` (key
`leave`, alias 解散, `help_category = "General"`) shows the localized command shape. Combat gate
precedent: the party-adjustment boundary already refuses mid-combat adjustment. Dialogue gate:
`clear_dialogue_session` marks the dialogue-session surface. Quest credit reads
`party_member`-style owner binding in the quest observer — untouched by design (ratified).

## Goals / Non-Goals

**Goals:** the complete deterministic contract of possession with zero puppeting — state,
gates, release ordering, command surface, clock predicate, silence triggers. The next change
plugs puppet transfer into `enter_possession`'s documented order without changing its contract.

**Non-Goals:** `puppet_object`/lock work (transition change), cmdset mount (transition change),
affordances/Vue (webclient change), combat/dialoge/shop entry while possessed beyond the refusal
messages the gates define.

## Decisions

- **`possession.py` mirrors party.py shape exactly:** `PossessionError` base,
  `PossessionGateError(reason)` (stable codes `not_bound`, `not_co_located`, `in_combat`,
  `dialogue_open`, `already_possessing`), `PossessionWriteError(reason, detail)`; module-private
  `_write_possession` with snapshot/restore + `restore_possession_surfaces` (same idmapper
  discipline, named in the docstring as the second single-writer module).
- **Order seam (documented in module docstring, consumed by the transition change):** gates →
  mirror write → [puppet transfer hook] → [cmdset mount hook] → boundary `log_info` event.
  Release reverses: [unpuppet hook] → [cmdset remove hook] → mirror clear → event. This change
  implements the non-puppet steps and leaves the two hook calls as named no-op call sites
  (`_transfer_puppet`, `_mount_cmdset`) raising nothing — documented seams (AGENTS.md: seam >
  fake), each carrying an `# possession: seam R1-transition` comment the transition change
  replaces.
- **Predicate module:** `world/rules/player_control.py` is tiny on purpose (one function +
  docstring naming D4 of the clock design); `charge_movement` and the room-entry trigger import
  it — never re-implement the OR. Puppetedness for the NPC leg is `npc.sessions.count()` (the
  account puppet is what makes possession real); PC leg keeps the existing
  puppeted-PlayerCharacter check.
- **Gate details:** `in_combat` = `is_in_active_session` on either side (the same helper the
  party-adjustment boundary uses); `dialogue_open` = the NPC's dialogue-session surface;
  `already_possessing` covers both the same npc (idempotence refusal) and a different npc (one
  account, one possession — resolved by scanning the account's own characters' `db.possession`,
  bounded by the account cap).
- **`leave` refusal is a gate on the command surface** (`REASON_HANDBACK_FIRST` fixed line) and
  inside `leave_party` itself (defense-in-depth: any API caller dismisses only after release) —
  the auto-leave hook calls `possession.release_for_party_change(npc, player)` FIRST, before the
  affinity atomic block, and `purge_npc_memberships` does the same unconditionally.
- **`release_for_party_change` is the FULL release (handback seam + attributes), not an
  attribute-only clear:** a DB transaction cannot make puppet/session side effects atomic, so
  ordering is release-then-commit: the handback seam runs first (a documented no-op in this
  change — no session ever puppets B until the transition change lands — and the real
  unpuppet-B/re-puppet-A ladder from the transition change onward); a seam failure aborts before
  the affinity atomic opens, so "affinity below threshold but still possessed" is unreachable.
  If the attribute commit itself later fails, the bounded recovery state is "A puppeted,
  possession still recorded": 歸位 or the next auto-leave retry converges (every leg idempotent).
  The transition change's tests pin both the seam-failure abort and the commit-failure retry.
- **`release_on_disconnect(account)`:** account-keyed helper scanning the account's characters
  for `db.possession` and running the full release per hit, idempotent. Its caller lands with
  the transition change on **`Account.at_post_disconnect`** — verified against Evennia 6.1,
  `at_post_unpuppet` fires on EVERY deliberate unpuppet (`Account.unpuppet_object` calls
  `obj.at_post_unpuppet`, `evennia/accounts/accounts.py:577`), including possession's own
  release of A, so wiring cleanup there would clear fresh mirrors mid-possession;
  `at_post_disconnect` fires only from `ServerSession.disconnect()`
  (`evennia/server/serversession.py:171`), never on puppet swaps or reload.

## Risks / Trade-offs

- [State records without puppeting looks like a half-feature] → the three changes are one
  delivery line; the text 附身 command lands HERE with real gates, and the transition change
  lands within days. The command's refusal set already prevents the confusing combos.
- [Double release (auto-leave + disconnect race)] → release is idempotent (no possession → no-op
  success), like `purge_npc_memberships`.
