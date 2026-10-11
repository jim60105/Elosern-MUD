# Confirmed Dream Requests to Executable Story Scenes

Date: 2026-10-11

Status: Conversation design approved; written review pending.

## 1. Purpose and approved decisions

Connect confirmed dream directions to production background generation and real
scene publication. A confirmed request must not stop at persistence or a private
narrative statement when the player asked for characters and executable actions.

This is the third sequential design. It consumes
[quest scene encounters and persistent NPCs](2026-10-11-quest-scene-encounters-design.md)
and [escort, party identities, and exclusive outcomes](2026-10-11-escort-rendezvous-design.md).

The end-to-end example is the exact direction
`我會在南門遇到一個女孩，她要我帶她找媽媽`, followed by dream confirmation.
The resulting arrangement must permit either mother-first or daughter-first
exploration, real conversation, distinct private escort offers, temporary party
membership, actual rendezvous, one exclusive result, and post-story everyday
dialogue with preserved character identity and memory.

Approved decisions:

- Confirmation saves the request and returns the player to waking play immediately.
  Generation begins in the background after commit, without advancing game time.
- Retain StoryDirector followed by ScenarioDirector for executable quest scenes.
  The roles may use the same configured model with separate contexts and schemas.
- Use durable request-scoped work with one running story generation in the server;
  other eligible requests queue. Do not add a generic agent or retry framework.
- Publication and NPC appearance are separate. Evaluate independent encounters
  at actual exploration boundaries and immediately after publication if the
  player is already in an eligible place.
- Provide truthful, spoiler-safe preparation, waiting, success, and failure feedback.
- Deploy against a rebuilt game database. Do not import, reconcile, migrate, or
  automatically execute requests from the previous database.

The architectural source of truth remains
[the engine design](2026-07-29-ai-mud-engine-design.md). Context and knowledge follow
[the cognition design](2026-10-03-narrative-memory-cognition-design.md).
This design wires explicitly confirmed directions, not unsolicited new stories or
an expanded automatic continuation engine.

## 2. Current root cause and affected contracts

`server/dream_service.py` confirms through
`world/narrative/dream_session.py::confirm_session()`. Authoring saves a valid
`CreativeRequest` and closes the dream. Its commit callback logs submission but
does not dispatch a director. `world/narrative/director.py::attempt_decision()` is
an implemented orchestration seam without a production scheduler.

The current beat proposal contains bounded beat kind, summary, recipient and
effects, not a complete NPC encounter blueprint. `quest_beats.py` captures an
existing participant issuer or defaults to a guild issuance context. That cannot
bootstrap a new girl's private commission. SceneBuilder and generated escort
also have the deliberate limitations addressed by designs 1 and 2.

Amend the dream scheduling, story-director, narrative-quest compilation, and
presentation contracts accordingly. Preserve owner boundaries, immutable context,
source deduplication, strict issuance, offline deterministic gameplay, and the
existing prohibition on filler replacement for a failed narrative quest beat.

## 3. Ownership and background service

| Owner | Responsibility |
| --- | --- |
| Dream/authoring deterministic lifecycle | Confirm one valid version; atomically persist the creative request and dispatch work; close the dream. |
| Server composition service | Start/stop the narrow background pump; construct configured clients; invoke generation off the confirmation response path; route committed feedback. |
| `world/narrative/` | Persist work and source identities, prepare permitted snapshots, orchestrate director decisions, revalidate and settle narrative state. |
| StoryDirector capability | Propose the bounded arrangement and required executable capabilities from permitted story context. |
| ScenarioDirector capability | Produce the extended quest scene blueprint with roles, encounters, dialogue and commissions. |
| Existing deterministic quests/rules/maps | Compile and publish packages, activate scenes, apply party/action effects, and evaluate real outcomes. |

AI modules never mutate game or work state. Keep client construction at the
server composition boundary and pass clients/snapshots into existing generation
seams. Extend or extract the current prepare/generate/settle functions where
needed; do not implement another director beside `attempt_decision()`.

Use the server reactor's background lifecycle and existing asynchronous client
machinery. No database transaction spans an LLM await. The service is started and
stopped with the Evennia server, not the portal. Only one service owns the pump
in a game server; transactionally claim individual work to prevent duplicate
callbacks from processing the same source.

## 4. Durable work and confirmation transaction

