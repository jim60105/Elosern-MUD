# Escort Objectives, Temporary Party Membership, and Exclusive Outcomes

Date: 2026-10-11

Status: Conversation design and written review approved.

## 1. Purpose and approved decisions

Make generated private escort commissions executable through the existing quest,
party, combat, possession, and settlement owners. This is the second of three
sequential designs, following
[quest scene encounters](2026-10-11-quest-scene-encounters-design.md).

The girl and mother are a functional verification example, not special-case
mechanics. Either may offer a different commission to escort herself to the
other. Their quest records and rewards are separate, but successful reunion
resolves one shared exclusive outcome and invalidates the alternative commission.

Approved decisions:

- Extend the existing party system with general and temporary membership.
  Do not implement an independent escort-follow system.
- Escort-added temporary members do not consume the general companion quota and
  do not leave because of affinity while their escort binding remains valid.
- Temporary members use existing following, combat participation, incoming
  targeting, and possession capabilities. They are not invulnerable passengers.
- Ending a commission releases its temporary membership reason. Preserve any
  pre-existing general membership or other still-valid temporary reasons.
- Support two explicit escort completion modes: destination arrival and role
  rendezvous. Mother/daughter reunion uses rendezvous, at any actual location.
- Model multiple distinct commissions with a shared exclusive outcome. Resolve
  and settle only one winner; alternatives expire, including accepted ones.
- Actual events determine completion and dialogue phases. LLM prose never proves
  arrival, reunion, death, acceptance, or settlement.

The architectural source of truth remains
[the engine design](2026-07-29-ai-mud-engine-design.md). Memory and knowledge follow
[the cognition design](2026-10-03-narrative-memory-cognition-design.md).

## 2. Current implementation and required amendments

`QuestRecord` already has `protected_entity_ids`. `bind_stage_runtime()` can bind
living entities, and `_escort_ready()` checks that every protected actor is alive
and at the destination. Generated escort publication is deliberately refused
because the generated protected-role binding flow is missing.

The current party has one membership identity and a four-companion quota.
`follow_companions()`, combat collection, possession, and affinity departure all
use that membership. Room observation is player-arrival-gated and supports
location-based completion, not moving role rendezvous. Private issuances and
automatic/counter settlement already provide the reward authorities.

Amend the current party, possession, quest runtime/progress, issuer, compilation,
and settlement requirements affected by dual membership, role completion,
`INVALIDATED` records, and exclusive result arbitration. Replace generated escort
rejection only after valid protected-role binding, actual movement, and settlement
are implemented and proved. Do not bypass the guard with a special mother/girl
payload or relabel the commission as another quest type.

Cover every current rejection boundary, including `server/ai_director_service.py`,
ScenarioDirector semantic validation, the compiler, and generated registration.
Enable only payloads/templates with the complete new protected-role and
completion contract; unsupported templates do not gain invented nearby actors.

## 3. Ownership and interfaces

| Owner | Responsibility |
| --- | --- |
| `world/quests/` | Escort definitions and active bindings, role completion predicates, exclusive outcome state, quest transitions and invalidation. |
| `world/rules/party.py` | Canonical general/temporary membership, quota, join/release, safe member reads, following and combat membership. |
| Existing rules combat/possession owners | Damage, life state, combat participation, control transfer, session compensation, and release. |
| Existing quest/rules settlement owners | Registered rewards, automatic/counter payout, and the existing exactly-once reward claim ledger. |
| `world/maps/` | Authoritative location and traversal, including wilderness coordinate identity and instance lifecycle. |
| `world/narrative/` | Durable result events, participant knowledge, dialogue/history and memory projection. |
| Presentation | Current party identities, mission state/reason, dialogue choices, and permitted possession actions. |

Consume the first design's stable package/role-to-NPC bindings. Scene roles are
not copied into a new escort NPC. A proposed role reference must resolve to the
same live entity at acceptance and at every completion evaluation.

Normal and possessed actions retain their existing authoritative actor/owner
mapping. A possessed temporary NPC remains the physical actor; the original
player remains the quest owner. Do not teleport the original body or rewrite
ownership to make a quest observer work.

## 4. Canonical party identities

Retain one ordered roster and one owner back-reference per NPC. Extend its
persistent membership metadata with general-membership status and a unique set
of temporary reasons referencing accepted quest identities and protected roles.
The normal binding path declares general membership; the escort binding path
declares a temporary source. Ordinary membership remains the normal default.
There is no second roster, legacy-format adapter, or general/temporary duplicate
entry for one NPC.

