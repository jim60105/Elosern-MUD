# Dialogue Panel Protocol and Publication Budgets

This document records the version-3 `dialogue` presentation panel wire format,
canonical UTF-8 JSON publication budgets, and the conditional envelope allowance
governing dialogue delivery over the Elosern Out-of-Band (OOB) protocol.

## Publication Budgets

### Contextual service authoring and opening

Static and generated dialogue may declare optional `services`, an array of exact
`{key, topic_id, label}` rows. Keys match `[a-z][a-z0-9_]{0,54}`; labels contain
1..64 Unicode code points. Keys and topic references are unique. References must
resolve within the same source and generated phase. Informational topics cannot
be advertised as services. Static support is the deterministic guild report
topic; generated support requires an authorized `offer_commission` topic effect.
Invalid associations reject the entire source candidate before publication.

A generated service role declares person-bound `scripted_dialogue` with both
`dialogue_key` and `service_id` equal to `scene_role:<package_id>:<role_id>`,
alongside its declared `quest_issuer`. Compilation supplies these trusted
identities before shared capability assembly. Narrative-only roles remain
unbound. Native plus associated entries must fit the 16-entry host limit in
every phase; overflow rejects before publication or assembly.

Exploration schema 5 adds independent per-target `services: {state, entries}`.
The state is `none`, `ready` or `unreadable`. Entries carry exact
`{key, label, enabled, disabled_reason, route}` and always name the selected
positive NPC identity. The bounded route union is
`{kind: "services", npc_id, section: "shop|registration|board|report|rank"}`,
`{kind: "dialogue", npc_id, topic_id}` or
`{kind: "command", npc_id, command: "church join"}`.
Services open the correlated `services.open` provider read; dialogue opens that
host and locally focuses the still-disclosed topic without selecting it.
Opening creates no quest effect or reading receipt. Explicit later activation
revalidates current source, phase, binding and control authority. Enrollment
only prefills `church join #<npc_id>` in the existing command input.
The player submits it separately. Coarse guild/shop navigation is removed;
ordinary editor navigation stays independent.

Dialogue delivery enforces finite canonical UTF-8 JSON publication budgets across
both backend selection and frontend transport:

| Scope | Budget | Enforcement Point | Description |
| --- | ---: | --- | --- |
| Scene | 8,192 bytes | `world.lore.scenes::Scene`, `world.rules.dialogue::select_authored_topic` | Maximum canonical UTF-8 wire size of an individual scene (lines, speakers, and revisions). |
| Delivery Bundle | 16,384 bytes | `world.lore.dialogue.codec::validate_dialogue`, `select_authored_topic` | Selected delivery scene plus all reachable `pure_chain` public successor scenes. |
| Dialogue Panel | 24,576 bytes | `protocol.py::check_envelope`, `validate_dialogue`, UMD `core.js::checkEnvelope`, UMD `misc.js::validateDialoguePanel` | Maximum canonical UTF-8 wire size of the complete version-3 dialogue panel. |
| Generic Envelope | 65,536 bytes | `protocol.py::check_envelope`, UMD `core.js::checkEnvelope` | Global size ceiling for generic OOB messages and dialogue-removed envelopes. |
| Dialogue Envelope | 98,304 bytes | `protocol.py::check_envelope`, UMD `core.js::checkEnvelope`, UMD `store.js` | Conditional ceiling for snapshots and updates carrying an available version-3 dialogue panel. |

## Conditional Dialogue Envelope Allowance

Ordinary envelopes retain the 65,536-byte limit. A snapshot or update carrying an
available version-3 dialogue panel (`schema_version: 3`, `available: true`, `kind: "dialogue"`)
may use up to 98,304 canonical UTF-8 bytes only when:

1. The complete envelope canonical JSON is at most 98,304 bytes.
2. The dialogue panel payload is at most 24,576 bytes.
3. The same envelope with the `dialogue` panel removed passes the generic 65,536-byte limit.

This allowance reserves publication capacity for multilingual attributed dialogue scenes
and pure chain successors without relaxing size bounds on sibling panels. If any bound is
exceeded, the frame is rejected without truncation.

## Pre-Effect Operational Rejection

Selection of authored topics (`select_authored_topic`) enforces scene, bundle, and panel
budgets before entering any database transaction and before applying state mutations (such as
talk affinity advancement or session updates). Oversized content raises
`DialogueBudgetExceededError`, resulting in a safe operational refusal with zero partial side
effects; relations data and session snapshots are preserved untouched.

