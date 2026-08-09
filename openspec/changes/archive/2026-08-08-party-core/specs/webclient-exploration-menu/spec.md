## MODIFIED Requirements

### Requirement: Exploration affordances are server-authored, never inferred from prose
Every `interact` affordance SHALL be derived from canonical data with the same checks commands use, never from typeclass names, display prose, or other heuristics. `explore.talk_scripted` SHALL be offered only for a present NPC with a resolved dialogue component (`OnboardingGuide` or `ScriptedDialogue`); the target descriptor then SHALL carry a bounded list of at most 16 scripted keyword descriptors (each exactly `keyword_id` and bounded `label`) derived from the dialogue table registry, and the talk_scripted affordance itself SHALL carry no keyword list (the scripted buttons live on the target so the interact payload stays within the protocol's global JSON-depth bound). `explore.talk_freeform` SHALL be offered only for a present NPC with an eligible free-form dialogue surface (an `LLMNPC`). `explore.party_invite` SHALL be offered only for a present NPC with an eligible free-form dialogue surface (an `LLMNPC`) that is not already a companion of the actor, SHALL be enabled when the actor's party has fewer than 4 companions and disabled with the full-party reason otherwise, and SHALL never be offered for an already-bound companion (the leave affordance covers it). `explore.party_leave` SHALL be offered only for a present NPC that is currently a bound companion of the actor. `explore.engage` SHALL be offered only for a present living hostile `Monster` when the actor has no active combat session. A `navigate`-kind service affordance (`surface` `"guild"` or `"shop"`) SHALL be offered only when the current room has exactly one unambiguous `GuildStaff` or `Merchant` host for a service the actor can use, and it opens the corresponding services submenu rather than inventing a mutation. No affordance SHALL reference a remote, absent, or ambiguous host or target. Every adapter SHALL re-verify at commit time, against the actor's current location and current canonical state, the affordance that produced its descriptor — presence in the actor's location, the exact typeclass/component/eligibility, and the unchanged keyword, party, or host condition — so a target removed from the room, type-changed, or no longer eligible between render and submit is rejected before the display, dialogue, invite, leave, or engage API is called and before any onboarding, memory, intent, party, session, or time state changes.

#### Scenario: A scripted host exposes its authored keywords
- **WHEN** a present NPC carries a `ScriptedDialogue` component with two authored keywords
- **THEN** its interact descriptor offers `explore.talk_scripted` with exactly those two keyword buttons and no free-form affordance

#### Scenario: A generative NPC offers free-form talk
- **WHEN** a present `LLMNPC` is in the room
- **THEN** its interact descriptor offers `explore.talk_freeform` and, when it also carries a scripted component, the scripted affordance as well

#### Scenario: An unbound generative NPC offers an invite
- **WHEN** a present `LLMNPC` is not a companion of the actor and the party has room
- **THEN** its interact descriptor offers `explore.party_invite` enabled; with four companions already the affordance is disabled with the full-party reason

#### Scenario: A bound companion offers leave instead of invite
- **WHEN** a present NPC is currently a companion of the actor
- **THEN** its interact descriptor offers `explore.party_leave` and never an `explore.party_invite`

#### Scenario: A living hostile monster offers engage
- **WHEN** a present living `Monster` is in the room and the actor has no active session
- **THEN** its interact descriptor offers `explore.engage`; an already-engaged actor receives no engage affordance

#### Scenario: No affordance is fabricated for a plain NPC
- **WHEN** a present NPC carries neither a dialogue component nor an eligible free-form surface nor a party binding
- **THEN** its interact descriptor contains no talk, invite, leave, or service affordance, and the browser renders only the descriptors the server sent

### Requirement: explore.party_invite proposes a party through the guarded dialogue seam
The production action registry SHALL register `explore.party_invite`. Its payload SHALL accept exactly `npc_id` (a positive integer) and `message` (a string of at most 512 code points, possibly empty). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — re-verify presence, free-form eligibility (an `LLMNPC`), no existing binding, and a party below the 4-companion bound, obtain the `npc_dialogue` profile client from the exploration composition root (a live `OpenAICompatClient` when the profile is enabled, or a non-`None` offline stub when disabled — the stub is never called because the guardrail degrades before any transport work), and run `npc.run_npc_exchange(message, actor, client)`. On the degraded terminal the adapter SHALL apply the fixed threshold decision (`affinity >= 70`) with deterministic accept/reject lines; otherwise it SHALL present the reply's speech and route the reply's intent through `apply_npc_intent`, rendering the join, refusal, full-party, duplicate, and remote notifications with the same fixed Traditional Chinese messages the `invite` command uses, and SHALL never override an AI decision with the threshold. The adapter SHALL return a Deferred that resolves to a safe success result after the seam settles, SHALL publish a full snapshot at one newer revision so the applied membership binding refreshes atomically, and SHALL NOT assign memory, intent, party, or affinity state directly. A missing, no-longer-present, non-eligible, already-bound NPC or a full party SHALL reject synchronously with a stable code before any client or transport work.

#### Scenario: An invited generative NPC joins through the webclient
- **WHEN** an actor submits `explore.party_invite` for a present unbound `LLMNPC` and the dialogue reply carries `party_invite` with `accept: true`
- **THEN** the NPC's speech is shown, `join_party` binds the companion, and the actor receives the join notification

#### Scenario: Offline webclient invites fall back to the fixed threshold
- **WHEN** the `npc_dialogue` profile is disabled or unreachable and the actor submits `explore.party_invite`
- **THEN** the invitation accepts on `affinity >= 70` with a deterministic acceptance line and rejects below it, with no network request

#### Scenario: A full party blocks the webclient invite before the AI call
- **WHEN** an actor with 4 companions submits `explore.party_invite`
- **THEN** the adapter rejects synchronously with the full-party reason and the dialogue seam is never invoked

### Requirement: explore.party_leave dismisses a bound companion without affinity change
The production action registry SHALL register `explore.party_leave`. Its payload SHALL accept exactly `npc_id` (a positive integer). The adapter SHALL obtain the actor from the authenticated session, re-resolve the NPC from the actor's current location's present contents — never a stored, remote, or ambiguous reference — re-verify that the NPC is currently a bound companion, and dismiss it through `world/rules/party.py::leave_party(npc, actor, reason="dismissed")`. Dismissal SHALL NOT change affinity in either direction, SHALL notify the actor with the fixed Traditional Chinese dismissal message shared with the `leave` command, SHALL publish a full snapshot at one newer revision, and SHALL NOT assign party or affinity state directly. A missing, no-longer-present, or unbounded NPC SHALL reject synchronously with a stable code and no state change.

#### Scenario: Webclient dismissal removes the binding
- **WHEN** an actor submits `explore.party_leave` for a present bound companion
- **THEN** the binding is removed through `leave_party(reason="dismissed")`, affinity is unchanged, and the actor receives the dismissal notification

#### Scenario: A webclient leave on an unbounded target rejects
- **WHEN** an actor submits `explore.party_leave` for a present NPC that is not a companion
- **THEN** the adapter rejects with a stable reason and no party or affinity state changes
