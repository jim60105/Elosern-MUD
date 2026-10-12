# Design

## Context

See proposal.md for motivation, exact capabilities, batch conflicts and the sizing exception. The entire approved dispatch design is authoritative, especially sections 3 through 11. The engine design sections 3, 7 and 11 preserve deterministic ownership and deterministic-before-generative ordering. Upstream proposals are planning interfaces today; apply waits for their executable implementations and proof.

Observed `server/dream_service.py::act()` confirms inside a transaction and returns an ending immediately. `director.py::attempt_decision()` already resolves/deduplicates sources, prepares an immutable invocation, generates StoryDirector output, optionally generates a blueprint, and settles it. It currently builds a missing scenario client from inside the orchestration path. `quest_beats.py::quest_context()` requires an actual participant issuer or the owner's registered guild branch and captures current-room anchor; publication compares all that captured context. Neither behavior can support a new symbolic private issuer or unrelated movement during future encounter generation. Server startup registers director layers, but server stop currently has no dispatch lifecycle.

## Goals / Non-Goals

Keep confirmed source immutable and execution recoverable under narrative ownership. Use the existing director orchestration, asynchronous clients, validated proposal pipeline and upstream deterministic operations. Production activation must reach real conversation/escort/outcome consumers before exposing generated execution. There is no second director, generic worker framework, uncontrolled predicate language or broad event bus. No upstream artifacts or implementations are required to change during this proposal run.

## Decisions

### Durable narrow work and atomic confirmation

Add a narrative ORM dispatch record with a database uniqueness constraint on creative-request/version plus stable owner/source linkage. Persist state, stage, service process/execution fence, snapshot and validated proposal references, publication references, reason and tick. Use the existing models/schema initialization conventions for current tables/constraints; no deployed-data conversion or reconciliation. Database uniqueness, not a list scan, supplies identity across restart. The confirmed request is never used as mutable work state.

Extend authoring's closed direction contract and dream collaborator output with bounded explicit experience requirements before confirmation. Resolve place references deterministically and present their readable meaning alongside the draft; a requirement cannot silently disappear to fit an easier proposal. The summary is retained unchanged as source prose. Summary changes require the corresponding requirement version to be reviewed; absent or stale review refuses confirmation while leaving draft/awakening available offline. The implementation must cut over dream server/client validators and consumers together, with no old shape adapter.

The shared draft/confirm direction shape adds `requirements` and `requirement_version` alongside kind/thread_id/summary and existing preferences. Requirements are bounded plain structured planning data; the bounded version identity identifies the shown persisted draft/version. Unreviewed draft preservation accepts empty requirements and a null version identity. Confirmation compares the submitted requirements and identity with the persisted shown valid version deterministically; it never asks a model to approve an already-shown version. Replace the existing sheet payload and edited-summary confirmation scenarios explicitly, preserving all other sheet behavior.

Within confirmation's outer transaction save the validated version, create/get work, close the session and preserve source linkage. Rollback includes Attribute/surface state where touched. `on_commit` only notifies the service, never owns source identity or arrangement evidence. Waking returns without model await and without another sleep/game-clock settlement. Every confirmation entry path, including direct authoring confirmation, uses the same deterministic handoff; dream closure belongs to the session path rather than standalone authoring.

### Reactor lifecycle and deterministic fencing

Compose one narrow background pump at the game server boundary after director/package registrations and restoration are ready. Stop it on reload/shutdown; never install it on the portal. Server composition constructs configured clients and injects them into existing narrative prepare/generate/settle seams. Extract stage checkpoints from `attempt_decision()` as needed, preserving its source deduplication and one-beat/conflict rules; remove its internal scenario-client construction for this path.

Short transactions claim/checkpoint/settle; none spans a model await. A process fence and per-execution token must match at every output persistence and settlement. One service-owned active execution serializes model generation; database uniqueness and SQLite-compatible serialized write discipline protect work claims. Do not treat select_for_update alone as a SQLite concurrency solution. A later process can recover interrupted claims only under exclusive server ownership after invalidating the prior token, never by elapsed lease racing a live model call.

Queue by stable confirmation sequence with an identity tie-break. Check the next stage's configured capability before claiming it. Missing/disabled stages become waiting_service and do not block eligible sources. Startup, profile activation/reload and ordinary notifications reconsider waiting sources; no independent retry scheduler or reachability polling. Existing client timeout and bounded transport/schema retries remain the complete attempt budget. Terminal failures never auto-reroll. A player can confirm a new reviewed version normally.

