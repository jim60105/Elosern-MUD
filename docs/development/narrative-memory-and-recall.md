# Narrative Memory & Fast Recall Developer Guide

## Overview

The `world/narrative` subsystem manages persistent narrative events, character memory cognition, and calibrated lexical recall.

### Core Modules

1. **`world/narrative/events.py`**:
   - Manages durable `NarrativeEvent` records with immutable provenance and idempotent projection tracking via `ProjectionProgress`.

2. **`world/narrative/memory.py`**:
   - Manages owner-scoped `MemoryRecord` and append-only `MemoryRevision` history.
   - Enforces knowledge scopes (`witnessed`, `told`, `inferred`, `public`) and owner privacy boundaries.
   - Increments `OwnerMemoryGeneration` on effective record changes.

3. **`world/narrative/tokenizer.py`**:
   - Deterministic Traditional Chinese and alphanumeric tokenizer (`tc_v1`).
   - Extracts canonical entity terms (e.g. `尤漢娜`, `銀羽驛行`, `保護`, `遭遇`).
   - Generates CJK unigrams and bigrams with Traditional Chinese stopword filtering.

4. **`world/narrative/ranker.py`**:
   - Pure-Python BM25 ranking (`bm25_v1`, $k_1=1.5, b=0.75$).
   - Precision-first lexical qualification threshold (`MIN_LEXICAL_THRESHOLD = 2.0`).
   - Requires substantive multi-character content overlap to prevent single common characters from admitting unrelated episodes.

5. **`world/narrative/recall.py`**:
   - `fast_recall(*, owner_id, query, requester_id=None, thread_id=None, limit=5, core_limit=3, working_limit=5, ...)`:
     - Step 1: Permission filtering and explicit scope checks (`get_owner_memories`, optional `thread_id` relation match).
     - Step 2: Bounded fixed memory selection (core and working tiers) ordered deterministically.
     - Step 3: BM25 lexical recall over qualifying candidates. Candidates scoring below the threshold are pruned; if none qualify, `recalled` is empty `[]`.
     - Step 4: Metadata bonuses (salience, confidence) rerank lexical candidates without ever rescuing non-lexical records.
     - Step 5: Replaceable tokenization cache keyed by owner generation.
     - Emits `narrative_fast_recall_executed` via `world.observability`.

6. **`world/narrative/calibration_runner.py` & `world/narrative/calibration_corpus.py`**:
   - Offline synthetic labeled fixtures and evaluation runner measuring Recall@1, Recall@2, false positive rate, and latency.
   - Committed report at `world/narrative/calibration_report.json`.

7. **`world/narrative/context.py`**:
   - Reproducible permission-filtered cognition context assembly with enforceable rendered budgets and immutable source snapshots.
   - Stable ordering: global rules, world digest, capability contract, character anchor, epoch summary, turn frames (recall items and affordances).
   - Budget profiles with completion reservation, future Deep Recall reservation, and estimation safety margins; selection and assembly share one rendered representation (headings included), and mandatory-section overflow rejects before generation.
   - Immutable `NarrativeContextSnapshot` model (append-only manager plus instance guards) tracking source IDs, read revisions, section hashes, budget accounting, truncation decisions, and the reconstructible rendered payload.
   - Thin `NarrativeRequestDescriptor` binding prompt messages, validators, and snapshot/trace identities, rejecting mismatched context/snapshot provenance.
   - Every fresh assembly reads the owner memory generation, so effective-memory changes surface to new generations while retries re-read the authoritative persisted snapshot instead of rewriting it.

## Fixed-hour correspondence delivery (W2)

`world.narrative.correspondence.send_letter` accepts persistent character primary
keys, a nonblank body of at most 8000 characters, and an optional stable source
identity and reply-to source identity. Preflight rejects unknown/non-character
recipients before persistence. Reusing the source identity is idempotent only
for the same sender, recipient, body, reply link, and source snapshot. Accepted `LetterSend` rows
are immutable; indexed `LetterState` rows own transitions separately.

The send fixes the current authoritative tick and a due tick exactly
`CLOCK_YAML["seconds_per_hour"]` later. Deterministic startup registers
`correspondence_delivery` after `npc_schedules` and before
`instance_reclamation`. Command, combat, and skip advances all settle exact
deadlines in `(start_tick, end_tick]`, including non-calendar-aligned sends.
Rejected skips do not advance; settlement never assumes the requested interval.

