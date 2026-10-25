# Exact-base presentation contract

## Context

`web/webclient/presentation/protocol.py::_validate_common_metadata` and browser `protocol/envelope.js::validateCommonMetadata` currently share seven snapshot/update fields and require nonempty panels. `protocol/store.js::receive` gates on newer revision, clones every notification, and has a separate specialized map assembler. `coordinator.py::panel_update` injects dialogue on every dialogue-mode publication. Main specs still require full post-text refresh and unconditional next revision on admitted completion. These are observed contracts to amend, not behavior already implemented.

Read the complete approved synchronization design and the architectural source listed in proposal.md. Presenters stay read-only; deterministic owners retain game-state authority. This is the batch's shared contract. The individual designs below add concrete ownership without superseding it.

## Goals / Non-Goals

Goals are exact logical envelopes, atomic baseline admission and a complete worker handoff. This slice changes emitters and fixtures enough to use the new wire immediately, while content suppression belongs to baseline. Existing maps retain their specialized delivery and storage.

No runtime compatibility, protocol v2 branch, hash revisions, source mutation counters, replay log, acknowledgement message, periodic alignment or performance measurement. The protocol remains version 1 because this project is unreleased. Deployment waits for the full batch.

## Decisions

### Logical wire contract, authoritative for every slice

An intact snapshot uses command `ui_snapshot`, one envelope in the first positional argument and no kwargs. Exact fields are `{protocol_version:1, presentation_epoch:E, revision:R, mode:M, panels:P, layout_version:L, server_time:T}`. Preserve existing E (22 URL-safe characters from 128 unpredictable bits), JS-safe positive R, mode enumeration, layout/time fields and all registered panel schemas. A snapshot renders the complete current eager set and omits area_map/world_map. It atomically removes prior eager names omitted from P and preserves same-epoch on-demand maps. Only a valid live-sequence snapshot can establish initial state or repair a mismatch; stale snapshots cannot regress R.

An intact delta uses command `ui_update` with the same seven fields plus REQUIRED `base_revision:B` and REQUIRED `removed_panels:N`. B is a safe integer >=1, R>B, N is a duplicate-free array of <=32 registered eager panel names, disjoint from keys(P). P may be empty. Each included payload is a complete registered replacement, including the existing available:false form. Missing names are unchanged. N explicitly deletes a previously committed eager value; removing an already absent registered eager name is idempotent. Unknown names, on-demand names in N, duplicate names and replace/remove overlap reject the entire publication. Server-selected removal is explicit via planner `removed_panels`; an absent candidate never implies removal.

Metadata is complete on every publication. Empty P/N with changed metadata is valid. Empty P/N with identical metadata never originates server-side, but a schema-valid newer delta is safe for a receiver to admit. JSON numbers share one number type: 1 and 1.0 compare equal, while true and 1 differ. Dictionary order is irrelevant; arrays retain order. Comparison visits validated candidate values and never serializes or hashes the whole presentation.

Exact-base applies to ALL ui_update publications, including intact on-demand maps and specialized map-body parts. A specialized map transfer repeats the same B and R on each part; it only advances the global committed revision after the complete map validates. Its existing body/limits remain unchanged. Consecutive logical map publications have consecutive baselines. An eager delta before a map uses its own revision; the next map's B equals that revision. No map bypass advances revision without updating the coordinator's sequence revision. General parts never embed a specialized map-body part.

### Atomic reducer contract

Preserve prior-generation, retired-epoch and different-active-epoch rejection before buffering or reduction. A delta cannot establish initial state. For the live epoch require B===committed revision and R>committed revision. Stage all metadata, replacements, removals and registered payload checks; commit once, then notify once. Rejected or incomplete data does not advance revision, mode, maps or server time. A rejected delta returns `{accepted:false, reason:"base_mismatch"}` for the recovery owner; malformed presentation uses existing invalid/missing_envelope reasons. Partial assembly returns `{accepted:false, pending:true}` and never invokes normal accepted-presentation callbacks. Older action results do not change presentation; a newer claimed result is recovery input, not evidence of adoption.