| Invariant | Required behavior |
| --- | --- |
| General quota | Count valid general members only; retain the current general quota. |
| Temporary-only member | Does not count toward that quota. |
| General member also protected | Keeps its general identity and quota usage; add the escort reason without duplicating its roster entry. |
| Validity | Temporary reasons must resolve to an active owned quest that binds this exact NPC as protected and is not invalidated. |
| Ownership | A role already bound to another owner cannot be stolen. |
| Safe reads | Resolve both membership kinds through the same canonical readers; stale/deleted/corrupt references grant no membership or affinity immunity. |
| Affinity | Keep relationship changes, but suppress automatic departure while any valid escort reason remains. |
| General recruitment | Apply ordinary eligibility/quota checks even if the NPC currently has only temporary membership. |
| Last-source release | Remove temporary-only NPCs when no valid temporary source remains; retain genuine general members. |

The same safe member set drives `bound_owner_of`, following, combat collection,
possession gates, affiliation, quest attribution, and presentation. Migrate every
consumer rather than adding escort exceptions in individual callers. Temporary
status does not waive presence, living-state, combat, dialogue, or other existing
possession-entry gates.

Manual dismissal must not detach an effective escort reason while leaving its
quest active. The interaction must use abandonment of the relevant commission;
when several reasons exist, show the affected commissions and release only the
chosen ones. General membership can be removed separately without cancelling
remaining valid temporary membership.

While an escort reason is valid, follower movement takes precedence over ordinary
NPC schedule movement. Releasing the last temporary reason restores applicable
schedule behavior at the current world tick, without transporting the NPC back
to an old encounter or replaying missed movement events.

## 5. Acceptance and release

The acceptance boundary revalidates issuance authority, current offer availability,
exclusive outcome status, protected role identity, co-location, living state,
and membership ownership. Full general quota does not reject temporary joining.

In one outer transaction, create the accepted quest record, bind the exact
protected entities, add temporary membership reasons through party APIs, update
applicable dialogue state, and record durable acceptance. Snapshot and restore
quest, party, component, and dialogue caches if any later write fails.

Multiple protected roles are permitted only as explicitly declared by the
validated definition. Each must be available; partial roster acceptance is
forbidden. The blueprint cannot add arbitrary nearby NPCs or choose a typeclass.

Completion, failure, abandonment, or invalidation removes that record's temporary
reasons. A role with other valid reasons stays bound; a pre-existing general
member keeps its general identity. No terminal transition deletes the actor,
resets memory, or converts a temporary-only member to a general member.

Before an NPC actually leaves the party, hand back any possession through
`release_for_party_change()` and the existing session/control-transfer machinery.
If it remains a valid member, do not interrupt unrelated possession. A rollback
after handback must restore control, cmdsets, possession mirrors, membership, and
cached quest state through existing compensation seams, not just database rows.
Technical handback failure is an all-or-nothing transition failure, never a
successful release with dangling control.

## 6. Explicit escort completion modes

Keep the escort quest classification separate from its objective predicate.
An escort objective declares exactly one closed completion discriminator:
`destination` or `rendezvous`. Reject missing/ambiguous predicates and payloads
that declare incompatible destination and rendezvous fields.

### 6.1 Destination mode

Require all exact protected identities alive at the validated destination, using
existing anchor, XYZ, or bound-instance locators. Evaluate after the applicable
owner traversal or possessed protected-actor movement settles, including follower
moves. Entering the room before the protected actors arrive is insufficient.
A different member or same-name NPC never substitutes for a protected actor.

Instance-room pinning remains distinct from permanent-location resolution. Do not
pass permanent rooms through the current instance-only pin contract or pretend a
permanent destination is a bound instance.

### 6.2 Rendezvous mode

Declare protected role references, meeting role references, and any required typed
relation such as parent/child. Require those exact actors alive at the same actual
location and the declared relation to match the published role identities.

No fixed destination is required. Mother and daughter may meet at the south gate,
a home, an inn, another ordinary room, an instance, or a wilderness position. The
player's original body need not be present; possessing and moving a protected
actor can satisfy the same physical condition. Do not require an unrelated party
member or a return to an originally suggested meeting location.