NPC recipients become `delivered`; player recipients become `available`, without
collection/read ticks. Delivery performs no recipient lookup, trait mutation,
quest transition, model call, or image call. Movement and absent live locations
cannot affect accepted delivery. Collection and reading use the player surface
below; optional replies use their own remote channel. Correspondence memory
projection is owned by `world.narrative.correspondence_memory` (see below).

Each transition atomically records a private `NarrativeEvent` with a stable
`correspondence:<send-source>:<status>` identity and pending `ProjectionProgress`.
`CORRESPONDENCE_PROJECTOR_VERSION = 2` keeps these progress rows for the
correspondence-owned consumer; the generic live-memory projector's version-1
startup queue never consumes them. The rows stay pending through the clock
advance — that pending downstream work is part of the archived delivery
contract — and the correspondence consumer drains them. Tables share the clock
transaction.
The declared surface contract has no cached entities: ordinary Django rows are
queried fresh, updated through querysets, and returned only as detached frozen
values. No cached mutable row survives rollback. Boundary logs run on durable
commit and include identifiers/ticks/status only, never letter bodies.

## Optional NPC replies (W2)

Delivery creates one durable `LetterReplyWork` per incoming NPC letter in the
same clock transaction. Delivery and startup never await generation or sweep the
pending queue. An intentional owner request calls
`server.correspondence_service.request_letter_reply(source_id)` once; callers
may inject a recorded `FakeLLMClient`. The service constructs the dedicated
`correspondence` profile client in production. A later explicit request is a new
attempt through the existing guardrail; there is no automatic retry policy or
promise that an NPC will respond.

`prepare_reply` captures the full delivered source and recipient-owned W1 recall
in an immutable context snapshot. The 32768-token context budget reserves the
profile completion budget, recall reservation and safety margin; its turn-frame
target/bound are 22000/24000 tokens, allowing the accepted 8000-character input.
The equipped model for the `correspondence` layer must therefore accept a 32k
context; a smaller window degrades the attempt to pending, never to truncated
input.
Uncaptured or truncated incoming inputs cannot produce a reply. Each attempt
captures a fresh snapshot; superseded completions and changed memory generations
or recipient anchors leave work pending. No remote player's private traits or
face-to-face context enter the prompt.

The dedicated prompt/schema admits a nonblank Chinese body and `none` or a
nonnegative `adjust_relation` delta bounded at 10; a zero delta is `none`, so the
rules writer is never called and no empty affinity record is materialized.
Narratively described meetings,
clues and quest claims remain statements in the stored letter. No quest,
objective, codex, inventory, physical action, party invitation or appointment
writer is called. Relationship proposals route to `world.rules.correspondence`
and the existing affinity writer's shared `AI_DIALOGUE` bounds/daily budget;
they do not require co-location. Rejected effects leave work pending rather
than sending speech that implies a committed effect.

Settlement serializes the work and recipient, revalidates the current source
and snapshot, and atomically commits relationship changes, the immutable
reply-to/source-snapshot link, outgoing send and work completion. The outgoing
deadline is one game hour after this send's own commit tick. Replay returns the
same outgoing letter without generating or charging relationship budget again.
Failed send settlement restores Evennia's relationship cache as well as rolling
back database writes. Failures never invent fallback letters.

No player command syntax or browser action changed, so command documentation
remains unchanged. Boundary events carry IDs/counts/ticks, never letter bodies,
private recall or prompts.

## Player correspondence surface (W2)

`world.narrative.player_correspondence` is the sole player lifecycle writer.
Authored `PlaceDefinition.letter_service` capabilities use the existing unique
tagged permanent-interior anchor; descriptive `PlaceKind` never grants service.
Both settlements have a hostless 銀羽驛站 branch. Any branch acquires all available
letters for the player's identity, preserving unread state. Metadata pages
contain at most twenty collected/read rows and an opaque numeric next cursor;
listing never fetches bodies or creates a clock.