The successor bundle budget measures the selected delivery plus reachable `pure_chain`
successors for a **formal** delivery only. A refusal reveals no successor, so an
undelivered successor's protected size never blocks a permitted refusal; the refusal
scene and the complete resulting panel are still measured against their own budgets.

## Server-Qualified Topic Availability

`world/rules/dialogue_availability.py::project_topics(context)` is the single
availability/disclosure authority. The version-3 panel's `choices`, the exploration
`explore.talk_scripted` vocabulary, the deterministic selection boundary and the text
`talk` surface all read it, so no surface can disagree about a topic or disclose a
protected body first.

- **hidden** topics are absent from every projection, and an explicit topic ID behaves
  exactly like an unknown one.
- **locked** topics (declared `unavailable: "locked"` with an authored `refusal`) carry
  only the stable ID, keyword, label, lock state, canonical `requirement_hint` and the
  server-built `{npc_id, topic_id, context_id}` action descriptor. Selecting one delivers
  the authored refusal with zero effects and never the fallback/variant body.
- **open** topics expose the same descriptor fields only; the authorized scene is chosen
  inside `select_authored_topic` after it rechecks current canonical state.

No row, choice, affordance descriptor, hint or text answer carries scene text, a variant,
a fallback, a successor bundle or a private phase body. The projection is pure: it writes
no session, reading record, affinity value or world state.

Guarded topics fail closed. A `requires` that does not hold is hidden or visibly locked
per the declaration. `predecessors` are served by the owner's saved reading: a topic whose
predecessors are not all saved is withheld entirely — even when declared
`unavailable: "locked"` — so a public successor never advertises itself before its
predecessor is read and a protected qualified descendant is never revealed early. A
projection with no lawful actor withholds every guarded topic instead of asserting an
availability; and a locked row whose canonical hint cannot render is withheld rather than
shipped.

Availability is never accepted from the client. The composed
`explore.talk_scripted` payload is exactly `{npc_id, topic_id, context_id}` plus the
server-injected `selection_id`; any extra field (including an `availability` flag) is a
malformed payload.

## Reading, Completion and Pure Chains

`world/narrative/dialogue_reading.py` owns the owner's persisted reading record on the
exact Shared-contract v2 Attribute shape:

```
dialogue_reading = {
  schema_version: 1,
  revision: int,                       # monotonic; increments only on a real change
  hosts: {host_key: {
    initialized: bool,                 # observation owns this (unread-notices)
    topics: {topic_id: {completed, ever_open, announced}},
    pending_batch: null | {batch_id, topic_ids, created_revision},
  }},
}
```

`reading_for(owner, host_key)` is pure: it never creates or repairs storage, and a corrupt
value reads as empty with one `dialogue_reading_integrity` event. `record_completion`
opens `transaction.atomic()`, makes a guarded owner-row `UPDATE` its first statement (the
SQLite write lock), reads the raw persisted Attribute through the `db_attributes` join,
merges exactly one host/topic in fresh containers, and compensates the Attribute cache on
failure. Observation (below) owns `initialized`, `ever_open`, `announced` and
`pending_batch`; a completion never touches them. Keys are the stable `host_key` and
source-aware `topic_id`: a physical dbid is never a reading key, so possession,
save/reload, a rematerialized binding and a returning generated phase share one record,
and equal local IDs in different package roles stay separate.

### Unread observation and unlock batches

`observe_availability(owner, host_key, open_topic_ids, *, declared_topic_ids, initial,
context_id, quiet_topic_ids)` and `claim_unlock_batch(owner, batch_id)` reuse the
completion lock discipline. Both run only inside the committed availability fan-out
(`world.rules.dialogue_availability._fan_out_availability`, reached from every
`refresh_dialogue_availability`/`queue_dialogue_refresh` call, including the
`cause="open"` refresh of every successful open or selection). Presenters, snapshots and
the client never call them, and a freeform-only host (no scene source) is never observed.

Classification is per stable topic ID, for static and generated sources alike:

- **First seen** (no row yet, including every ID of a newly permitted generated phase on
  an already initialized host): the row is inserted with `ever_open` and `announced`
  equal to its current openness, so a first visit or a phase's first appearance shows
  unread markers without an unlock notice. A host first observed by a canonical
  refresh rather than an open initializes exactly the same way.