Compare authoritative positions, not display keys. Ordinary room identity and
wilderness provider/coordinate identity must remain distinct; recycled wilderness
room objects cannot prove co-location at different coordinates. This adds a
rendezvous predicate, not an invented wilderness destination locator or pathfinder.

Use role movement, encounter activation, acceptance/binding, and living-state
changes as evaluation boundaries. The current player-only room-arrival hook is
insufficient. Evaluate the relevant owned bindings through indexed role/outcome
references; do not scan every player or every generated story per movement.

Consolidate checks after the applicable movement/follower settlement, with a
stable source identity and the existing one-transition-per-event rule. A
pre-follow room receive and a post-follow recheck cannot advance two stages for
one traversal. Direct NPC/possessed movement must reach the same evaluator.

### 6.3 Finding and knowledge

Finding a character uses real presence and interaction, not an invented location
fact from a model. Clues and scripted topics expose only what the speaker knows.
The deterministic evaluator may inspect the actual meeting actors, but their
hidden coordinates do not become player hints merely because the objective
references them. Explicit information transfers can add later clues/memories.

No arbitrary condition language, generated action program, autonomous search
agent, or additional escort completion family is introduced. Other objective
families require a separately designed deterministic contract.

## 7. Exclusive outcomes and alternative commissions

A validated package can declare an exclusive outcome group naming a concrete
result condition and the distinct commissions that become obsolete when it holds.
Story-thread identity alone does not imply exclusivity. Each alternative keeps
its own definition, issuer, accepted record, protected roles, deadline, and reward.

Persist group state under owner/package/group identity with uniqueness and a
committed resolution source. State is unresolved or resolved; resolution records
one winning accepted record or explicitly records resolution without a commission.
Assign a monotonic acceptance sequence under the same owner/group lock. World
tick alone is insufficient to order two acceptances in a single tick.

On a satisfying event:

1. Lock and revalidate group state and all relevant active records.
2. Select the terminally satisfying accepted record attributable to the actual
   escort event. Attribution uses the event's actual moved/bound protected actor
   identities. If several remain valid candidates, choose by acceptance sequence,
   then stable record identity.
3. Apply one winner's actual transition to `COMPLETED`. Mark other active
   alternatives `INVALIDATED`, with a structured obsolete-outcome reason.
4. Close all unaccepted alternatives and reject stale acceptance attempts.
5. Release only the affected temporary membership reasons and obsolete stage pins.
6. Record the outcome, participant knowledge, and dialogue phase changes. Apply
   the winner's existing settlement mode and reward-claim rules in the same
   transaction when automatic payout is required.

Arbitrate before planning reward effects. The existing per-record claim ledger
cannot by itself prevent two different alternative records from being paid.
Exactly one record may gain settlement eligibility for this group. Counter
settlement may be claimed later only for that winner; alternatives never gain a
counter claim. Private rewards remain merit-free and registry-derived.

`INVALIDATED` is a distinct terminal quest state, not `FAILED`, abandonment, or
successful completion. It has a visible reason, no payout, no failure penalty,
and no retry/acceptance path after the group has resolved. Update serialization,
planners, deadline processing, presentation, tracking and all terminal checks.
Retain normal failure rules for actual death or missed deadlines.

The exclusion applies when the declared result is achieved, not when a player
merely accepts one offer. If physical conditions permit multiple accepted
alternatives, they remain separate until result arbitration. Do not suppress
unrelated commissions in the same storyline.

When the player causes actual rendezvous without accepting any alternative,
commit the real outcome, participant memories and appropriate dialogue changes,
and close now-obsolete offers. There is no winning quest, retroactive acceptance,
or reward. A repeated/restarted event preserves the same resolution identity.

For multi-stage definitions, the group declares which final result resolves it.
An intermediate arrival or clue does not invalidate alternatives or pay the
terminal reward. Preserve the one-stage-transition rule for each source event.

## 8. Dialogue, failure, and presentation

Reunion produces an authoritative event for the actual participants. Use the
first design's phase-aware greeting, topics, fixed responses and free-form
context. Resolve reunion acknowledgment and then the defined closure interaction
before selecting everyday content. Private planning data never becomes NPC
knowledge. Uninformed third parties do not learn reunion from a global stage flag.

A lost follower stays at its real location and the player receives the existing
kind of lost-follow notification. Separation alone is not a fabricated death or
automatic success. Returning to the actor can resume the valid escort.

