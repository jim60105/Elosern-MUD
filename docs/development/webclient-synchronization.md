# WebClient presentation synchronization

The browser presentation wire is one versioned, exact-base delta protocol
shared by `web/webclient/presentation/protocol.py` (server validator and
envelope builder) and `web/static/webclient/js/elosern/protocol/` (browser
validator and reducer). Protocol version stays `1`: the project is unreleased
and this cutover ships no compatibility path for the previous shape.

## Envelopes

Two server messages carry presentation state. Both are exactly one JSON object
in the first positional argument of Evennia's transport triple, with no kwargs.

| Message | Exact top-level fields |
|---|---|
| `ui_snapshot` | `protocol_version`, `presentation_epoch`, `revision`, `mode`, `panels`, `layout_version`, `server_time` |
| `ui_update` | the same seven fields plus `base_revision` and `removed_panels` |

`protocol_version` is integer `1`. `presentation_epoch` is exactly 22 URL-safe
ASCII characters generated from 128 random bits and changes with every
transport/puppet sequence. Revisions are positive JavaScript-safe integers
excluding booleans. `mode` is one of `creation`, `exploration`, `combat`,
`dialogue`, recomputed at publication time. `layout_version` is within
`1..65,535`. `server_time` carries the exact calendar fields
(`year`, `season_index`, `season_label`, `day_in_season`, `hour`, `minute`,
`second`).

### Snapshot

A snapshot renders the complete current eager panel set and never carries an
on-demand map body. It atomically replaces eager membership (every prior eager
name omitted from `panels` disappears), preserves same-epoch on-demand maps,
and clears every map on a new epoch. Only a valid live-sequence snapshot can
establish initial state or repair a mismatch.

### Delta

A delta names the exact committed baseline and its explicit removals:

- `base_revision` is a safe integer `>= 1` and strictly older than `revision`.
- `panels` may be empty; each included value is a complete registered
  replacement (including the common `available: false` form). Omitted names
  are unchanged.
- `removed_panels` is a duplicate-free array of at most 32 registered *eager*
  panel names, disjoint from the keys of `panels` and never naming an
  on-demand map panel. Removing an already absent eager name is idempotent.
  An absent replacement never implies a removal.

A delta with empty `panels` and `removed_panels` is valid: complete metadata
alone is a meaningful publication. Identical metadata with an empty body never
originates server-side, but it is schema-valid for a receiver.

Comparison is structural: dictionaries are unordered, arrays keep their order,
and JSON numbers share one number type (`1` and `1.0` compare equal while
`true` and `1` differ). No content hash, canonical digest, or serialized
comparison of the whole presentation exists on the wire.

### On-demand maps

`area_map` and `world_map` travel only on `ui_update`. They follow the same
exact-base rule: a specialized map transfer repeats the same `base_revision`
and `revision` on every part of its bounded body transfer, no partial map
advances the committed revision, and only the complete, validated map commits.
Consecutive logical map publications have consecutive baselines; an eager delta
before a map uses its own revision and the next map builds on that revision.
A general part frame never embeds a specialized map-body part.

### General publication parts

An eager `ui_snapshot`/`ui_update` whose canonical document does not fit its
intact envelope allowance travels as one bounded transfer of
`ui_publication_part` frames. The sender is
`web/webclient/presentation/publication_parts.py`; the shared limits are
declared there and mirrored in
`web/static/webclient/js/elosern/protocol/constants.js`. The browser assembler
`web/static/webclient/js/elosern/protocol/publication_parts.js` consumes a
transfer invisibly and the reducer adopts the complete logical document once.

Each part is exactly one JSON object in the first positional argument and
carries:

| Field | Meaning |
|---|---|
| `protocol_version` | integer `1` |
| `presentation_epoch` | the logical document's 22-character epoch |
| `revision` | the logical document's target revision |
| `base_revision` | the delta's exact base; required for `delta`, forbidden for `snapshot` |
| `publication_kind` | exactly `snapshot` or `delta` |
| `transfer_id` | 32 lowercase hex characters from 128 random bits per logical publication |
| `part_index` | zero-based index inside the transfer |
| `part_count` | `ceil(total_bytes / 24,576)` |
| `total_bytes` | canonical UTF-8 JSON byte length of the logical document |
| `chunks` | 1..16 standard padded RFC 4648 base64 strings |