The transition path is queued to generating_story, checkpoint to generating_scene for a supported quest scene, checkpoint to publishing, then arranged after settlement. Supported non-scene effects use the existing real owner contracts and proceed to publishing without inventing a scene stage. A missing required capability waits at its next stage with previous checkpoints intact. Unsupported/no-eligible output fails. Interrupted running states can resume their still-valid saved stage under a fresh token; stale relevant data rejects or regenerates only an uncommitted interrupted stage under the same source. Existing committed result always wins and prohibits another package.

### Two contexts and complete symbolic planning

Prepare provenance-bearing source/version, relevant thread revisions, history, constraints and bounded actor/locator references as immutable data. StoryDirector receives the confirmed shown requirements and emits existing beat families; a scene requires quest_seed with explicit scene needs. ScenarioDirector receives only the permitted planning subset, separate schema/prompt/history even when its model profile is shared. No context grants an NPC private planning data.

Extend quest-beat context to represent reusable symbolic role/issuer declarations. New roles cannot pass as existing authorized participants, and private role issuance cannot fall back to a guild or require rank. Consume the full upstream package payload including independent encounters, characterization, initial permitted knowledge/relations, complete phase dialogue, actual locator references, distinct commission IDs, protected roles, destination/rendezvous completion and explicit exclusive groups. Upstream shared validators/registries remain the contract source for both semantic validation and deterministic compilation. Generated numeric state, code, predicates and authority grants remain invalid.

Completeness compares explicit shown requirement fields with proposed executable capabilities. The motivating request cannot succeed through a letter, private event or generated unregistered key. Other wishes may use supported non-scene effects if those effects genuinely satisfy their confirmed requirements; none/no-content is an unsuccessful dispatch result. Text about past actions changes no authoritative history or objective progress.

### Current-state settlement joins upstream publication

At publishing, lock/revalidate the work/source and affected thread using the existing serialized write discipline. Check owner/version/token, required actor identity, actual locator validity, relevant thread facts/revisions, issuance scope and supported capability availability. Current position is excluded unless a declared condition depends on it. This replaces exact whole-context current-room equality for future encounter scenes without weakening relevant fact validation.

Within one outer publication transaction settle the accepted director decision, thread linkage, at most one beat/result, `publish_scene_package` result and request-publication identity, then set arranged with references. The upstream publication operation joins this transaction; its existing registration/cache rollback discipline must remain intact. Publication never activates future roles, accepts an offer, progresses a quest or rewards the player. Failure settles a durable failed reason after rollback under a still-valid work token and emits no success. Post-commit activation/notices may fail without undoing durable publication; reconnect/startup repairs projection from saved state.

### One indexed production activation entry point

A deterministic boundary consumes saved package/owner, actual lawful exploration actor, current authoritative room or wilderness provider/coordinate and tick. It calls upstream `lookup_story_role` and `activate_scene_encounter`, preserving their existing signatures and authority semantics. The caller does not supply invented observations. Use owner/locator indexes for movement/current position and declared finite registered prerequisite indexes for affected changes.

Invoke after committed publication for connected owners, after actual room entry or wilderness coordinate travel, on reconnect, on server startup for connected owners and on declared prerequisite changes. Startup also synchronizes published encounters whose fan-out was lost. Resolve current control/session mapping at invocation, including lawful possession; saved owner remains original player. Offline publication needs no actor movement or fake appearance.

For traversal, collect affected authoritative identities without consuming transition eligibility. In the owning movement transaction, settle movement and followers, activate relevant scene roles, then run the upstream consolidated `evaluate_escort_event` with the same originating source. Standalone activation uses its own owner-issued activation source/transaction and final evaluation. Use `resolve_exclusive_outcome` through its owning evaluator flow; read `exclusive_outcome_status` where status needs a durable result. Ordinary NPC movement already uses upstream rendezvous evaluation and cannot activate all future scenes. Both mother-first and daughter-first are eligible before acceptance. Bound actors remain at actual positions and phases with identity/memory unchanged.

### Existing truthful presentation and knowledge

After commit refresh existing occupant/affordance and conversation projections using existing session helpers and upstream `transition_story_dialogue` observations. Only actual visible/access-eligible NPCs reach interaction targets. Real authorized offer actions reach `accept_escort_commission`; normal terminal flows reach `release_escort_bindings`. No notice autoaccepts a quest or opens a future NPC conversation.

Ordinary Traditional Chinese output distinguishes receipt, preparation, service waiting, executable arrangement and failure with bounded actionable reasons. It discloses no future identities, private locations or outcomes. Resolve the saved owner's current legal session mapping on delivery. If offline retain work state; reconnect reads latest status and current scene. Effects are exactly-once through durable identity, while an ordinary notice can repeat.