- **Later opening**: a previously observed locked/hidden row that opens becomes
  `ever_open`. While it stays uncompleted and unannounced it joins the host's one
  `pending_batch` (at most 16 IDs in declaration order; any further IDs follow in the
  next batch). Refusal playback changes nothing, so a refusal then an unlock still
  announces once. A completed row, and a public chain successor declared with
  `disclosure: pure_chain` and no `requires` (its openness comes only from reading its
  predecessor), are marked announced silently.
- **Retirement**: a pending ID that is no longer declared (a retired phase) or is
  completed is suppressed (marked announced); a pending ID that merely relocked leaves
  the batch and stays eligible for a later reopening. Returning to a phase never resets
  completion or history.
- **Relock/reopen and variants** never reset `completed` and never re-announce.

Observation does not bump `revision` and stores no recipient context. Right after it,
the fan-out claims the pending batch under the owner lock (marking its topics announced)
**before** pushing, with or without a live watcher, and emits
`dialogue_unlock_batch_claimed` (`char`, `actor`, `npc`, `host`, `batch`, `topics`,
`context`, `cause`). A claim is at most once, so a duplicate refresh, a second
connection, a failed push or a reconnect can never replay it; the durable unread markers
(`unread` on open, uncompleted rows) remain. An observation failure logs
`dialogue_unlock_observation_failed` once and the plain panel is still pushed.

`push_dialogue_reading(owner, unlock_batch=claimed)` wraps the claimed batch separately
for each current watcher whose puppet talks to the same logical host: the wire
`unlock_batch` is `{batch_id, host_id, context_id, topic_ids}` with that watcher's own
physical host identity and context and only the batch topics its freshly rendered panel
lists as open. Contexts C1 and C2 of one owner at host 41 both receive batch U, each with
its own context; another character of the same account receives nothing. Snapshots
always carry `unlock_batch: null`. The validators on both sides require the batch to name
the panel's own host and context and 1..16 unique open choice IDs in declaration order.

The client (`stores/elosern/dialogue_reading.js`) keeps a memory-only set of seen batch
IDs and a bounded pending list per character and context. It defers every batch until
the current scene's explicit finish returns the choices, then shows one non-focus-stealing
`unlock` toast per batch naming the still-unread topics (topics saved or read meanwhile
are dropped; an emptied batch shows nothing). A changed host, context or character, or a
reload, discards pending notices; the persistent unread pips in the choice list remain.

### Session receipts

`db.dialogue_session.completion_receipts` holds at most 32 exact
`{delivery_id, context_id, topic_id, scene_revision, phase_revision, kind, predecessors}`
rows, at most the latest and previous formal delivery per topic. The sole session writer
merges them: malformed rows are dropped, a repeated delivery replaces its row, and a third
delivery of one topic retires that topic's oldest receipt. Refusal, opening and service
deliveries never hold a receipt. A new context, phase or control identity starts an empty
set, so a retired phase's receipts reject while the stable topic's saved completion stays.

### Completion

`explore.dialogue_complete` carries exactly
`{npc_id, delivery_id, context_id, topic_id, scene_revision}`.
`world.rules.dialogue.complete_dialogue_delivery` accepts it only when the actor's LIVE
session (never a caller-supplied snapshot) still owns a retained receipt whose kind is
formal and whose context, topic, exact scene revision and phase match the current
authenticated context, host binding, owner and actor. It never re-runs eligibility or
settles an effect. Refusals carry stable codes: `dialogue_context_closed`,
`dialogue_receipt_unknown`, `dialogue_receipt_foreign`, `dialogue_receipt_stale`,
`dialogue_receipt_kind` and `dialogue_predecessor_unread`; each writes nothing and
schedules nothing. An accepted completion persists reading and then queues
`refresh_dialogue_availability(owner, cause="reading_completed")` on commit, so a
qualified successor that just became eligible is projected without waiting for an
unrelated state change. A duplicate acknowledgement returns `already_saved` with the
unchanged revision. Delayed completion of an earlier topic stays valid while its receipt
is retained and never replaces the currently playing scene.

### Pure chains versus qualified successors

Selecting a formal root also pre-delivers its eligible public closure: every node declared
`pure_chain` whose predecessors are the root or an earlier qualified public node, in
predecessor order (at most 15). A node that needs an out-of-chain predecessor is omitted
together with its dependents, and traversal never passes a qualification boundary, so no
qualified descendant's body is bundled. Each public node gets its own server receipt
(`kind: "formal"`, no selection receipt, no effect — including no talk affinity) and rides
the panel's `pure_chain` as `{delivery, predecessors}`. The chain is re-derived for the
CURRENT delivery from those receipts, requiring the exact authored scene revision, so a
stale body is omitted with its dependents rather than replaced.