Dialogue coupling changes from unconditional transmission to candidate dependency. Whenever current mode is dialogue, include a fresh dialogue render among candidates. On a mode transition into or out of dialogue, include dialogue and the other declared mode-dependent candidates. Equal dialogue content may be omitted only if the staged committed dialogue remains consistent with the recomputed mode. Client validates mode/dialogue against staged state, rather than requiring dialogue to appear in every delta. Snapshot behavior remains complete.

### Scope and exact integration ownership

This change owns Python `protocol.py::{validate_ui_snapshot,validate_ui_update,_validate_common_metadata}`, browser `protocol/{constants,core,envelope,store}.js`, public protocol exports in `web/static/webclient/js/elosern/protocol.js` and app `lib/protocol.js` when exports change. Update coordinator `_build_presentation`, `panel_update`, `_publish_with_maps` to emit B/N on every delta and prevalidate the new shape. Do not implement suppression or multipart here.

Fixture migration owns `web/static/webclient/js/tests/protocol_fixtures.js::update`, `protocol_support.js`, direct update literals throughout JS tests, `web/webclient-app/tests`, `web/webclient-app/stories/Core/AppShell.stories.js`, Python coordinator/dispatcher/map fixtures and `web/tests/browser/world_map_transport_fixture.py`. Derive each fixture's B from that fixture's actual last committed revision, never assume R-1 for skipped revisions. Shared helper can default B=R-1 only where the fixture explicitly models consecutive publications; explicit gaps supply B. No validator fallback for missing B/N. Existing spec traceability decorators must be updated with meaningful behavioral assertions rather than removed.

### Batch dependency and code-conflict matrix

| ID | Change | Completed prerequisites | Shared-file conflict groups |
|---|---|---|---|
| D | webclient-delta-contract | none | protocol, coordinator, fixtures |
| B | webclient-publication-baseline | D | coordinator, dispatcher/ingress, publishers |
| P | webclient-publication-settlements | B | causal callbacks, coordinator, dispatcher/ingress, push consumers |
| C | webclient-publication-codec | B | coordinator, protocol |
| A | webclient-publication-assembly | C | browser protocol, transport |
| R | webclient-sync-recovery | A | browser protocol, app transport/bridge |
| M | webclient-movement-alignment | P | movement identity, grouped settlement facts |
| S | webclient-settlement-alignment | M | dispatcher/ingress, settlement facts |
| I | webclient-immutable-adoption | R | browser protocol, app view/store |
| F | webclient-sync-functional-smoke | S, I | browser support, shared manifests |

Direct matrix edges are D->B, B->P, B->C, C->A, A->R, P->M, M->S, R->I, S->F, I->F. All other dependencies are transitive. C/A/R/I and P/M/S are logically independent after B, but C and P share coordinator integration surfaces; do not run concurrent edits there. Recommended deterministic implementation order is D, B, P, C, A, R, M, S, I, F. Every slice's integration owner serializes `.github/evennia-shards.json`, `.github/browser-shards.json`, traceability registrations and documentation amendments. No new UI design or content writing is required.

Active proposal conflicts are source integration constraints, not missing semantic dependencies. `authored-dialogue-availability`, `authored-dialogue-reading-server` and `authored-dialogue-unread-notices` share dialogue_push.py and exploration_actions.py with B/P/M/S. `authored-dialogue-reading-server` shares constants.js with D/C/A. `authored-dialogue-reading-client` shares stores/elosern/transport.js and store composition with R/I; `authored-dialogue-unread-notices` shares view consumers. `authored-dialogue-refresh-lifecycle` directly shares typeclasses/npcs.py callbacks with P and owns clock.py/possession.py callback registrations whose semantics P preserves. The physical/lifecycle availability callback helper must capture P causal groups when integrated; no unimplemented dialogue feature is introduced by this batch. Serialize shared files, retain domain projection/reading authority, and route resulting pushes through B/P. `authored-dialogue-locked-ui`, all ten authored-dialogue-content-* changes and `authored-dialogue-generated-packages` have no direct owned-source overlap; manifests/main-spec archive still serialize. Do not edit or complete those active proposals during this batch.

