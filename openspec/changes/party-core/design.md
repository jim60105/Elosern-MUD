# party-core Design

## Context

`affinity-system` provided the sole-writer affinity API and installed the party auto-leave recheck
hook as a verified no-op; `affinity-ai` taught the dialogue layer to inject the NPC's affinity
context (value, cap, stage) and to guard the numbers from player-facing speech. Nothing yet turns
relationships into companionship. This change lands the party's core: membership binding, the
`invite` / `leave` commands, the AI-judged invitation with the offline threshold fallback, and the
wired auto-leave rule. Constraints: single-writer invariant (`world/rules/party.py` is the only
membership writer; `world/ai/` never writes), offline playability (no AI → fixed threshold),
command-docs contract, and all-or-nothing two-entity writes (player + NPC).

## Goals / Non-Goals

**Goals**

- Bounded, persistent, atomic membership (≤ 4 companions) with one owning module.
- `invite`/`leave` commands (text + webclient action) with deterministic preflight and feedback.
- AI judgment via the existing guarded dialogue seam and the new `party_invite` intent; fixed
  threshold (70) as the offline fallback; the AI never bound by it.
- Auto-leave rule wired into the affinity negative-delta path.

**Non-Goals**

- Movement follow (`party-follow`), joint combat (`party-combat`), quest assistance and the +2
  completion bonus (`party-quest`), decrease events, cap breaks.

## Decisions

### D-1: Membership is mirrored storage owned by one module

`player.db.party = [npc_dbid, ...]` (player-owned list) and `npc.db.party_member = player_dbid`
(NPC-owned backref) are written only by `join_party` / `leave_party` in `world/rules/party.py`,
inside one `transaction.atomic()` with snapshot/restore of both attributes (the `npc_intents`
two-entity idiom). Mirroring gives companions an O(1) local "am I bound?" read for follow/combat
hooks without scanning players, at the cost of a dual write that the owning module keeps atomic
and idempotent.

### D-2: The invitation uses a structured dialogue outcome; the threshold applies only on degrade

The invite flow cannot reuse `at_talked_to` blindly: it resolves to `None` both when the AI
declines-with-intent-kept and when the layer degrades, so "didn't join" must not be read as
"offline". The seam gains a structured exchange helper, `run_npc_exchange(speech, character,
client)` in `typeclasses/npcs.py`, returning a frozen `DialogueExchangeResult(degraded: bool,
reply: NPCDialogueReply | None)` that performs the memory append and thinking timer but applies
nothing. `at_talked_to` becomes a thin composition of the helper plus intent application (its
observable behavior is unchanged), and the `invite` adapter uses the helper directly: on
`degraded=True` it applies the fixed threshold; otherwise it shows the speech and routes the
reply's intent through `apply_npc_intent`. The client comes from the existing composition root
(`build_dialogue_client()`), which returns an offline stub when the profile is disabled — the
stub is never called because the layer degrades first, so the invite falls back to the threshold.
One injection site, no new transport plumbing, and the AI's decline is never overridden by the
threshold.

### D-3: The decision is the reply's; the threshold is the fallback only

When the dialogue layer resolves, the `party_invite` intent is the sole decision; the threshold is
never consulted. When the layer degrades, the threshold (`affinity >= 70`) decides with
deterministic accept/reject lines. This preserves the owner's "AI 可以自由判斷" requirement and
the "AI 不可用時以固定值判斷" fallback.

### D-4: `party_invite` is a whitelisted dialogue intent, not a new layer

The whitelist grows from seven to eight kinds; the schema bounds `accept` as a boolean, a
per-kind validator enforces the exact single-field shape, and `apply_npc_intent` re-verifies and
delegates to `join_party` — the AI cannot create a binding it could not perform. Illegal intents
keep the speech (the §7.4 failure mode). Because `affinity-ai` will archive first, the
`party-core` delta for the two shared requirements carries the merged text (whitelist and applier
blocks include the `adjust_relation` additions) so sequential archival loses nothing.

### D-5: Auto-leave is wired at the writer, not at decrease events

`affinity-system` already runs `run_auto_leave_recheck` after every negative delta; `party-core`
replaces the no-op body with the membership check (bound companion and affinity below 70 →
`leave_party(..., "affinity_below_threshold")`). The auto-leave SHALL be part of the affinity
write's transaction: if the leave fails, the whole negative-delta operation rolls back, so
"affinity below threshold but still bound" is unreachable. The player notification SHALL be sent
only after the outer transaction commits. Decrease events are future callers of the same
negative-delta path; no new trigger is invented here.

### D-6: NPC deletion purges its party bindings

Instance reclamation and scene teardown delete NPCs directly (`entity.delete()`), which would
leave stale dbids in `player.db.party` and permanently consume companion slots. `world/rules/party.py`
SHALL own `purge_npc_memberships(npc)`, invoked from the `NPC` typeclass's deletion hook
(`at_object_delete`), removing the NPC from any player's party list and clearing its
`party_member` in one transaction. A stale dbid found by any other party API SHALL be treated as
an absent companion (never a crash).

## Risks / Trade-offs

- [Mirrored storage drifts if a write bypasses the module] → `party.py` is the only writer; a
  contract test asserts no other module assigns `db.party` / `db.party_member` (mirroring the
  map-knowledge ownership contract pattern).
- [NPC deletion orphans the binding] → `purge_npc_memberships` runs from the typeclass deletion
  hook; stale dbids degrade to "absent companion" everywhere (D-6).
- [The text client has no AI client of its own] → `invite` uses the existing composition root;
  the offline stub degrades to the threshold path by construction (D-2).
- [AI decline could be misread as offline] → the structured `DialogueExchangeResult` makes the
  degraded terminal explicit; the threshold applies only to it (D-2).
- [A mid-decision race fills the party after the AI accepted] → `join_party`'s rejection reason
  is surfaced to the player as a fixed Traditional Chinese message by both adapters; the AI
  speech is still shown.
- [Sequential archival could drop `affinity-ai`'s text] → the shared-requirement deltas carry the
  merged content (D-4); both changes declare their dependency order.
- [An AI echo of the invite message could leak affinity numbers] → `affinity-ai`'s no-leak
  validator already covers every dialogue reply, including invites.
- [Auto-leave failure leaves an invalid state] → the leave joins the affinity write's
  transaction; notification fires post-commit (D-5).
- [The invite call adds latency when the AI is up] → one guarded call per invitation, the same
  budget as a talk; the threshold path is instant when offline.

## Migration Plan

No released users; no data migration. `db.party` / `db.party_member` are new attributes created
on first write; no existing state is reinterpreted. Rollback is a revert; an NPC with a stale
`party_member` after a partial failure is repaired by the module's idempotent `leave_party`.

## Open Questions

- None blocking. The exact phrasing of the deterministic accept/reject lines and the
  party-joined/refused notifications is authored at apply time in Traditional Chinese.