The text interface emits the whole attributed scene in predecessor order; a complete
successful emission counts as reading and each emitted node is completed through the same
service. A failed or partial emission stops the chain and marks neither that node nor its
dependents. Naming a public successor explicitly before its predecessor's reading is saved
answers with a fixed refusal and never selects or marks anything.

## Availability Refresh

`world/rules/dialogue_availability.py::refresh_dialogue_availability(owner, *, cause)`
is the explicit refresh API. It re-resolves the owner's current acting body (the owner,
or the companion it lawfully possesses) **inside** a `transaction.on_commit` callback,
emits the `dialogue_availability_refreshed` boundary event with
`char`/`actor`/`npc`/`context`/`cause`, and fans the freshly rendered `dialogue` panel
out through `web/webclient/presentation/dialogue_push.py::push_dialogue_reading`. That
helper discovers the owner's current account connections through
`commander_sessions`, adds the owner's own body and its currently possessed companion,
filters every candidate by `resolve_commander(puppet) is owner`, and publishes one
epoch-guarded panel per connection from THAT connection's own puppet. Another character
of the same account receives nothing, and no connection's locally playing scene is
replaced. Nothing is persisted; a failed push is isolated to one
`dialogue_availability_refresh_failed` event and recovers on the next canonical sync. A
rolled-back owning write schedules nothing.

Canonical mutation writers call the companion
`world/rules/dialogue_availability.py::queue_dialogue_refresh(owners, *, cause)` with the
owner objects they captured **before** any destructive membership or control write. It
deduplicates the lawful owner identities, registers one commit callback per write, and
re-resolves each owner row, acting body, host binding and published generated phase
inside that callback. Pre-commit eligibility is never used, several callbacks from one
outer operation may each re-evaluate the final committed state, and an outer rollback
discards them all. `affected_dialogue_owners(entity, *, prior_owner=None)` is the
discovery half: a persistent player owns itself; any other body contributes its lawful
party-bound owner and its currently lawful possession owner; a caller detaching a body
passes the pre-detach owner as `prior_owner`. It never returns an account-wide sibling
character and never creates a conversation, session or selection. Refresh is
source-neutral: it re-reads the current static snapshot or published generated
binding/phase, so no static membership filter or immutable-package edit is involved,
and the already-delivered scene keeps its selected wording.

An already delivered scene keeps its chosen variant/scene revision across a refresh: the
session stores the committed delivery, and only the projected choices are recomputed.
Context invalidation, phase change, movement, combat and host cleanup keep their existing
owners.

### Canonical physical source matrix

These are the exact commit hooks `authored-dialogue-refresh-physical` owns. Every row
captures its owner(s) before the write, registers only after the successful write, and
therefore publishes nothing when the owning transaction rolls back.

| Condition source | Exact commit hook | Captured owner(s) | Committed acceptance |
|---|---|---|---|
| Carried item, including use/trade/transfer | `world/rules/equipment.py::apply_inventory_plan`, after the inventory + ACQUIRE writes inside the caller transaction | `affected_dialogue_owners(plan.entity)`; each transfer plan captures its own owner | Telnet, another web connection and a no-session call all refresh; an outer rollback publishes nothing |
| Worn exposure bias | `world/rules/equipment.py::toggle_equipment`, after the final equipment/gauge write | `affected_dialogue_owners(entity)` | Wearing/unequipping changes the threshold choice while the delivered variant stays unchanged |
| Base exposure transition | `world/rules/sexual_transitions.py::apply_event`, after the converged cascade | owner captured before the operation | Threshold crossing refreshes once the final committed state is visible; a later fault cancels the callbacks |
| Structured social identity | `world/rules/social_identity.py::set_social_identities`, after the validated write | `affected_dialogue_owners(entity)`; construction with no lawful owner is a no-op | Tag add/remove refreshes a live possessed actor; persona prose is not a source and has no effect |
| Skill ownership and proficiency | `world/rules/progression/_gates.py::award_practice_xp` after the stored XP assignment; `world/rules/progression/_lineage.py::apply_lineage_auto_seed` after the ownership/proficiency assignment; `world/rules/cross_lineage_unlock.py::grant_owned_skill` immediately after the ownership write, only on a new grant | affected learner owner | Passive/active ownership and proficiency thresholds refresh from any origin (study, another session, a scheduled tick) |
| Race | existing construction/import establishes race before any dialogue; opening and selection always re-read the acting body's race | no speculative new race writer | A new body's race is honored; control refresh owns changing actor identity |