`read` gates owner and collection inside the transaction, conditionally changes
`collected` to `read`, and commits the first-read tick, one private
`correspondence:<source_id>:read` event, its version-2 progress row and the
owner's told memory together. The event references the immutable original
letter; it does not copy prose. Rereads anywhere perform no canonical writes,
and the completed row means a replay adds no cognition. Collection creates no
content knowledge or read event; the generic version-1 projector cannot consume
this queue.

Text `信件` (`letters`) and the four allowlisted browser `letters.*` actions use
these same APIs. Browser metadata and explicit-open bodies use the existing
correlated action result-data channel, not a new panel protocol. Up to 8000
Unicode code points travel as at most four 2000-code-point parts, preserving
the transport's existing 2048-code-point leaf bound. Unknown payload fields,
including forged owner fields, fail closed. Browser retries retain the send
identity while the draft is unchanged; server sends remain atomic/idempotent.
Session/character replacement drops local private data and never automatically
replays a send. The tool group's envelope opens the shared focus-trapped drawer;
its ruled folio uses shared ink/paper/brass tokens without nested card boxes.

Each text command invocation is a new send, not an identified request replay.
Identical intentional letters must remain possible: deduplicating by body/name
would incorrectly suppress legitimate correspondence. Text clients must not
automatically retry an uncertain send after a lost acknowledgement. Both player
references state this distinction. An identified text retry protocol would be
a new command contract, outside this boundary's existing text conventions.

Offline smoke: run
`world.narrative.tests.test_player_correspondence.PlayerCorrespondenceTests.test_real_text_and_browser_offline_smoke_and_log_privacy`
through the guarded Evennia test entry. It exercises actual text send, committed
clock delivery, another-branch browser collection, portable browser/text reading
and first-read log privacy with synthetic data and no generation services.
Delta-only coverage IDs are obtained by the later spec-sync owner after sync.

## Correspondence cognition projection (W2)

`world.narrative.correspondence_memory` is the version-2 consumer of the durable
letter transition sources. The receipt is the authority, never the claim: a
letter creates told cognition only, with no world truth, quest objective, item,
appointment or defeat fact. An NPC gains a letter at its delivery occurrence; a
player gains it only at the first read after collection. Undelivered letters and
collected-but-unread letters have no memory at all, so retrieval, fixed
selection and prompt context cannot expose them.

Each memory keeps immutable letter provenance (letter source identity, sender,
sent/settled ticks, reply-to link) plus `statement` with the letter body, scope
`told`, category `correspondence` and the claim confidence below a witnessed
observation. `summary` stays a bounded excerpt, because the rendered cognition
line enters prompts while the full statement stays in owner cognition. The tier
is `working`, so bounded fixed selection supplies face-to-face continuity
instead of copying the letter archive into `DialogueTurn` speech.

Settlement drains the same durable queue from four boundaries. Server startup
recovers every pending version-2 source left by an interruption (boot-tolerant
`narrative_correspondence_projection_init`; the pending source stays pending if
it must be retried). `prepare_reply` drains its letter's delivery source after
the completed-work early return and before recall capture: a ready reply either
sees the settled delivery cognition or waits, and generation never bypasses the
delivery knowledge boundary. `build_dialogue_context` drains before its recall
selection, so a delivered letter is present for a face-to-face turn. The
player's first read projects inside the read transaction, because that
occurrence is the owner's knowledge boundary and nothing else would trigger it.

Projection is idempotent: the `(source_id, projector_version)` progress row
settles once and a replay returns the original records instead of duplicating
memories, and both versions keep independent rows. Boundary events carry only
source/owner/version/count identifiers — `correspondence_memory_projected`,
`correspondence_memory_projection_skipped` (a pending source with no durable
event stays pending and is reported) and `correspondence_memory_projection_failed`
— never letter text. A source whose projection fails keeps its pending row by
design (the durable work is never dropped) and is retried at the next drain
boundary, each attempt reporting the exception chain; there is no give-up
threshold. Only the startup recovery entry announces the cataloged pending
scan, so the hot dialogue and reply drains stay quiet.

Delta-only coverage IDs for this boundary are obtained and annotated by the
later spec-sync owner after the delta spec reaches `openspec/specs/`; this
change annotates its substantive tests against existing canonical main IDs.

## Durable face-to-face dialogue (W1)