Every part of a transfer repeats the same epoch, revision, kind, transfer id,
count, total and (for a delta) base; no part carries `mode`, `panels` or time
fields. The reassembled bytes must decode once as strict UTF-8 and the
resulting document must match those headers and the kind's logical schema
before adoption. No checksum field exists.

The authoritative shared table:

| Resource | Limit |
|---|---|
| Logical publication (canonical UTF-8 JSON, before fragmentation) | 16,777,216 bytes |
| Raw bytes per part | 24,576 |
| Raw bytes per base64 chunk | 1,536 (2,048 ASCII characters) |
| Chunks per part | 16 |
| Parts per transfer | 683 = `ceil(16,777,216 / 24,576)` |
| Live general assembly per transport | 1 |
| Assembly lifetime from the first accepted part | 30,000 ms |

The first five are enforced here; the last two are receiver policy declared
here and enforced by the browser assembler. At the maximum, the final part is
16,384 raw bytes in 11 chunks (ten 1,536-byte chunks and one 1,024-byte chunk).
Chunk base64 must be canonical: whitespace, alternate padding and non-standard
encodings reject, and no string may exceed the generic 2,048-character limit.

Encoding rules:

- The logical document is validated once (global JSON safety measured from the
  logical root, the exact envelope schema, registered panel schemas and their
  local byte limits) and its canonical bytes are produced once, then reused for
  sizing and splitting.
- If the existing intact check accepts the document — including the
  dialogue-carrying allowance of 98,304 whole / 24,576 dialogue / 65,536
  dialogue-removed bytes — it is sent unchanged under `ui_snapshot`/`ui_update`.
- Otherwise only a schema-valid document within the 16,777,216-byte logical
  ceiling is split. The 65,536-byte generic frame ceiling is never raised, and
  logical validation never reapplies that ceiling to the reassembled document.
  The dialogue allowance never becomes a logical aggregate cap, while the
  24,576-byte dialogue panel limit still applies after assembly.
- Every part envelope is checked against the unchanged generic frame ceiling.
  A UTF-8 code point may straddle a part boundary; the receiver concatenates
  raw bytes before decoding.
- A publication above the logical ceiling, a panel that violates its schema or
  local byte limit, or an impossible part shape fails preflight: no frame from
  that batch is sent, no revision is consumed, and nothing is truncated.
- On-demand map bodies keep their specialized protocol (intact world map under
  its scoped allowance, area map as bounded `ui_update` parts); a general part
  never wraps them.

### Receiver assembly

`protocol/store.js` routes `ui_publication_part` to one general assembler per
transport, independently of `protocol/map_parts.js` (the specialized map
transfer keeps its own buffers, bounds and lifecycle). Nothing a transfer
carries becomes visible until:

1. the frame is a transport-generation- and epoch-eligible part with the exact
   nine-field shape (plus `base_revision` for a delta only), the generic frame
   bounds and canonical base64 chunks of the derived sizes;
2. the live transfer holds indices `0..N-1` exactly once, with identical
   epoch/revision/kind/transfer/count/total (and base), in order;
3. the reassembled bytes decode once as strict UTF-8 JSON;
4. the logical document validates from its root — global JSON-safety limits,
   the kind's exact envelope schema, every panel-local bound and the
   24,576-byte dialogue panel cap — matching its headers and never reapplying
   the 65,536-byte frame ceiling; and
5. final baseline admission succeeds (active epoch, newer target, and for a
   delta `base_revision === committed revision` at adoption).

Pending parts return `{accepted: false, pending: true}` and change no
presentation, metadata, revision, subscriber notification, mutation gate or
recovery signal. Only the final admission triggers the one staged commit and
notification.

One transfer is live per transport (`<=16 MiB`, `<=683` parts) with a fixed
30,000ms deadline from its first accepted part; later traffic never extends
it, and a missing final part fails once without requiring another frame.
Disconnect, a new transport generation, no-puppet detach, supersession and
expiry release the buffers and cancel the timer. A newer same-epoch snapshot
may supersede an incomplete lower-target transfer at part 0 (or arrive intact
and prune it); a stale or malformed publication never destroys the last
complete presentation. A delta arriving while an earlier general publication
remains incomplete — as parts or intact — abandons that transfer and signals
recovery instead of committing out of order.