The cross-lineage hook is exactly `grant_owned_skill`, not `clause_satisfied` and not a
second call in `evaluate_cross_lineage_unlocks`; no new skill mutation API is
introduced. A raw GM console Attribute repair stays outside ordinary gameplay
publication and its next canonical sync re-evaluates state.

### Canonical lifecycle source matrix

These are the exact commit hooks `authored-dialogue-refresh-lifecycle` owns. They reuse
`queue_dialogue_refresh`/`affected_dialogue_owners` unchanged; no third event bus exists.
Every row registers on the owning transaction, so a rollback publishes nothing and the
callback re-projects from the final committed state.

| Condition source | Exact commit hook | Captured owner(s) | Committed acceptance |
|---|---|---|---|
| Guild registration and rank | `world/rules/guild.py::register_adventurer` after the registration write; `world/rules/guild_exams.py::settle_exam_outcome` after a passed rank assignment inside the settlement transaction | explicit actor | Registration and a promotion each open rank topics independently; a failed exam schedules nothing |
| Quest lifecycle, every state | `world/quests/transitions.py::_schedule_transition_events` (the diff boundary every replacement/delta/pending-effect writer calls) plus `apply_quest_log_delta` after the final replacement | quest actor owner (`affected_dialogue_owners(actor)`) | Accepted, in-progress, completed, failed, invalidated and absence transitions all refresh; completion-only observers are not used |
| Reward claimed | `world/rules/guild.py::write_reward_claims` inside the caller transaction | owner actor | Counter and automatic claims refresh the named completed record after commit |
| Host affinity | `world/rules/affinity.py::apply_affinity_change` on a value change and `seed_affinity` after the save; `raise_affinity_cap` alone is not a source | explicit player | Another connection's write updates choices; a rollback opens nothing |
| Companion membership | `world/rules/party.py::_write_binding` for join/leave/general/temporary mutations and `purge_npc_memberships` | player/prior owner captured before a detach | Removal, expiry and auto-leave refresh the owner's unrelated-host conversation |
| Companion presence and deletion | `typeclasses/npcs.py::at_post_move` and `at_object_delete` | `affected_dialogue_owners` with the prior owner captured before purge | A bound companion leaving/returning changes `CompanionPresent` while the conversation host stays present |
| World time | `world/rules/clock.py::WorldClock.advance` after tick persistence, only on a daypart crossing | `session_bearing_dialogue_owners()` (stored `dialogue_session` discovery), independent of the action scope | A midnight/daypart commit reaches an idle owner not participating in the initiating action; a within-daypart advance schedules nothing |
| Generated phase | `world/quests/story_dialogue.py::transition_story_dialogue` commit callback through `refresh_dialogue_phase` | every live session naming the advanced role actor | A new phase retires the obsolete delivery/receipts before the new projection; saved reading persists |
| Control | `world/rules/possession.py::_enter_possession`/`release_possession` after the verified transition | explicit player captured before the old body detaches | The old actor's session retires; release republishes the new body's own view without copying the obsolete possessed scene |

Completion-to-refresh
(`cause="reading_completed"`) is queued by `complete_dialogue_delivery` only after an
accepted, committed reading write. Command and
presentation observers are not a substitute: a committed writer with no live session
(Telnet, a scripted clock tick, another actor's change, or an offline character) never
walks a command, panel render or action path, so only the owning writer can schedule the
refresh. The one non-mutation cause this slice adds is `cause="open"` from the successful
open/selection path.

The text `talk` command introduces no new listing syntax: its topic enumeration (which
keyword resolves to which topic) reads the same projected rows, so a hidden keyword
answers with the ordinary no-understanding line instead of its formal prose and a locked
keyword plays the authored refusal. A player-facing text listing remains a UI decision
outside this slice; no scenario or existing surface defines one.

## Reconnect and Transport Generation Adoption

Presentation coordinator (`coordinator.py`) enforces `check_envelope` on candidate snapshots
and updates before advancing session revision counters. The UMD client store (`store.js`)
applies the same conditional allowance in `checkEnvelope`:
- A reconnect full snapshot establishing a new presentation epoch adopts the bounded frame up
  to 98,304 bytes cleanly.
- Stale snapshots from retired epochs remain rejected.
- Non-dialogue frames or frames where the dialogue-removed envelope exceeds 65,536 bytes are
  rejected.