Committed death of a protected actor fails its active escort. Death/removal of an
essential meeting actor makes the objective unavailable through an explicit
transition, not an endlessly pending quest or substitute spawn. Ordinary knockout
uses existing living/recovery rules and is not equated with death. Combat failure
planning must cover hostile and environmental sources, not only player attacks.

Temporary party members participate in the same lawful combat and targeting
rules as general members. No temporary-only immunity or combat exclusion is
added. Apply the current knocked-out-member engagement behavior.

The party view identifies general and temporary status and associated commissions;
a member carrying both is still one row. Surface quota information separately
from total roster size so a full ordinary party plus escorts is not mislabeled.
Render the complete effective roster rather than truncating it to the ordinary
quota; temporary members must remain reachable through existing party controls.
Preserve existing layout/input behavior; do not add a new escort-control UI.
Refresh versioned capabilities on membership/phase/offer changes and reject stale
choices. The text client must retain equivalent interaction and explicit reasons.
Update both command documentation files when invite/leave or availability changes.

All changed boundaries use the observability facade with player, quest, issuer,
package, group, role, NPC, room/position, tick and source identifiers in context.
Record escort join/release, progress, exclusive resolution/invalidation, control
handback, payout, and named failures; protect prose and credentials as usual.

## 9. Acceptance and verification

Use synthetic fixed scene packages through real deterministic owners, no live LLM.

1. Fill the ordinary quota, accept an escort, and reload. The exact NPC joins as
   temporary without evicting existing members or consuming an ordinary slot.
2. Change affinity below the ordinary departure threshold. A valid temporary
   member stays; an ordinary-only control still follows the ordinary rule.
3. Bind a pre-existing general member and an NPC with multiple temporary reasons.
   Releasing one mission preserves every remaining legitimate membership.
4. Run actual exit/wilderness following, combat engagement and received damage,
   possession and possessed movement. Observe the same NPC identity and correct
   owner throughout; no double-follow or extra clock charge occurs.
5. Complete rendezvous at more than one location, including a valid wilderness
   position, without requiring the player's original body. Same-name impostors,
   dead/missing actors and different coordinates fail the predicate.
6. Complete destination mode only at its declared locator after every protected
   actor arrives. An unrelated companion and an early player arrival cannot
   substitute for the protected roster.
7. Exercise both issuer-first orders, distinct alternative records and a
   simultaneously satisfiable event. Observe one stable winner, one payout
   entitlement, invalidated accepted alternatives and closed unaccepted offers.
8. Cause physical reunion without accepting an offer. The story changes to
   reunion/closure and everyday dialogue without adding a reward claim.
9. Repeat/restart a resolution and retry stale acceptance/choice capabilities.
   No duplicate transition, payout, membership, or later-stage progress occurs.
10. Exercise abandonment, actual lethal damage, knockout/recovery, deadlines,
    missing required actors and invalidation. Outcomes and per-role dialogue are
    distinct; no NPC is deleted or regenerated as lifecycle repair.
11. End an escort during possession. Handback and source release preserve control
    invariants. Inject failures after record, membership, group, reward and
    handback changes; committed reload and live session state return to baseline.
12. Reload terminal state and reopen the actual NPC conversation window. Successful
    closure shows everyday greeting/topics and preserves prior history/memory;
    unresolved failure never presents a successful reunion.

Run focused party, quest, combat, possession, dialogue and presentation tests;
observability/data lints; affected command documentation tests; manifest ownership
checks; and the mandatory contract gate. Trace amended current requirements with
substantive behavior tests. A runtime smoke must use actual acceptance, movement,
combat/possession, completion, payment and reload; passing blueprint validators
alone is insufficient.

## 10. Dependency contract

Design 1 provides materialized role identity, independent pre-acceptance encounters,
validated issuer scope, retention, and phase-aware dialogue. Amend its package
contract to permit multiple distinct issuances and exclusive-group references;
do not replace issuer authority with prose or one shared quest record.

[Design 3](2026-10-11-dream-story-dispatch-design.md) must preserve both possible
encounter orders, consume the extended blueprint contract, activate relevant roles
before final movement-result observation, and publish these commissions without
autoaccepting them. Its request lifecycle must not treat a textual quest proposal
as successful execution.

No data migration or backward-compatibility layer is added. Deployment uses the
fresh database approved in design 3, with current schema initialization. Preserve
the existing party ID roster shape and normal defaults, extend its metadata
contract, and update every affected reader/writer in one cutover.