`world.narrative.dialogue` replaces the destructive NPC Attribute history.
`submit_turn` allocates one ingress identity and preserves the original player
speech. `run_npc_exchange` carries that identity and the immutable snapshot ID
in its result; it never records an undelivered NPC response. Talk and both
invitation delivery callers record the displayed response through
`settle_response`, whose unique `(submission_id, kind)` key prevents duplicate
settlement. Authored offline greetings are delivered turns; silence and
stale-persona responses are not. Existing late co-location/schedule rejection
still displays validated speech but rejects its intent, so that displayed
speech remains in the archive.

`pair_view` reads only the configured tail (at most 12 turns), keyed by persistent
NPC/player identities. Trimming affects rendering only. Omitted-turn counts
accompany the prompt and snapshot; originals remain recoverable in
`DialogueTurn`. Changing a persona changes later rendering without rewriting
historical speech. There is no compatibility history store or migration of old
Attribute data.

Each exchange uses owner-permitted Fast Recall followed by the existing context
builder. Core and working selections remain fixed context. Protection events
project to the existing `archive` tier: durable episodic experience excluded from
fixed working selection, but eligible for relevant lexical recall. Unrelated
questions do not force that episode into cognition. The W1 system template stays
in the prompt library; cognition is added to the existing user JSON placement.
The snapshot captures the exact final system/user messages and only sources
whose recall block survived rendering. Normal logs contain IDs/counts, never
speech, private persona, or prompt prose.

## Author-controlled Yohanna protection/revisit route

The fresh NPC import card is `world/imports/examples/yohanna_cooper.json`.
It authors Yohanna Cooper's hereditary barrel-making family and guild artisan
connections, independently of temporary handoff plots. The compact-card importer
is the persona/age/name-validation boundary; `NPC_SOURCE_INVENTORY` records its
existing `import_example` ownership.

For an author-controlled local world, put an unbound player at a reachable room
on the guild approach, with no current fight. From the existing administrator
Python seam, call `world.rules.protection_demo.prepare_protection_demo(player)`.
For example, in an administrator's `@py` context where `self` is the player:

```python
from world.rules.protection_demo import prepare_protection_demo
npc, enemy = prepare_protection_demo(self)
```

This imports Yohanna beside the player, binds her through the real party owner,
and engages the lowest registry threat tier. It does not declare a victory.
Use the existing combat attack/action menu to defeat the creature while Yohanna
survives. Real combat settlement commits the protection fact; the normal
projection consumer creates her witnessed episode. Dismiss her with the existing
party-leave action so she stays at the encounter location. Use ordinary downtime
commands over several days, return to the same reachable room, and talk about
the earlier protection. An unrelated topic omits the recalled episode; the
pair's original dialogue can of course still mention it.

No new player command, alias, syntax, or availability context is introduced.
Permanent acceptance tests use a synthetic card and fixed combat rolls plus
`FakeLLMClient`; the separate registered authored-data contract checks the shipped
card and setup. A controlled recorded/offline smoke can run the focused
`DurableDialogueTests.test_real_protection_commit_multi_day_revisit_and_permissioned_recall`
and `test_offline_delivered_greeting_is_durable_but_silence_is_not` labels through
the guarded Evennia test entry point. Do not enable live model/image services for
automated checks or assert live wording. New delta-only requirement annotations
are added by the later spec-sync owner after obtaining their canonical main IDs;
this change annotates substantive tests against the existing main IDs.

## Explicit dialogue epochs and stable prefixes

DialogueEpoch is an append-only pair boundary, separate from the current-target
session. DialogueFrame retains canonical JSON bytes, tick and captured memory
source revisions. Location, affinity, recalled cognition and player context
belong to the current frame. Replayed frames retain their original bytes; the
current authority marker supersedes their state without rewriting history.
Global rules and world digest precede the prompt-library capability/character
anchor. The four `npc_dialogue.system` placeholders remain supported, with
`location=""`; NPC persona remains system-side and public player persona stays
user-side. Changes to rendered anchors, persona or rendering version create a
new epoch. Historical affinity numbers remain covered by the no-leak validator.