Materialization initializes role-permitted background knowledge through narrative APIs. Conversation, information transfer and physical result observations teach only actual permitted participants. Job status, private drafts and director snapshots are never NPC memories. Upstream phase/persona staleness checks remain in force for delayed free-form replies and history append.

## Risks / Trade-offs

Cross-transaction callbacks can create duplicate or false success without durable identities. Mitigation uses source uniqueness, checkpoint persistence, fencing and after-commit projection only. SQLite write behavior requires serialized writes and fault tests rather than a row-lock assertion. Attribute/registry/session rollback must follow existing owner compensation patterns.

Context revalidation can overreject movement or underreject required facts. Record explicit relevant dependencies; test unrelated movement independently from changed actor/thread/map/authority facts. Publication and activation must remain separate transactions at the post-publication boundary, while traversal activation and final result evaluation join the originating movement transaction.

The full acceptance list exceeds a credible one-day estimate. See proposal.md's explicit 16-hour inference and suggested two-unit split. No criterion is deferred by this artifact set and no extra change is created.

## Migration Plan

No migration is planned. Target the user-approved fresh-database deployment boundary only after implementation readiness. During proposal creation do not execute, script or schedule any deletion. The later deployment operator must stop the server, identify the actual configured game database and SQLite sidecars, scope removal to those verified files, recreate current schema with supported Evennia/uv initialization and rebuild the image/source bundle through the ordinary container workflow. Preserve log/transcript/static/media/art resources, credentials, configuration and unrelated mounts. Do not wipe a volume or guess paths.

Deployment rollback must stop new claims and prevent mixed-schema operation. Restore a matching tested source/image and its matching game-database snapshot only under a separate explicit operational authorization, or reinitialize the matching fresh schema. Do not translate legacy requests or use shell domain patching to fabricate acceptance. No rollback/reset command is supplied by this proposal.

## Verification and acceptance mapping

Every approved section-11 criterion maps to real-owner tests with synthetic deterministic fixtures, fresh test database and fixed outputs solely at the model boundary. Claim/notification scheduling can use a deterministic reactor harness; the production service and director/quest/map/rules/presentation consumers run normally.

| Source acceptance | Owning behavior/assertions |
| --- | --- |
| 1 | Real dream confirmation, frozen requirements, exactly one request/work, unresolved background Deferred and immediate waking, separate recorded director contexts, unchanged generation clock |
| 2 | Publish while remaining at south gate, then real post-commit activation, exact daughter, greeting/topics and private offer without guild rank/re-entry |
| 3 | Both encounter orders, ordinary/possessed room and wilderness exploration, owner mapping, unrelated movement during generation, exact actor identity |
| 4 | Real conversation acceptance of each alternative in separate fixtures, temporary membership, actual movement/possession to multiple legitimate rendezvous positions, one exclusive result/reward, invalid alternative, everyday dialogue/memory after committed reload |
| 5 | Interruption after story, blueprint, before publication and after commit/before notification; count unchanged decision/thread/beat/package/NPC/offer/reward identities after recovery |
| 6 | Duplicate confirmation and invalidated-token/version callbacks change no work/publication/history and append no stale dialogue |
| 7 | Disabled profiles, malformed/misfitting outputs, required identity change and failure after publication writes yield distinct durable reasons, no filler/partial effects and actual cache/session compensation |
| 8 | Complete offline, reconnect at eligible controlled position, latest status/current scene without future private knowledge in notices or dialogue |
| 9 | Disable model services after publication; real scripted conversation, escort, combat/possession and reward consumers run without transport |
| 10 | Readable narrative-only output fails explicit executable requirements without arranged state |

Cover every requirement heading with substantive assertion-bearing tests. Modified requirements retain their IDs and reviewed assertions; added IDs come from `tools.spec_traceability list` against an equivalent spec tree after both upstream deltas and this delta, never manual construction. Planning changes are outside the current-contract index, so a proposal validation pass does not prove test coverage. Register new non-browser modules and any new browser methods in exact shard manifests. Local implementation proof uses focused owner/presentation tests, relevant observability/data lints, ownership contracts and mandatory contract gate; CI owns full browser/evidence verification. One scoped runtime smoke must execute real confirmation, background dispatch, construction, conversation, acceptance, movement, resolution, payment and committed reload.

All upstream/service/schema/compiler/registration forward guards remain until their owning executable flows and this production handoff proof pass. Generic offline templates and unsupported-wish refusals remain. Update development and player command documentation with the actual altered command behavior at apply; this proposal edits no such files.