Create a narrative-owned dispatch record with database-enforced uniqueness for
creative request identity/version. Store owner, stable source key, work state,
current stage, process/execution token, snapshot/proposal references, publication
references, structured reason, and relevant game tick. Store validated generated
data, not credentials or raw unrestricted model transcripts.

The confirmed creative direction remains immutable source data. Mutable execution
state belongs to the dispatch record. A new confirmed version is a distinct
source; an identical retry of confirmation is the same source.

| State | Meaning |
| --- | --- |
| `queued` | Valid confirmed source, eligible for a future claim. |
| `generating_story` | A fenced execution is preparing or generating the story arrangement. |
| `generating_scene` | A supported scene arrangement is producing its blueprint. |
| `publishing` | Validated output is ready for deterministic revalidation and atomic publication. |
| `waiting_service` | A required configured capability is absent or disabled before dispatch; no substitute content exists. |
| `arranged` | The validated executable arrangement or other legitimately supported requested effect has committed. |
| `failed` | A bounded generation/validation or execution failure has a recorded reason; no success is claimed. |

In one confirmation transaction, save the exact valid request, create/get its
unique work record, close the session as confirmed, and preserve source linkage.
Notify the pump after commit, without waiting for generation. A notification is
only a wake-up hint; the database work record is authoritative.

Service startup resumes its existing nonterminal dispatch records. It does not
scan legacy creative requests to create missing work. Recover interrupted claims
under exclusive service ownership and fence the old execution token before
resuming. Do not use lease expiry to race a still-running model request.

Persist successful stage outputs before proceeding. After a crash, reuse saved
valid output when its relevant snapshot still validates; otherwise reject or
regenerate only an uncommitted interrupted stage under the same source identity.
Never generate another package when the source already has a committed result.

Queue eligible work in stable confirmation order. A request waiting for a disabled
capability does not prevent other eligible work from running. Configuration
activation/reload, server startup, or another pump notification can reconsider
waiting work; no infinite reachability polling or independent retry subsystem is
introduced.

## 5. Director context and executable proposal contract

Prepare an immutable, provenance-bearing snapshot from the confirmed direction,
permitted history, existing story linkage, relevant world constraints and bounded
locator/actor references. Preserve requested experience requirements in validated
structured planning data alongside the original summary. A generated interpretation
cannot erase an explicit named place, required new character, or requested private
commission merely to obtain an easier valid proposal.

Extend the dream collaborator's draft contract to propose these bounded
requirements before confirmation and include their readable meaning in the
existing draft presentation. Confirmation freezes the shown requirements together
with the direction. Deterministic completeness checks enforce those explicit
fields; they do not claim to prove arbitrary natural-language intent from a late,
hidden interpretation.

StoryDirector classifies and arranges the request. Keep the existing bounded beat
families; a quest-scene arrangement uses the quest-seed route with explicit scene
requirements rather than an unrestricted `spawn_npc` effect. ScenarioDirector
receives only the permitted immutable planning data needed to produce the first
two designs' package schema. Shared deployment profiles do not share histories or
private knowledge.

Extend quest-beat context and compilation to carry validated symbolic scene roles
and issuer declarations. New roles are not existing authorized participants or
guild branches. Planning validation uses role references; materialization and
commission registration perform the strict actual-entity checks from design 1.
Do not silently route a private commission to a guild or require guild rank.

The complete blueprint contains independent encounters, reusable role definitions,
initial knowledge/relationships, complete phase dialogue, actual locator references,
distinct commissions, protected-role references, explicit escort completion modes,
and declared exclusive outcome groups as needed. Mechanical values stay
registry-derived. Generated code, arbitrary predicates and authority claims remain
forbidden.

Validate that the proposed capabilities actually satisfy the confirmed request.
For the motivating direction, a private narrative statement, letter, clue summary,
or unregistered quest key cannot substitute for executable NPC encounters and
escort commissions. Choosing no eligible arrangement is an explicit unsuccessful
result, not an `arranged` request.

Other directions may use existing supported non-scene beat effects according to
their real contracts. This work does not invent execution for unsupported wishes
or convert every dream into a quest. A textual claim about a past player action
never becomes committed world history or objective progress.

## 6. Revalidation and atomic publication

Model generation uses frozen inputs; settlement uses current authoritative state.
Revalidate source version, owner, relevant thread revisions, map references,
explicit actor identities, issuance scope and executable capability availability.
Do not reject a future south-gate encounter merely because the player moved while
the model was running. Current room is relevant only when an actual declared
condition depends on it. Conversely, changed required actors or contradictory
story facts cannot be ignored.