An assembly failure (timeout, contradiction, invalid body, or a logical
document that fails validation) records the client's one recovery episode (see
"Bounded complete recovery" below) and keeps graphical mutations locked. A
valid complete snapshot clears that episode; a delta neither clears nor
bypasses it. On-demand map assembly is unaffected except that a completed
general snapshot prunes a map transfer whose target is already committed and
retains same-epoch complete maps.

## Bounded complete recovery

The browser reducer (`web/static/webclient/js/elosern/protocol/store.js`) owns
one recovery episode per transport generation:

| State | Meaning |
|---|---|
| `idle` | No failure is outstanding; normal gates apply |
| `needed` | One failure is recorded and the single automatic request is owed |
| `requested` | That one `ui_sync` left the client; the repair is in flight |
| `failed` | The one attempt did not land; terminal for this generation |

Every failure source records the same episode rather than a second one: an
exact-base mismatch, an invalid or incomplete publication, an assembly failure
or expiry, a transport-corrupted frame, a recoverable `ui_protocol_error`, and
(from the app) a matching action result claiming a revision the client never
adopted. A failure never erases panels. Every state keeps the last complete
presentation and its revision exactly as committed and locks graphical
mutations; text play is never gated. A failure recorded while `requested` makes
the episode `failed` (the repair itself did not arrive intact), so a repeated
malformed payload can never start a second automatic sync.

