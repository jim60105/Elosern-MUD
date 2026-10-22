# Recent Deeds for Epithet Nomination

Date: 2026-10-22
Status: Approved in conversation; written-spec review pending

## 1. Goal and scope

Supply epithet nomination with committed recent deeds, including adult-system activity, through the existing durable narrative-event store. Preserve player consent and the deterministic title writer. Replace the rest-day-boundary trigger with a wake transition trigger.

The player should receive names grounded in recent accomplishments and distinctive behavior. Party members are peers. Their survival does not establish that the player protected them. Adult-system deeds have the same standing as other eligible deeds.

This document amends the nomination trigger and input contracts described in `openspec/specs/title-system/spec.md`. Main specifications must be updated through the repository OpenSpec workflow during implementation. The architectural ownership in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` remains unchanged.

No implementation is included in this design change.

## 2. Current behavior and relevant existing components

`server/title_nomination_service.py` builds a plain nomination context and calls the AI proposer. Its production triggers supply no `event_logs`, so the recent-event field is empty. The service does not retrieve history.

`world/ai/title_nomination.py` requests five candidates, applies deterministic name filters, and retains at most three survivors. Its current event serializer selects actor, skill, targets and entry templates. It omits entry data that distinguishes adult-system outcomes.

`world/narrative/events.py` already records immutable, source-keyed narrative events transactionally. Records carry participants, location, world tick, visibility and salience. This is the sole persistent source for the new deed feed. Existing narrative events include generated statements, so eligibility must be explicit.

`world/rules/action/event_log.py` exposes settled action evidence such as `sexual_transition`, `sexual_counter`, `sexual_resist`, and skill effects. `world/rules/sexual_state/handler.py` also maintains cumulative state. Cumulative state alone cannot establish when an occurrence happened.

The existing `encounter_protection` selector treats victory with a qualifying surviving ally as protection. Epithet nomination will not consume that classification. Other narrative consumers retain their existing behavior.

## 3. Decisions and alternatives

Use the durable narrative-event store and add missing deterministic producers. An epithet-specific history would duplicate facts. Querying separate quest, examination and combat histories at nomination time would couple the reader to multiple lifecycles and omit process-level behavior.

Use an inclusive rolling 48-hour world-time window. Event-count windows and since-last-nomination windows were considered and rejected. Nomination does not consume events; a deed may be used again while it remains inside the window.

Events that automatically award built-in titles remain eligible material, but their settlement does not itself trigger nomination. Suppression uses a common award-result contract rather than an event-type exclusion list. The player accepts the possibility that a later nomination uses those deeds under a different name.

No eligible material means no nomination attempt. Character identity and preference summaries alone are insufficient grounds for a call.

## 4. Ownership and data flow

The deterministic subsystem settling an action or lifecycle transition provides the authoritative evidence. `world/narrative/` owns durable narrative-event writes. These writes participate in the original settlement transaction. A rollback leaves neither the action outcome nor its deed record committed.

Narrative storage must not import the AI proposer. The composition-root nomination service reads eligible committed events, builds detached prompt data, and invokes `world/ai/`. The AI module proposes candidates without mutating game state. Only the existing rules-layer writer persists a ballot or grants an accepted epithet.

Event producers use stable occurrence identities. Replayed settlement notifications must resolve to the same event rather than create another occurrence. Names are display snapshots; durable participant identities determine attribution and authorization.

Nomination is a read workflow after settlement commits. Failure to query or generate a nomination cannot roll back completed gameplay. Failure to write a required deed inside its source transaction fails that transaction and preserves all-or-nothing behavior.

## 5. Eligible evidence

Eligibility uses a closed set of deterministic event adapters. Arbitrary narrative event types and model-authored statements are excluded. Player self-reports and narrator prose are not evidence.

| Source | Included facts | Limits |
| --- | --- | --- |
| Completed quest | Quest identity, completed objective and actual outcome | Acceptance and partial progress do not establish completion |
| Passed guild examination | Examination identity and attained rank | Supplies material without triggering nomination |
| Completed combat encounter | Actual victory, defeat or escape; participants and opponents | Summarize the encounter rather than each hit; simulated examinations must not become lethal victories |
| Settled skill use | Skill identity, actual actor, recipients and committed effects | Do not infer rescue, exceptional difficulty or merit from a skill name or repeated casting |
| Adult-system action | Established act type, participant roles and committed outcomes | Do not infer participation from proximity or party membership |
| Adult-system milestone | Experience newly acquired, an unlock actually crossed, or a significant state transition | Record at the transition; do not date an existing lifetime counter or state as recent |

Exclude routine movement, waiting, commerce and conversation from this scope. Do not add a protection deed category. Concrete healing and other effects may be included under skill use without describing them as protection or rescue.

An eligible event carries the automatic built-in-title award results associated with its occurrence. These results originate at the unified rules-layer award entry point described in section 5.2. Producers forward authoritative results without maintaining separate title-bearing event classifications. Ordinary skill-use records never create immediate nomination triggers.

### 5.1 Adult-system meaning and knowledge boundaries

Read structured effects and committed state transitions. Preserve who performed an action and who received an effect. Numerical arousal, climax and automatic compliance do not establish affection, willingness or a relationship commitment. A resistance result must retain its actual meaning.

Only evidence personally involving the player and accessible to that player can enter the feed. Participant membership alone does not authorize disclosure of every field about another participant. Adapters omit private internal state the player cannot know and apply existing visibility rules before aggregation or rendering.

Private personal experience can support the player's nomination. It does not establish public notoriety. Neither the prompt nor the generated basis may claim witnesses or public recognition without evidence. This change does not create a reputation system or alter downstream title-display availability.

### 5.2 Extensible built-in-title award contract

All automatic built-in-title awards use a unified rules-layer award entry point. It reports the titles actually newly granted to the recipient and associates those results with the originating occurrence's stable source identity. Player acceptance of an LLM-generated epithet is a separate workflow and does not produce an automatic built-in-title award result.

An award result identifies the source occurrence, recipient and granted title identity. Several title grants from the same occurrence contribute to that occurrence's results. A title already owned contributes no new grant. Replayed settlements preserve the original committed results and cannot erase suppression by replacing them with an empty replay result.

Award results, source evidence and title writes share the source settlement transaction. Finalize the event and its award results before committing the immutable narrative record. Do not persist an event and later patch award information into it. Rollback removes the title grant and associated evidence together.

The nomination service suppresses an immediate trigger when its source occurrence has an automatic award result for the nominated player. It does not inspect event types, display names, or the player's unrelated existing titles. An award to another participant does not suppress the player's nomination. No second exclusion list or producer-authored Boolean duplicates the award result.

Existing guild-examination and other automatic built-in-title award paths must adopt this contract in the same cutover. Future exploration, combat, adult-system or other built-in titles use the same award entry point and source association without requiring nomination-service changes. This contract does not make new event types eligible nomination triggers or evidence automatically; those remain separate policies.

Suppression is local to the triggering occurrence. A later wake or logout can still use the award-bearing deed inside its rolling window. Adding a title already owned does not suppress an otherwise eligible new occurrence through this rule.

## 6. Time window and selection

Freeze the world tick `T` when an admitted nomination begins. Derive the duration of two days from the canonical clock configuration; under the current 24-hour day this is 172,800 game seconds. Include events with ticks from `max(0, T - duration)` through `T`, inclusive. Exclude future records.

The current fatigue policy has full reserve 360,000 units. Ordinary wakefulness consumes 4 units per game second, foot travel 8, and awake combat 12. Full-to-empty times are respectively 25 hours, 12 hours 30 minutes, and 8 hours 20 minutes. Sleep restores 12 units per second; empty-to-full restoration takes 8 hours 20 minutes. The 48-hour window exceeds the slowest depletion plus full restoration by 14 hours 40 minutes. These numbers justify the chosen window; do not duplicate fatigue balance constants in nomination code or dynamically resize the window when fatigue changes.

Filter time, eligibility and access before aggregation. No out-of-window occurrence may affect a count or summary.

Group actions from the same combat encounter with its outcome. Combine effects and milestones from the same action occurrence. Repeated actions can be compressed when they are consecutive in the eligible stream and share the action type, participant identities and roles, and encounter context. Do not combine across different encounters. Outside combat, a change in those fields ends the repetition group. Retain distinct results and milestones within each group. Counts represent retained committed occurrences only.

Sort groups by latest included occurrence tick descending, breaking ties by stable source identity ascending. Retain at most eight groups. Render the event JSON within 8,000 Unicode code points, including its envelope. Remove older complete groups if needed. Never truncate JSON or detach a claim from its result. A group that cannot fit alone is omitted rather than clipped into a misleading account. If no renderable groups remain, treat the feed as empty.

Every presented fact remains traceable to immutable source IDs. A group includes the source IDs needed to support its retained facts. Reference lists are part of the same size budget; do not invent a persisted event ID for an aggregate.

## 7. Triggers and suppression

Eligible triggers are player logout, player awakening, and qualifying quest completion. Replace the old rest-crossing-midnight trigger completely. The common award-result check suppresses immediate nomination from a source occurrence that automatically awards a built-in title to the player, including guild promotion and title-awarding quest completion. Guild examinations remain evidence-only and do not register a separate nomination trigger. Do not add event-type exceptions to implement the award-result check.

Awakening means a committed transition from voluntary or forced sleep posture to awake. It is independent of command spelling, transport, midnight and UI notifications. Notify the composition-root service after the outer transaction commits. Replaying the same transition does not create another attempt. A teammate waking does not nominate the player. NPC transitions do not nominate. Do not invoke nomination while the player remains in live combat; no special deferred wake trigger is added for that case.

Keep the existing single-ballot and decline-derived cooldown rules. Acceptance does not create a cooldown. Empty material, a disabled profile, or a failed/void generation does not start one.

Allow at most one in-flight nomination per player identity within the server process. Wake followed immediately by logout joins no new call and replaces no request. Release the in-flight slot on every completion and failure path. The rules writer rechecks suppression when a result arrives. A process restart retains existing ballots through their current storage; abandoned generation is not resumed.

## 8. Prompt and output contract

Keep player name, current full title, recent declined-name preferences and recent removed-name preferences. These preference lists are advisory. Fixed-title names and the live owned-epithet collection stay out of the prompt and remain deterministic collision inputs.

Replace the old template-only event serialization with structured recent-deed data. Each group carries provenance, occurrence times, location, relevant participants and their roles, actual actions and outcomes. IDs establish identity; player-facing labels make the facts understandable. Do not send live entities or unrestricted raw content dictionaries.

Ask for exactly five candidates. Each output candidate has `display`, `basis` and a non-empty `source_ids` array of distinct IDs. All cited IDs must appear in the material actually rendered for that request. An invalid citation eliminates that candidate. Whole-response shape, count and field-size violations retain their existing round-voiding behavior. Require bounded citation arrays using the request's supplied source set as the maximum possible count.

Preserve the existing display and basis length limits. Existing per-candidate form and collision filters retain their order; citation eligibility is checked before a candidate can enter the ballot. Retain the first three survivors. One or two survivors remain valid; zero survivors void the round.

Citation validation proves source membership. It cannot prove that free-form language faithfully describes a source. The prompt must forbid fabricated outcomes, actor-role reversals, unwarranted consent or relationship conclusions, and invented public recognition. A second model review is outside scope.

The generation boundary consumes `source_ids` for validation and passes only `display` and `basis` to the current ballot writer. The player-facing ballot and stored title shape stay unchanged. Request and response transcripts retain the cited provenance through the existing transcript mechanism.

## 9. Errors and observability

Persisted malformed title state remains fail-closed under existing rules. Inaccessible or unsupported source records never enter the prompt. Malformed eligible records fail closed for that record with a diagnostic; if nothing usable remains, skip generation.

Read failures, transport errors and invalid outputs leave completed gameplay untouched. They create no ballot and no decline cooldown. Do not manufacture substitute deeds or names. An unavailable LLM leaves deterministic gameplay playable.

Use the existing `world.observability` facade and narrative-event boundary events. Nomination workflow events identify the player, trigger, frozen tick and source counts in context. Exceptions use `exc=`. Do not duplicate full private deed prose in operational logs. Full request and response payloads follow the existing transcript policy and credential exclusions.

## 10. Verification and specification updates

Behavior tests must establish the following boundaries with synthetic data.

| Boundary | Required proof |
| --- | --- |
| Window | Include the exact lower boundary; exclude older and future events; exclude expired repetitions before counting |
| Evidence | Correct actor and recipient roles; no protection inference; structured adult results survive prompt construction |
| Transaction | Inject failure after relevant writes and show gameplay, title grants, award results and narrative records roll back together; replays neither duplicate occurrences nor erase original award results |
| Milestones | A newly crossed threshold is recorded once; pre-existing counters do not create recent milestones |
| Trigger | Voluntary and forced awakening trigger after commit; midnight alone, teammates, NPCs and fixed-title-bearing settlements do not |
| Award extensibility | A synthetic new event and built-in title use the common award entry point and source association to suppress an otherwise eligible immediate nomination without nomination-service changes; the deed remains usable at later wake/logout |
| Award attribution | Another participant's award and an unrelated previously owned title do not suppress the player's nomination; several grants from one occurrence suppress once |
| Authorization | Another character's private or unknown fields never appear in rendered inputs |
| Prompt budget | Preserve complete JSON and factual groups; no retained claim loses required provenance or outcome |
| Empty/offline | No model call for empty material or disabled profiles; no ballot or cooldown on failure |
| Output | Unknown or omitted-source citations eliminate candidates; existing form and collision behavior remains intact |
| Concurrency | Overlapping triggers cause one call; all failures release the slot; late results cannot overwrite a ballot |

Run representative offline smoke flows through real construction, source settlement, committed event storage, selection, rendered prompts, a fake model transport, and committed ballot reload. Exercise a non-fixed-title accomplishment and an adult-system action, including an untouched-recipient control and rollback injection. A fake transport replaces the external service only; it must not replace the settlement or persistence boundaries.

Update the main title capability through OpenSpec deltas, affected traceability claims, and focused tests. Register added or moved Evennia test modules in the shard manifest. Update command documentation if observable command behavior or availability changes. Run focused tests with observability lint when logging changes, then the repository contract gate. Full browser suites and complete evidence verification remain CI-owned.

## 11. Non-goals and cutover

Preserve built-in-title award conditions and benefits while unifying their award-result reporting. Do not change fatigue balance, adult mechanics, party relationships, reputation, player acceptance, ballot expiry, or the decline cooldown. Do not remove the existing protection projector from other narrative consumers. Do not add historical backfill, migrations, or compatibility paths for the empty-feed interface.

Replace old input producers and callers together. Remove the obsolete rest-day trigger and unused event-log-only nomination serializer when the structured feed takes over. Use the repository OpenSpec proposal and apply workflow for implementation after written-spec review and planning.