The deterministic owner exposes `start_epoch(npc, player)` for natural
boundaries and `compact_epoch(npc, player, client)` for compaction. Inject an
`OpenAICompatClient(get_profile("dialogue_summary"))` in production, or a
recorded FakeLLMClient in tests. The summary capability uses its own schema and
guardrail hooks; it summarizes bounded original dialogue, never state frames.
Accepted generations retain original turn hashes/revisions and their immutable
snapshot. Subsequent summaries can reference the prior summary generation.
Original turns are never removed. Invalid, offline and stale completions do
not activate successors. The active epoch remains usable through a bounded
tail view. NPC-row locking and pair/sequence uniqueness serialize boundaries.

The `dialogue_summary` profile uses the existing endpoint/profile controls
(including generated `LLM_DIALOGUE_SUMMARY_*` environment names). Provider
cache controls are optional; validated cached-token counts are metadata only.
The [rendered calibration report](dialogue-epoch-calibration.md) records profile
reservations, source/output measurements and hard summary limits.
No player command surface changes, so both command references are unchanged.
New dialogue-epochs main requirement IDs must be obtained and annotated by the
later sync/archive owner; active delta requirements are not canonical IDs.

## Story threads: lifecycle and real linkage (W3)

`world.narrative.threads` owns the deterministic `StoryThread` row: immutable
`origin`, `participants`, `visible_to` (the owner ACL), the factual
`factual_summary`, `unresolved_questions`, `proposed_plans`, gameplay-established
`commitments`, `memory_references`, `development_ticks`, the lifecycle `state`,
and a monotonic `revision`. `thread_id` and `origin` are immutable, every
effective change appends an append-only `StoryThreadRevision`, and the durable
rows reject queryset-level mutation, bulk updates, and deletion.

Facts stay separate from plans. `establish_commitment` is the only path that
appends to `commitments`, and it requires an existing durable `NarrativeEvent`
that is not a statement channel: claims (`claim_receipt`), correspondence
(`correspondence_delivery`/`correspondence_read`), and private authoring are
rejected, so a letter's expressed willingness is linked as
`relation="statement"` and never becomes a commitment. An allowlist over the
not-yet-existing gameplay commit event types would be a one-entry stub, so the
gate is the negative statement-channel set recorded in the dev doc; a future
statement-flavoured event type must join that set.

A commitment replay is not an effective change: repeating an identical
commitment text for an already-linked event returns without advancing the
revision, so later snapshots are not needlessly invalidated.

Lifecycle is explicit. `transition_thread` accepts only the four states and
refuses to move out of `resolved`/`abandoned`; `mark_thread_dormant` and
`apply_inactivity` may only move an active thread to dormant, using the most
recent instant across creation, `development_ticks`, and link ticks, so
inactivity alone can never produce abandonment. Abandonment and resolution are
explicit operations with a stated reason. `note_thread_quest_completion`
requires an existing quest link, records `relation="quest_completion"`, and
leaves the thread state untouched: a completed quest never resolves its parent
thread. Quests are linked by durable identity only (`link_quest_to_thread`);
`world/quests` still owns quest lifecycle, so narrative neither duplicates it
nor reads quest registries, and a quest reference is stored exactly as supplied
(not existence-checked) with `identity_only` recorded in its link provenance.

Each effective change appends one append-only `StoryThreadRevision` row inside
the same transaction as the materialized update. The unique `(thread, revision)`
row is the concurrency backstop: a backend without row locking lets the losing
writer fail loudly with a typed `NarrativeThreadError` instead of silently
losing an update, and the enclosing transaction rolls back.

Linkage is real. `StoryThreadLink` rows are keyed
`(thread, source_kind, source_ref, relation)` and validate that the referenced
`NarrativeEvent`, `LetterSend`, `DialogueTurn` (`submission_id:kind`), or
`MemoryRecord` (`mem:<pk>`) row exists before a link is stored; relations are
whitelisted per kind. Source references are stored exactly as supplied and
matched case-sensitively, and a link is durable: it outlives a memory's
supersession, while recall still excludes superseded cognition unless it is
explicitly requested. `link_memory_to_thread` also writes the thread identity
into the memory's latest revision relations, which is what the existing
`fast_recall` thread scope filters on. Tagging a memory this way appends a
memory revision and therefore advances the owner memory generation: that is
intentional conservative invalidation of every later snapshot for the owner,
and no production path links on every turn.