In one publication transaction, commit the accepted director decision, story
thread linkage, scheduled beat/result, validated scene package, and request-to-
publication identity. Lock relevant sources/threads and enforce existing
one-eligible-beat and no-conflicting-arrangement rules. Set dispatch state to
`arranged` only with those durable references present.

Preserve the current definition/registration cache rollback patterns. A publication
failure creates no orphan scene, issuer, accepted quest or partially linked beat.
Publication does not instantiate untriggered roles, accept a commission, award
progress or pay rewards.

Defer player notices and scene-refresh fan-out until commit. A missed notification
does not erase or undo publication; reconnect/startup can recover current status.
Do not set success in a callback whose result is the only evidence of publication.

## 7. Production encounter activation

Provide one deterministic encounter-eligibility/activation entry point shared by
post-publication handling and actual exploration. Consume the saved package, owner,
actual exploring actor, authoritative location and current tick. The actor may be
the player character or a lawfully possessed party member; ownership remains the
original player. Publication can finish while the player is disconnected.

Invoke it at these boundaries:

- After publication, inspect the connected owner's actual current exploration
  position and activate eligible encounters there without requiring re-entry.
- On settled room entry or wilderness-coordinate travel, check relevant pending
  encounters indexed by locator and owner.
- On reconnect, synchronize status and evaluate the actual current position.
- After service startup, synchronize connected owners' pending encounters at
  their current positions, including committed publications whose fan-out was lost.
- On declared deterministic prerequisite changes, reevaluate the affected
  encounters, not every unrelated scene.

Use finite registered conditions and validated locator references. Reuse the
existing movement/visibility/control contracts. Do not install an arbitrary event
bus or let the model supply subscriptions or condition expressions.

For a traversal that can materialize a meeting role, settle actual movement and
followers, activate eligible scene roles transactionally, then run the shared
escort/outcome evaluator on the resulting position. Preserve one transition per
source and deduplicate the encounter. NPC movement already covered by design 2
reaches the same rendezvous evaluator; unrelated NPC roaming does not activate
all of a player's future encounters.

The two motivating encounters are independent. Mother-first remains possible
before any acceptance or daughter encounter. Already materialized actors remain
at their actual positions with their identities, current dialogue phases and
memories; no repeat spawn or return-to-origin teleport occurs.

After activation commits, refresh the existing room occupant/affordance and NPC
conversation projections. Actual visibility/access gates still apply. An
arrangement notice cannot present unmaterialized roles as current occupants.

## 8. Player feedback and knowledge boundaries

Use ordinary game output and existing scene/conversation updates, not a new story
control panel or action-option system. Confirmation gives a truthful receipt.
Preparation, service waiting, arrangement and failure have distinct player-facing
Traditional Chinese messages. Arrangement reports that the direction has an
executable arrangement without leaking future identities, hidden locations or
plot outcomes.

An activation can report an actually visible new encounter and update its real
interaction targets. Model failure, missing capability, invalid place, stale
required fact and unavailable actor use distinct actionable reasons. Never show
an arranged/successful state because a model returned readable prose.

Feedback uses the saved owner and current legal session/control mapping, not a
stale actor captured before generation. If offline, retain current work state;
reconnect supplies its latest status and authoritative scene. Do not promise
exactly-once notification delivery; committed effects are exactly-once even when
an ordinary status notice must be repeated after reconnect.

Creative discussions, job status, future plans and private director snapshots are
not NPC memories. Materialization initializes only role-permitted background
knowledge with provenance. Conversation, information transfer, reunion and
closure project later knowledge through existing narrative APIs. Adding a live
NPC to story participation cannot grant it the owner's private draft or all
planning facts.

## 9. Failure and offline behavior

Check capability configuration before claiming a model stage. Disabled services
leave work waiting with no fake NPC, quest or template substitution. Use existing
client timeouts and bounded transport/schema validation retries. Exhaustion,
misfit or unsupported requested effects produce a durable failed reason and no
partial publication. Do not automatically retry terminal director failures under
a new hidden source identity.

A failed direction remains saved. The player may confirm a new version through
the normal dream lifecycle. Interrupted uncommitted execution recovery is distinct
from repeatedly rerolling a terminally rejected direction.

A stale execution token/version cannot deliver a result, mutate state, append an
obsolete dialogue exchange, or change dispatch success. Shutdown cancels further
claims and invalidates unfinished callback ownership; saved checkpoints govern
restart.