### Main-spec amendment ownership

D modifies `webclient-oob-protocol::Full snapshots and updates have registered replacement semantics` and adds exact-base admission. B modifies `webclient-action-dispatch::Admitted action completion publishes canonical state before unlocking`, the full `A non-success action result surfaces its message exactly once` requirement's stale-order scenario, and `webclient-oob-protocol::WebClient text commands refresh presentation after completion`. C modifies `webclient-oob-protocol::Elosern OOB messages use exact versioned envelopes` to distinguish logical publication size from frame size. R modifies `webclient-oob-protocol::Protocol failures degrade without disabling text play`. New delivery/assembly/causal-settlement/event/immutability/verification capabilities augment the unchanged map, frame-resolution and browser-verification contracts. Existing epoch/puppet, request deduplication, scoped dialogue and world-map allowances remain authoritative. Main specs are updated by the normal later apply/sync/archive lifecycle; this proposal modifies delta specs only.

### Approved source traceability

| Approved design | Requirement/scenario owner | Concrete task owner |
|---|---|---|
| §§3.1,4,5,6 comparison, isolated baseline, unknown scope, no-op | B comparison/baseline requirements | B 1.1-2.2 |
| §§5,7 exact base, removal, metadata, atomic adoption | D modified replacement and exact-base requirements | D 1.1-2.2 |
| §§4,6 all publishers, ordering, preflight and partial-send invalidation | B publication and C preflight requirements | B 2.1-2.2, C 1.1-2.1 |
| §§6,8 serialized settlement, overlapping commands and all-watcher callback order | P causal settlement requirements | P 1.1-2.2 |
| §7 incompatible base, claimed result, bounded recovery | R recovery requirements | R 1.1-2.1 |
| §8 authoritative movement and instance contexts | M checkpoint requirements | M 1.1-2.1 |
| §8 terminal combat and completed skips through both transports | S checkpoint requirements | S 1.1-2.1 |
| §9 one oversized panel, constants, safe schema, teardown | C delivery and A assembly requirements | C 1.1-2.1, A 1.1-2.2 |
| §10 immutable references, snapshot isolation and local state | I immutable adoption requirements | I 1.1-2.1 |
| §§10-11 on-demand maps, generation/epoch/result safety | D/A/I regressions and F actual-browser scenarios | D 2.1, A 2.1, I 2.1, F 1.1-2.1 |
| §11 changed-path functional smoke, deliberate missed invalidation | F integration requirements | F 1.1-2.1 |
| §11 explicit omission of measurements | all Non-Goals and verification contracts | no benchmark/profiling task |

## Risks / Trade-offs

Breaking fixtures can conceal incorrect base handling. Migrate concrete producer state rather than adding inferred receiver defaults. New wire changes require a coordinated unreleased deployment; rollback restores the whole batch and starts fresh transport epochs. Preserved map allowances are explicit exceptions, never permission to relax other panels. No protocol decision remains for apply workers.

## Independent critique disposition

The final whole-artifact independent review found three blocking integration gaps. All were adopted. B now has one always-Deferred queueing API and private nonqueueing synchronous publisher, including direct art/ingress callers and explicit failure/retirement outcomes. New one-day slice P replaces long-lived session tokens with causal synchronous commit groups, preserves overlapping text/graphical Deferred execution, and captures presentation callbacks for every watcher in either push/fact order. M/S now depend on and reuse P, with new reverse-completion, multiwatcher and out-of-ingress scenarios. The critique did not run implementation checks; strict proposal validation and the repository contract gate are separate final evidence. No second independent review or clean-review verdict is claimed.