Thread revision is the context read identity. `assemble_narrative_context`
accepts an explicit `thread_id`, reads the current revision for that scope and
for every validated memory's `relations['thread_id']`, records it on each
`SourceReference` and in `AssembledContext.thread_revisions`, and
`persist_context_snapshot` stores that map on the immutable snapshot;
`build_request_descriptor` compares it as provenance. New generations see the
new revision, while historical captures and retries keep the revision they
captured. The tokenization cache is deliberately *not* keyed by thread revision:
tokenization depends only on immutable record content, and any linkage change
already advances the owner memory generation that the cache is keyed on.

Explicit thread recall is gated before ranking. `fast_recall(..., thread_id=...)`
resolves the thread and requires the owner to be in `visible_to`; an unknown or
inaccessible thread yields no eligible views at all and emits the warn event
`narrative_thread_recall_denied`, so no private thread or source content enters
recall. Boundary events (`narrative_thread_created`, `narrative_thread_linked`,
`narrative_thread_revised`, `narrative_thread_recall_denied`) carry identifiers,
counts, ticks, and revisions only — never summaries, commitments, or letter
text. Delta-only coverage IDs for this boundary are obtained and annotated by
the later spec-sync owner after the delta spec reaches `openspec/specs/`; this
change annotates its substantive tests against existing canonical main IDs.

## Private dream authoring records (W3)

`world.narrative.authoring` owns the authoring boundary. An `AuthoringDraft` is
a private record of a negotiated direction: immutable `draft_id`, `owner_id`
and `created_tick`, the desired `direction`, durable `sources`, a monotonic
`revision`, and `confirmed_revision`. A `CreativeRequest` is an immutable,
versioned request created only by confirmation. Both are authoring data, never
in-world knowledge: they confer no clues, items, quest progress, persistent
stat changes, skill advancement, buffs, or codex unlocks, and the module
creates no `NarrativeEvent`, `ProjectionProgress`, or `MemoryRecord`, so a
private discussion is absent from cognition and recall by construction. The
module imports nothing from `world.ai` and opens no transport; confirmation is
deterministic and works with every generation service offline.

Confirmation is explicit and versioned. `save_draft` creates a draft, or
updates its content and advances `revision`; content is never silently
discarded (an identical save is a no-op). `draft.confirmed_revision ==
draft.revision` means the current version is confirmed, so editing a confirmed
draft makes the new version unconfirmed again and always requires a new
confirmation. `confirm_draft` validates the current version, then creates one
`CreativeRequest` whose `submission_key` is `"{draft_id}:v{version}"`. A repeat
confirmation of the same version — including after reconnect — returns that
same row without a second submission; the unique `submission_key` and
`(draft, version)` constraints are the durable "submit once" guarantee, not the
row lock (`select_for_update` is kept for backends that support it, SQLite
ignores it). The previously confirmed version stays authoritative and immutable
until a newer version is confirmed; an unconfirmed edit does not retract it.
A draft itself schedules nothing.

Validation is deterministic and concrete. `validate_direction` reads only
durable rows and returns either a normalized direction or named reason codes
with player-facing messages: referenced `thread_id` must exist, be owned by the
requesting owner (`thread_accessible`), and not be in a terminal state;
committed-history targets must exist and are then rejected as
`committed_history_rewrite` (personality and outcome rewrites have their own
codes); any requested `effects` are `unauthorized_effects`; shape, bounds and
unknown keys are `malformed_direction`/`malformed_participants`. A refusal
changes no durable state — `DirectionValidationError` carries the reasons and
the draft keeps its stored direction, so re-running validation reproduces the
same reason rather than reading a stored status that could go stale. Approval
is direction, not outcome: `new_story` directions unrelated to prior
experience are valid and simply become eligible only after explicit
confirmation.

Access is owner-scoped. `get_draft`/`get_request` raise `AuthoringAccessError`
for a foreign or missing record, and `list_drafts`/`list_requests` return only
the owner's rows. `collaborator_creative_brief` is the spoiler-filtered read
model for the collaborator: the latest confirmed version's summary and
preference fields only, with no source references, validation internals, other
owners' data, or StoryDirector-hidden answers (this record model has none). A
deterministic recency key (`submitted_tick`, then the durable monotonic row id)
makes `latest_confirmed_request` resolve same-tick submissions to the later
submission, so a caller-supplied `draft_id` cannot steer it.