Generation and work management never advance the game clock. Existing offline
quests and deterministic mechanics remain playable. A published encounter,
scripted conversation, escort, possession and settlement do not require a live
model; only optional free-form conversation depends on it.

Operational events use the observability facade, stable English identifiers and
context for request/version, owner, work/stage, process token, decision, thread,
package, scene, tick and call ID where present. Preserve credential filtering,
exception reporting and transcript rules. Log confirmation handoff, claims,
waiting/failure, publication, recovered execution and actual activation.

## 10. Fresh-database deployment

The user explicitly chose to discard the previous game database. Implementation
and deployment therefore target a rebuilt database and normal idempotent authored
startup synchronization. No legacy-request scanner, data migration, compatibility
parser or historical request reconciliation belongs in these changes.

This document records the destructive deployment requirement; writing it does
not authorize deletion during brainstorming or implement the reset. When the
approved implementation reaches deployment, stop the game server, remove only
the configured game database files in its database volume, recreate the current
schema through the supported Evennia/uv workflow, and run normal initialization.
Identify the actual configured database and its SQLite sidecars before removal;
do not wipe an entire volume or execute a guessed path.

Preserve logs, LLM transcripts, static/media assets, generated art, credentials,
external service configuration, and unrelated mounts. Rebuild the image/source
bundle through the normal container workflow when deploying changed code. No
raw domain patching through a Django shell is used to fabricate acceptance.

## 11. End-to-end acceptance and verification

Use a fresh test database, deterministic synthetic content and fixed generation
outputs at the model boundary. The production dispatch service, director context
validation, compiler, SceneBuilder, party, combat/possession, quest and settlement
owners must execute normally. Tests may not echo a fabricated success message in
place of those effects.

1. Enter the motivating direction and confirm using the real dream surface.
   Observe a confirmed immutable request plus one dispatch record, immediate
   waking response, background StoryDirector/ScenarioDirector calls and no clock
   charge from generation.
2. Publish a validated package while the player remains at the south gate.
   Observe one actual daughter with current greeting/topic choices and a valid
   private offer, without exit/re-entry or guild membership.
3. Exercise mother-first and daughter-first entry, normal and possessed
   exploration, and unrelated player movement during generation. Preserve actor
   identity, correct owner and independent encounter eligibility.
4. Accept either distinct escort offer through the actual conversation window.
   Move/possess the protected actor, rendezvous at different legitimate locations,
   resolve one exclusive result, invalidate the alternative, settle exactly one
   reward and reopen everyday dialogue with earlier memory retained.
5. Crash/restart at saved story output, saved blueprint, pre-publication and
   post-commit/pre-notification boundaries. Observe recovery under one source and
   no duplicate thread/beat/package/NPC/offer or reward.
6. Submit duplicate confirmation and late callbacks from invalidated executions.
   They cannot duplicate work or alter committed publication and history.
7. Disable required profiles, return malformed/misfitting output, change a required
   identity and fail after publication writes. Observe distinct durable reasons,
   no filler, no partial game effects and correct cache/session compensation.
8. Finish generation while disconnected and reconnect at an eligible position.
   Synchronize latest work state and actual encounter, with no private future
   facts exposed in notices or NPC dialogue.
9. Disable model services after publication. Complete scripted conversation,
   escort, combat/possession and reward paths using deterministic mechanics.
10. Supply a readable narrative-only proposal for a request requiring real roles.
    Reject it as insufficient rather than marking the request arranged.

For implementation handoff, run focused dream, authoring, director, publication,
scene and affected presentation tests, relevant observability/data lints, shard
ownership contracts and the mandatory contract gate. Trace amended main-spec
requirements substantively. Use one scoped runtime smoke through real confirmation,
background dispatch, construction, conversation, acceptance, movement, resolution,
payment and committed reload. No full browser suite or live network model is
required for automated proof.

## 12. Completion boundary

The three designs are complete only when the whole requested experience is
executable. A wired model callback, accepted JSON, private event, or generated
quest without real encounters is insufficient.

Implement the scene/role/dialogue contracts first, followed by the
escort/party/outcome contracts, then production request dispatch and exploration
activation. Retain forward guards until their owner implementations and
end-to-end proof exist.
No arbitrary LLM action program, new autonomous NPC framework, unsolicited story
scheduler or unrelated refactor is introduced.