`requestPresentationSync(mode)` in `web/webclient-app/stores/elosern/transport.js`
is the single coalescing gate; `bridge.js`'s `requestResync` (automatic),
`client.sync` (the player's explicit synchronize), the reconnect lifecycle and
the reducer's own state drive it. Modes:

| Mode | `idle` | `needed` | `requested` | `failed` |
|---|---|---|---|---|
| `auto` (renderer / view) | records a need, then requests | requests | coalesces | refuses |
| `lifecycle` (reconnect deferral) | plain sync, no episode | requests | coalesces | refuses |
| `manual` (player) | plain sync, no episode | requests | coalesces | **one** further attempt |

A disconnected or incompatible-protocol sequence never sends: the need is
recorded and the reconnect's own initial-sync lifecycle (a fresh generation)
owns the next request. A synchronous send failure makes the episode `failed`
instead of waiting out a deadline nothing will answer.

The repair has two independent bounds. The client's response deadline is
30,000 ms from `sendSync` (`web/webclient-app/transport.js`, cancelled by any
commit, failure, reset or disconnect that ends the episode); a part-assembled
repair additionally carries its own 30,000 ms first-part deadline. Expiry of
either while `requested` fails the episode and releases the abandoned
transfer's timers and buffers.

The episode ends through a valid, newer live-sequence complete snapshot (the
repair the client asked for, which replaces the whole eager store), through the
adopted revision when the claim was a single unadopted publication, through the
player's own explicit synchronize (one further attempt), or through a new
transport generation. Nothing the client receives re-arms a failed episode and
no mutation is ever resubmitted; a publication that cannot be planned inside
the logical policy is never truncated, it simply leaves the repair failed.

### Action-result revision safety

Publication order means a matching `ui_action_result` may only name the
revision its presentation committed. A result naming a newer revision than the
committed one is recorded once (message/data deduplication) but can never
release the in-flight mutation: it implies a publication this client did not
adopt, so it starts the one complete repair and keeps the lock until the
claimed revision, or a complete snapshot, is adopted. A result at or below the
committed revision satisfies the matched action under the existing
request/epoch checks and never changes committed metadata or panels; busy and
foreign results unlock nothing.

### Server safe failures

A preflight or send failure never claims a revision that was not synchronized.
A result-only safe answer (`_publish_now`'s `result_only` path) claims
`held_revision` — the last fully installed baseline revision, or 0 before any
publication — never the issued target an invalidated baseline still reports. A
failed completion publication additionally emits one `presentation_unavailable`
protocol error (no revision, no reload demand) before that single bounded
answer, so the client marks its presentation unavailable and asks for one
complete repair. An explicit `ui_sync` whose complete snapshot violates the
publication policy (schema or the 16,777,216-byte logical ceiling) answers with
the same safe `presentation_unavailable` and stops: nothing is truncated and no
retry loop starts.

## Admission

The browser reducer (`protocol/store.js`) admits a delta only for the live
transport generation and epoch:

1. Reject a prior transport generation, an unknown message name, a missing
   envelope, a retired epoch, and a different active epoch before any staging.
2. Reject a delta while the store is `idle`, `awaiting_initial_snapshot`, or
   `detached`: a delta cannot establish an epoch.
3. Reject `revision <= committed revision` as `not_newer`.
4. Require `base_revision === committed revision`; otherwise return
   `{accepted: false, reason: "base_mismatch"}` and lock mutations until a
   recovery snapshot commits. Rejected or malformed data never advances the
   revision, mode, maps, or server time.
5. Stage every replacement, removal, and metadata field, validate the staged
   mode/dialogue relationship, then commit once and notify subscribers once.
   A partial map assembly returns `{accepted: false, pending: true}` and never
   invokes the accepted-presentation callbacks.

Malformed envelopes keep the existing `invalid` / `missing_envelope` reasons.

## Dialogue coupling

Dialogue is a candidate dependency, not an unconditional transmission. Whenever
the recomputed mode is `dialogue`, the server includes a freshly rendered
dialogue panel among its candidates; on a mode transition into or out of
dialogue it includes dialogue and the other declared mode-dependent panels.
Equal dialogue content may be omitted from the wire, so the receiver validates
the relationship against the **staged** state: a delta whose staged mode is
`dialogue` must leave a committed `dialogue` panel, and removing the committed
dialogue panel while remaining in dialogue is rejected. Snapshot behavior stays
complete.

## Producer rules

`PresentationCoordinator` emits `base_revision` and `removed_panels` on every
delta and prevalidates each frame against both the frame bounds and the delta
schema before a revision is consumed. A coordinator with no committed baseline
(`revision == 0`) cannot form a delta at all, so its first publication is the
complete snapshot; the mutation API still rejects an empty publication that
names neither a replacement nor a removal. Server-selected removals are
explicit: a planner passes `removed_panels`; an absent candidate never implies
a removal.

Every eager logical publication is prepared through
`presentation.publication_parts.encode_publication`, which validates the whole
logical document (including each transmitted panel through its registered
validator, so a supplied candidate cannot bypass its schema) and returns either
one intact frame or the complete tuple of bounded part frames before the first
send. A batch that mixes an eager publication with specialized map plans is
fully planned and validated before any of its frames leaves.

## Publication baseline and the one owner

Each live session sequence keeps **one** isolated ephemeral baseline: the epoch,
the revision the client can hold, the owned eager panel values it was last
given, and the mode, layout version and server time published with them.
Nothing is persisted, and no second store exists — every publisher (graphical
action completion and the stale/internal recovery paths, explicit
`ui_sync`/login/reconnect/puppet sync, text-command settlement, art completion,
the party/dialogue/lore-codex pushes, the action-options and title-ballot
generations, the scene-activation and dream refreshes, and the on-demand map
request) hands the same coordinator an intent:

```python
coordinator.enqueue_publication(
    context_factory,            # rebuilds the canonical read context at drain time
    *,
    affected_panels=None,       # absent/empty/invalid ⇒ unknown eager scope
    candidate_panels=None,      # already-rendered push payloads (isolated here)
    removed_panels=(),
    force_snapshot=False,
    expected_epoch=None,
    completion=None,            # dispatcher-owned result published with the batch
)  # -> Deferred[PublicationReceipt | None]
```

The call always returns a `Deferred`, including work that is rejected
immediately. It resolves with a `PublicationReceipt(epoch, revision, kind,
published)` after the whole batch — every presentation frame and, when present,
the matching action result — has been sent; `kind` is `snapshot`, `delta` or
`unchanged`, and `published` is `False` for an unchanged publication. A sequence
that retires before its intent executes resolves `None`. Preflight or send
failures errback with the real error (`PresentationQueueFull` for the bounded
intent queue, `ResultDeliveryError` when only the action result failed after a
complete publication); a guarded push logs and resolves `None` instead of
raising into its async caller.

### What is transmitted

- Candidates are compared against the committed baseline value with JSON value
  semantics: object key order is irrelevant, array order is significant,
  `true`/`1` differ, `1`/`1.0` are equal. Only unequal (or previously absent)
  panels are transmitted; an unchanged panel costs no bytes and no copy.
- An absent, empty or invalid `affected_panels` declaration is *unknown scope*:
  every eager panel is re-rendered and only real differences are sent. On-demand
  map panels are never rendered by that path.
- A mode transition recomputes every eager panel, so mode-dependent payloads
  (dialogue above all) are compared together and the staged mode/dialogue pair
  can never diverge. In dialogue mode a fresh dialogue render is always a
  candidate; it is still omitted when its content is unchanged.
- A changed common-metadata field alone (mode, layout version, server time) is
  one metadata-only delta with empty `panels` and `removed_panels`.
- A snapshot checkpoint (`force_snapshot`, the first publication, a recovery
  outcome, or a repaired sequence) renders all eager panels and consumes one
  revision even when the content equals the baseline.
- Adopted values are owned plain-JSON copies made **before** the first send, so
  a presenter that reuses a mutable container can never change what was
  published; unchanged baseline values are kept by reference.

### Serialized batches, revisions and failure

One synchronous publication critical section sends a prepared batch, with no
await between frames, so no reentrant sync or push can appear between an
action's presentation frames and its result. Public enqueues run at the existing
serialized publication boundary; reentrant work joins the same queue and drains
immediately after the current batch, in order. The boundary is described under
"Causal publication groups" below: every queued entry waits for the reactor's
next turn, except the dispatcher's result-only retirement flush. At most 64
group entries and 64 waiting callers may be pending for one sequence.

Planning reserves the next target revision without consuming it: all frames and
the action-result envelope are validated first, so a preflight failure sends no
presentation bytes and consumes no revision. The issued revision advances at the
first attempted send, so an escaped target is never reused; the baseline is
installed only after a logical publication's frames all succeeded. A send
failure after a frame escaped keeps the values for diagnostics but marks the
baseline invalid and requires a fresh snapshot at a later revision before any
delta. A failure of the action result alone (after a complete presentation)
leaves the baseline valid and published.

Map plans keep their specialized delivery: an eager companion delta, then one
logical publication per requested map with consecutive baselines, a world map
intact under its scoped allowance and an area map as bounded parts that repeat
the same `base_revision`/`revision`. Every frame of every logical publication is
prevalidated before any is sent, and an on-demand body never enters the eager
baseline.

## Causal publication groups

One committed deterministic operation can produce several presentation effects:
an ordinary panel push from an on-commit callback, a checkpoint fact from a
movement/terminal/skip owner, and the fan-out to every watcher session. They
share one ephemeral **causal publication group** so each watcher receives one
final publication for that commit instead of a delta followed by a correction.
`world/rules/presentation_events.py` is the whole API; nothing is persisted, no
group identity is serialized, and no second publication owner exists.

### Group lifetime and capture

| Entry | Contract |
|---|---|
| `new_publication_group()` | A fresh `PublicationGroup` with a unique 32-hex ephemeral id. |
| `publication_group(group=None)` | Binds the group (or a new one) for one synchronous scope. A nested scope **reuses** the active group, so nested on-commit callbacks keep one identity. The binding is closed and reset in `finally`, before the callable returns, and is never active while an external operation is pending. |
| `current_publication_group()` | The live binding, or `None`. Twisted's `@inlineCallbacks` copies the context at generator start, so a resumed generator still *references* the binding object; because the binding is closed when its synchronous owner returned, resumption reports `None` and can never revive an already-published group. Resumed deterministic work opens its own scope. |
| `on_publication_commit(callback, *, using=None)` | Registers on Django's `transaction.on_commit` while capturing the group active at registration time, and rebinds **exactly** that group for the callback's synchronous execution — even when another group is bound at commit time (an outer transaction committing inside another committed operation). A rolled-back transaction registers and runs nothing; callback exceptions keep Django's existing behaviour. |

A group is captured at the `enqueue_publication` call boundary (explicit
`group_id`, else the live binding, else a fresh standalone group). A group-less
publisher therefore gets its own group and is never attached heuristically to a
pending action. `independent=True` marks an explicit entry (a `ui_sync`, a text
refresh, a recovery answer) that must never join an ambient command group.

### Queue shape and drain boundary

The coordinator keeps **one pending entry per group id**, in first-enqueue
order. Within an entry the declarations merge:

- candidate names and a declared eager scope are unioned; any request that
  declares unknown scope widens the whole entry to "compare every eager panel";
- explicit removals are unioned and win over a replacement of the same name;
- a checkpoint promotion (`force_snapshot`, a committed alignment fact) wins,
  so the entry publishes one fresh complete snapshot and no intermediate delta;
- a completion's context factory (which carries the action-local round record)
  survives later ordinary pushes; otherwise the newest factory wins, and every
  grouped factory rebuilds current canonical state.

**Every** queued entry drains at the reactor's next turn: all on-commit
callbacks of the synchronous operations that queued them have run by then, so
each entry is complete before it is planned and sent. First-enqueue order is
therefore publication order — a later text refresh or explicit sync can never
overtake an earlier committed operation, and an earlier entry is never finalized
by unrelated later work. `ui_sync`, a text refresh, an async generation
completion and a dispatcher recovery answer are still their **own** entries
(`independent=True`); they simply queue at the same boundary. Two narrow
exceptions keep B's ordering guarantees:

- the dispatcher's **result-only** completion (the sequence-retiring actions)
  flushes just its own group before returning, because its adapter may already
  have scheduled the retirement for the next turn;
- explicit `ui_sync` remains an independent forced-snapshot entry and may run
  while any number of domain Deferreds are pending, but it never interleaves a
  prepared presentation/result batch.

A process without a running reactor (the test runner, a one-off command) has no
live transport to observe frames, so the injected scheduler publishes at the
enqueue boundary there; tests inject a queued scheduler to exercise the
production boundary deterministically.

### Checkpoint facts

`PresentationAlignmentFact(group_id, actor_id, cause, source, destination)`
carries a committed checkpoint for one actor (`movement_boundary`,
`combat_terminal`, `skip_completed`) and `AlignmentIdentity`/`emit_alignment_fact`
are fully functional value and observer APIs with no no-op fallback. The
registered observer (`web/webclient/presentation/alignment.py`, connected at
`at_server_start`) forwards each fact to every lawful watcher of the actor as a
forced-snapshot intent under the fact's group id: it merges with that group's
ordinary push whether the fact callback ran before or after it, needs no
initiating session, and is a no-op for a fact with no live watcher. M owns the
movement identity reader/first producer; S owns the terminal/skip producers. A
later options/art generation completion forms a new standalone group and is
never suppressed by an earlier one.

### Outcomes and bounds

Every public queueing entry returns `Deferred[PublicationReceipt | None]`. All
waiters of one group resolve with the **same** actual receipt after every frame
and the attached result have sent; a retired sequence resolves `None` for all of
them; preflight, send and overflow failures errback every waiter with the real
error (`PresentationQueueFull` for the bound). Completed group metadata is
removed before its waiters resolve, so no history grows, and `reset`/detach
clear pending groups. The bound is 64 pending group entries and 64 waiting
callers, with result-only answers exempt; exceeding it invalidates the baseline
and answers explicitly. The guarded helpers (`publish_panel_update`,
`refresh_after_command`, `synchronize_session`) are terminal consumers: they log
a published failure, never raise into an async caller, and now also resolve the
actual receipt on success.

A one-shot delivery notice that the wire contract forbids inside a snapshot (a
claimed dialogue `unlock_batch`) publishes as its own **independent** entry, so
a later checkpoint promotion can never consume and drop it.

## Fixtures

Test fixtures derive each delta's `base_revision` from that fixture's actual
last committed revision, never by assuming `revision - 1` across a skipped
publication. Scenarios that follow an abandoned, never-committed transfer, or
that skip integers, supply the baseline explicitly. A synthetic session that
publishes a delta first establishes a committed baseline snapshot, exactly as a
live transport does. There is no validator fallback for a missing
`base_revision` or `removed_panels`.