Boundary events (`narrative_authoring_draft_saved`,
`narrative_authoring_draft_edited`, `narrative_authoring_validation_rejected`,
`narrative_authoring_request_submitted`) carry identifiers, counts, ticks and
reason codes only — never the direction summary, themes, or a reason message.
Delta-only coverage IDs for this boundary are obtained and annotated by the
later spec-sync owner after the delta spec reaches `openspec/specs/`; this
change annotates its substantive tests against existing canonical main IDs.

## Deterministic narrative attention (W3)

`world.narrative.attention` owns the deterministic filter-and-rank boundary that
narrows the directions a later StoryDirector may pursue. It generates no text,
calls no model, and persists no beat: `rank_attention` is a pure function over
plain immutable `AttentionCandidate`/`AttentionContext` values, and the module
is read-only, so a run never mutates, deletes, or hides unselected story state.
The output is a bounded `AttentionDecision`: the focus-limited `selected` set,
the full `ranked` order, the `excluded` candidates with their reasons, immutable
identity+revision `sources`, a `snapshot_hash` fingerprinting inputs and
configuration (not the order), and a `reason_counts` tally.

`build_attention_candidates(owner=...)` is the read-only durable extraction
layer. Every active `StoryThread` becomes a candidate marked `knowledge` (the
owner is in `visible_to`, is a participant, or owns a linked
memory/event/dialogue/letter experience) and `invested` (the owner is a
participant or owns such a linked experience) — an ACL-only thread is known but
not yet invested. Every valid `CreativeRequest` version becomes a
`confirmed` request candidate, with only the authoritative
`latest_confirmed_request` marked `authoritative`; earlier versions stay in the
result as `superseded_request` exclusions so the decision is observable.
Thread `unresolved_stakes` counts unresolved questions plus gameplay
commitments, `repetition` counts developments beyond creation, and
`last_activity_tick` is the latest development, link, or creation instant
(request candidates use `submitted_tick`).

Eligibility runs before any scoring. Knowledge (`unknown_to_owner`), an
invested source or confirmed request (`not_invested`), capability feasibility
(`not_executable`; only `dialogue`, `letter` and `quest` have deterministic
owners), location reachability (`location_unreachable`; `required_location` is
the most recent linked event location), a participant NPC whose
`schedule_state` blocks `interaction_reason` (`schedule_blocked`), and
superseded request versions are all excluded first, so a high-salience
ineligible candidate can never out-rank an eligible one. An unrelated new story
is therefore eligible only as an explicitly confirmed request, never as
automatic history.

Scoring normalizes named components — unresolved stakes, engagement,
relationship (`relations.affinity_for`), deadline, location relevance,
repetition and cooldown — each clamped to `0..1`, and combines them with the
calibrated `AttentionWeights`; repetition and cooldown subtract. Engagement is
built only from observable owner actions: initiated dialogue, sustained
correspondence, explicit clue questions, and committed gameplay participation.
Passive receipt (letter collection/reading, and the private
`correspondence_read` event it writes) is counted as `passive_receipts` and
contributes zero. Engagement is counterpart-scoped: the candidate's other
participants bound the queries, and a candidate with no other party is zeroed
rather than inheriting the owner's global activity. Ties resolve by
`candidate_id`, so identical inputs and
configuration always yield an identical order and reason data offline. Weights,
saturations, cooldown and the focus limit are calibration choices recorded in
`world/narrative/attention_calibration.py` and the committed
`world/narrative/attention_calibration_report.json` (regenerate with
`python -m world.narrative.attention_calibration`); the report pins the
deliberate behavior that cooldown plus repetition can outweigh a higher stake
for a just-developed thread, so attention does not repeat it.

Boundary events (`narrative_attention_ranked`, and the warn-level
`narrative_attention_candidates_truncated` / `narrative_attention_engagement_truncated`
when a read bound is hit) carry owner id, config version, counts, tick and the
snapshot hash only — never player prose, thread summaries, or direction text.
Delta-only coverage IDs for this boundary are obtained and annotated by the
later spec-sync owner after the delta spec reaches `openspec/specs/`; this change
annotates its substantive tests against existing canonical main IDs.
