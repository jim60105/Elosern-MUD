# Narrative Memory, Cognition, and Collaborative Story Design

Date: 2026-10-03

Status: Written review approved. Nineteen OpenSpec proposals for W0–W3 are
committed on master; Section 10 records the proposal register and parallel
batches. Section 6.4 records one retracted assistant position that is overridden
by the user's approved explicit-presentation requirement.

## 1. Purpose and decision record

Elosern should remember what the player has done and continue the people and
stories the player cares about. Combat, exploration, skills, equipment, and
quests remain deterministic ways to make choices and experience consequences.
Generative systems organize and propose narrative content; they never write game
state.

This design supersedes the corresponding proposals in
`tmp/Elosern-AI-Narrative-System-Handoff.md` for the work described here. The
architectural source of truth remains
[the AI engine design](2026-07-29-ai-mud-engine-design.md). W0 must explicitly
amend its subsystem ownership list before implementation begins.

Approved product decisions:

- Automatic continuation is proactive but bounded. It develops existing world
  facts, player experiences, and invested storylines, rather than introducing
  unrelated stories automatically.
- Player-initiated collaboration may introduce a new storyline unrelated to
  earlier experiences. The player negotiates direction without learning plot
  secrets or predetermined outcomes.
- Correspondence supports non-contact narrative progression, not remote quest
  acceptance or physical actions.
- The delivery institution is **銀羽驛行**, with branches named **銀羽驛站**.
  Its identity accommodates future cargo services; cargo mechanics are not in
  scope.
- Dream collaboration allows six completed exchanges, followed by explicit
  confirmation or draft preservation and awakening.
- Dream collaboration is rendered with explicit sexual presentation, consistent
  with the game's established adult tone and canonical light-faith doctrine.
- The W1 demonstration NPC is **尤漢娜‧庫柏 (Yohanna Cooper)**. No other named
  demonstration NPC or plot is inherited from the handoff.

## 2. Architecture and ownership

### 2.1 Chosen approach

Add `world/narrative/` as an explicitly named deterministic subsystem owning its
own persistent narrative data. Reuse existing infrastructure rather than
introducing a general agent framework or converting the game to event sourcing.

Responsibilities within the package:

| Area | Responsibility |
| --- | --- |
| Events | Durable narrative facts and deterministic projection |
| Memory | Owner-scoped records, revisions, selection, and maintenance |
| Threads | Cross-conversation and cross-quest continuity |
| Correspondence | Letters, delivery settlement, collection, and reading |
| Attention | Deterministic eligibility and candidate ranking |
| Context | Read-only context construction, rendering, budgets, and snapshots |
| Authoring | Creative sessions, direction confirmation, and request lifecycle |
| Director orchestration | Validated beat application and scheduling |

These are responsibility boundaries, not a requirement to create empty packages
up front. Each implementation change creates only the modules it actually uses.

Existing owners retain their responsibilities:

- `world/rules/` applies general actions and relationship changes.
- `world/quests/` owns quest lifecycle and materialization.
- `world/maps/` owns room and instance lifecycle.
- `world/lore/` and `world/skills/` remain registry/read-only systems.

Narrative orchestration invokes the relevant deterministic owner. It does not
write another subsystem's data directly. Generation code remains under
`world/ai/` and cannot obtain mutation authority.

### 2.2 Generative capabilities

NPC dialogue and correspondence share cognition but use channel-specific
contracts. The dream collaborator negotiates creative direction. StoryDirector
turns approved requests or eligible continuation candidates into beat proposals.
ScenarioDirector compiles beats requiring quests into `QuestBlueprint` proposals.
Memory summarization creates derived retrieval material.

The dream collaborator and StoryDirector must be separate capabilities with
separate context permissions. They may use the same deployment profile. A
shared model does not imply shared conversation history or access to secrets.

Reuse `LLMProfile`, the existing client, prompt library, and guardrail. A thin
invocation boundary associates capability, prompt version, schema, immutable
context snapshot, validators, and trace identifiers. It must not grow into a
second client, retry system, or stateful agent framework.

### 2.3 Alternatives rejected

Distributing memory and communication across existing AI modules would duplicate
knowledge selection and bind continuity too closely to quest lifecycle. Complete
event sourcing would require a much broader rewrite than narrative traceability
needs. The selected subsystem approach provides shared cognition without either
cost.

## 3. Truth, cognition, and persistence

### 3.1 Distinct data authorities

| Data | Meaning | Authority |
| --- | --- | --- |
| `NarrativeEvent` | A committed, observable narrative occurrence | Deterministic core |
| `MemoryRecord` | What one character knows, was told, or believes | Owner-scoped cognition with provenance |
| `StoryThread` | Continuity across events and interactions | Deterministic lifecycle; separate facts from plans |
| Creative session/request | Desired experience and negotiated constraints | Authoring data, not in-world knowledge |

Events store structured facts, participants, location when applicable, world tick,
visibility, salience, and source identifiers. They do not capture every low-level
action indiscriminately. Projectors select occurrences worth future reference.

A statement and its truth are different. If a letter claims that a dragon lives
in a cave, the authoritative occurrence is receipt of that claim. The recipient
may remember being told about a dragon; this does not establish a dragon in the
world. Generated summaries and player text never replace authoritative facts.

### 3.2 Storage and transaction boundary

Use indexed Django tables for growing narrative history rather than a single
unbounded Evennia Attribute list. Specific model definitions and indexes belong
to the owning subproject designs.

For covered gameplay paths, the committed result and its durable narrative event
must be recorded in the same database transaction. The existing `EventLog`
dataclass alone is not a persistent stream or a durable source ID. W1 must define
stable source identities and the adapters at actual commit boundaries.

Memory projection may run after commit, but its source and pending progress must
be durable. It must be possible to recover after process interruption and to
process a source again without creating duplicate records. A transient callback
alone does not meet this requirement.

This is a narrative durability contract, not authorization to rewrite unrelated
action workflows. Reuse existing transactions and integrate the covered paths.

### 3.3 Memory records and revisions

A record identifies its owner, creation tick, category, tier, content, salience,
knowledge scope, confidence, subjects, source references, and relevant threads.
Derived records also identify their generation. Knowledge scopes distinguish
witnessed, told, inferred, and genuinely public information.

Content and provenance are immutable. Changes to availability, tier, decay,
relationships between records, and supersession are represented by revisions.
Current effective metadata may be materialized for efficient reading, but revision
history must remain recoverable.

Source references include durable narrative events and, for conversation
summaries, the preserved dialogue or correspondence records being summarized.
Historical retrieval may include superseded records; normal retrieval excludes
inactive or superseded material.

### 3.4 Knowledge before retrieval

Determine access before scoring. A high relevance score cannot grant knowledge.
An uninformed NPC receives neither hidden facts nor another owner's private
memory. Letter content enters NPC cognition at delivery and player cognition at
first reading after collection.

Private authoring discussions are not NPC memories. The dream collaborator gets
creative preferences and a spoiler-filtered adventure summary. Hidden answers
used by StoryDirector are absent from the collaborator's context.

## 4. Recall, dialogue history, and prompt assembly

### 4.1 Memory selection

Retain `core`, `working`, and `archive` tiers. Core holds persistently relevant
cognition; Working holds recent or active context; Archive holds long-lived
episodes. Tier is a loading strategy, not a truth rating.

Before a major generation, perform permission filtering, bounded fixed-memory
selection, and Fast Recall. The first retrieval implementation uses Traditional
Chinese tokenization, entity matching, and BM25 without embeddings or a vector
service.

Use precision-first thresholds calibrated on project-owned labeled cases. Return
no recalled memory if none is sufficiently relevant. Metadata bonuses only
rerank candidates with relevant lexical overlap; they cannot independently
introduce an unrelated high-salience record. Deterministic owner and explicitly
requested thread filters define scope before ranking.

Deep Recall is a later read-only capability with bounded calls, result count, and
tokens. It uses the same access policy. A generation cannot search other
characters' private cognition by choosing a different owner argument.

Owner memory-generation counters and thread revisions invalidate immutable
retrieval snapshots whenever effective data changes. Cache rebuilding must not
alter search results or require persistent vector infrastructure.

### 4.2 Dialogue versus correspondence

Preserve append-only turn streams per player/NPC pair, with explicit epochs for
compaction and natural boundaries. This is separate from the existing
`world/rules/dialogue.py` session that tracks the current interaction target.

Letters have their own body, delivery ticks, collection/read state, and reply
links. Do not append the entire correspondence archive to the face-to-face turn
stream. Shared memories and thread references provide continuity between the
channels. An undelivered letter is absent from its recipient's context.

### 4.3 Prefixes and budgets

Order prompt sections by stability: global rules, world digest, capability
contract, character anchor, epoch summary, then append-only turn frames. Put
changing location, relationships, recall results, and current affordances in the
new turn frame rather than rewriting older prefixes.

Historical frames retain the information supplied at their original tick.
Current frames identify current authoritative state and supersession clearly.
Persona or prompt-version changes invalidate the affected prefix and epoch as
needed; correctness takes precedence over preserving cache hits.

All sections have configured soft selection targets and hard rendered-input
bounds. Selection and final assembly use the same rendered representation,
including headings and attribution. Profile context limits reserve capacity for
completion, Deep Recall, and estimation safety margins. Numeric token limits and
recall thresholds are calibrated in the owning change rather than assuming a
universal 32k model.

Stable ordering, deterministic tie-breakers, and rendering versions make repeated
assembly reproducible. Provider caching is optional. Prefix hashes and reported
cached-token usage are observability data, never functional prerequisites.

## 5. 銀羽驛行 correspondence

### 5.1 Institution and scope

銀羽驛行 is a cross-settlement courier network. Its branches are 銀羽驛站. The
institution may eventually carry goods, but the current feature transports
letters only. Do not add parcel placeholders, cargo inventory rules, or speculative
payload types.

Keep delivery scheduling responsibilities distinct from letter content and
reading responsibilities. Future cargo design can reuse appropriate scheduling
concepts without inheriting letter-specific acquisition rules automatically.

### 5.2 Sending and guaranteed delivery

Players send free-text letters from a branch to an established recipient
character, addressed by persistent identity rather than location. Validate the
recipient and body bounds before committing the send.

Delivery takes a fixed **one game hour**, configurable as a deterministic rule.
It does not depend on distance, recipient movement, real elapsed time, or model
latency. Delivery records remain associated with durable identities rather than
a currently instantiated room occupant.

Advance delivery using authoritative world time, including the actual ticks
crossed by sleep or waiting. Do not assume a requested time skip completed if the
existing skip rules interrupted it. Settlement is idempotent.

NPC letters transition from sent to delivered at the due tick. Delivery always
succeeds once sending has been accepted; there are no receipt conditions,
location searches, or delivery-failure mechanics. For this simplified service,
an NPC gains the letter's stated information at delivery.

### 5.3 Player collection and reading

Player letters transition from sent to available-for-collection, then collected,
then optionally read. Available is not collected, and collected is not read.

Any branch can collect all due letters for the player. There is no home-city
restriction. Away from a branch, the personal letter menu exposes collected
letters only, not uncollected bodies. Previously collected letters can be opened
at any time. First reading establishes knowledge of the content.

The design does not specify exact command keys or layouts. The owning change must
update both player command documentation files and their contract tests when it
introduces the actual command surface.

### 5.4 Replies and allowed effects

NPC cognition can propose a reply to a delivered letter. Store its reply-to link
and source snapshot. Delivery is guaranteed; a response is not. Model outages
leave generation work pending rather than blocking delivery or fabricating text.
A generated outgoing reply starts its own one-hour delay when its send commits.

Allowed effects are information exchange, memories, clues, invitations as
statements, and deterministically validated relationship changes. Letter claims
cannot satisfy quest objectives. Letters cannot accept quests, confirm formal
appointments, transfer items, or execute physical actions.

Use channel-specific affordances and validators. Do not reuse a face-to-face
co-location gate unchanged, or give correspondence the entire dialogue intent
whitelist. An expressed willingness is remembered as speech, not automatically
converted into a formal commitment.

## 6. Collaborative dreams

### 6.1 Entry and sleep settlement

Sleeping offers an explicit dream-collaboration choice. Ordinary sleep can finish
without conversation; resting and waiting do not force the encounter.

Preserve existing sleep safety, duration, and restoration rules. Settle sleep
once before presenting the dream, with no second settlement when leaving.
Conversation exchanges do not advance world time. A fully restored character
may still enter the dream after a zero-duration sleep result.
Rejected sleep does not open a dream session. If sleep is interrupted, use its
actual committed outcome and the existing safety rules rather than pretending
the requested interval completed.

### 6.2 Counterpart and creative authority

The setting is a pure-white dream space with a bed and a goddess-like counterpart
whose true form cannot be resolved. Give the counterpart a stable persona, but do
not identify her as a specific deity or disclose canonical divine mysteries.

The world references informing this frame are
[the religion overview](../../lore/overview.md) and
[the light skill-tree lore](../../lore/skill-trees/light.md). The frame does not
establish that the counterpart is a material NPC or that she can guarantee future
events.

Negotiate themes, atmosphere, participants, desired emphasis, and exclusions.
Support both new-story requests and changes to the direction of existing threads.
Do not rewrite committed history, established personality, or deterministic
outcomes. Incompatible requests receive a concrete explanation and remain
unconfirmed until the player chooses a valid direction; never silently substitute
a different story.

Creative records are private authoring data. They confer no clues, items, quest
progress, persistent stat changes, skill advancement, buffs, or codex unlocks.
No age-based gameplay branch is introduced by this technical design. Existing
import age bounds remain unchanged.

### 6.3 Six-exchange contract

An exchange consists of one player message and one successfully delivered,
validated counterpart response. Opening text, confirmation buttons, transport
failures, validation retries, and duplicate submission do not consume exchanges.
Persist the count; reconnecting does not reset it.

Allow at most six completed exchanges and display the remaining count. Begin
converging by exchange five. Exchange six summarizes a spoiler-free direction
and introduces no new question. Independently bound rendered input size so one
large message cannot bypass the session budget.

At the cap, stop free-text input and offer explicit confirmation or draft
preservation. Confirmation creates a versioned creative request which passes
deterministic validation before scheduling. A confirmed version submits only
once. Early departure uses the same choices; incomplete or unconfirmed content
remains a draft.

Ending and awakening require no additional model call. Cancellation, disconnect,
or model failure preserves committed sleep and saved session progress. Resume
saved discussion on a later entry; never duplicate sleep settlement or creative
submission.

### 6.4 Approved explicit presentation contract

The dream session is presented explicitly. The player and the obscured
goddess-like counterpart have sex on the bed in the pure-white space while they
negotiate story direction. Non-graphic presentation is rejected because it would
conflict with the game's existing mechanics and world canon. The repository
already defines a live sexual-state subsystem:

- `world/rules/sexual_state/handler.py` owns ordered `arousal`, `wetness`,
  `shame`, `exposure`, and `climax_phase` traits, a bounded pleasure gauge,
  lifetime occurrence counters, and `climax_today`.
- `world/rules/sexual_state/pleasure.py` maps pleasure `0..100` onto five
  canonical `AROUSAL_LEVELS` bands from `world/lore/sexual_vocab.py`.
- The religion lore in `docs/lore/skill-trees/light.md` binds pleasure to
  vitality, and `docs/lore/overview.md` defines orgasm as a public blessing.

Dream prose must use that established vocabulary for bodies, stimulation,
arousal, and climax rather than introducing a separate sanitized register. The
interaction is continuous conversation during sex, so each generated exchange
carries scene prose and the counterpart's dialogue as one validated response.

The session uses a separate dream arousal track. It is deterministic and bound to
the six-exchange budget, so each completed exchange advances a configured
pleasure delta through the same canonical five bands and may enter
`climax_phase` during the convergence or ending sequence. The track is scoped to
the dream session and is **not** a live `SexualState` handler: it must not write
persistent traits, pleasure gauges, sensitivity, lifetime counters,
`climax_today`, buffs, skill advancement, codex unlocks, or relationship state.
The deterministic sleep settlement already committed in Section 6.1 remains the
sole physical-restoration path; dream climax is its narrative presentation, with
no second restoration settlement.

Explicit prose is generated through the existing guardrail pipeline rather than
being authored as fixed strings in this design. The validator accepts explicit
sexual content for this capability while continuing to reject hidden metadata,
system fields, spoilers supplied outside the collaborator's permitted context, and
claims that authoritative state has changed. The model's own dream arousal track
is server-computed; a generated response cannot silently advance it and must
describe the server-supplied phase.

Voluntary exit and the six-exchange cap both offer confirmation or draft
preservation before the ending sequence. If the server-computed track has reached
climax, the ending renders the canonical post-climax phase before the white space
fades and the player awakes. If the player exits earlier, the scene fades without
forcing a climax. The ending itself requires no additional model call, so model
failure cannot trap the player in the dream.

## 7. Threads, attention, and directors

Threads retain origin, participants, factual summary, unresolved questions,
commitments established by valid gameplay, memory references, and development
ticks. Lifecycle states are active, dormant, resolved, and abandoned. Inactivity
alone is not proof of abandonment. Quest completion need not resolve its parent
thread.

Automatic candidates arise from existing experiences, relationships, clues,
correspondence, and invested threads. Unrelated new stories require an explicitly
confirmed creative request. Confirmation approves direction, not an outcome or
an immediate historical fact.

Attention is deterministic and does not call the model. Filter for knowledge,
location, scheduling, and executable feasibility before scoring. Engagement comes
from observable actions such as initiated visits, sustained correspondence,
questions about clues, and participation. Passive receipt alone is not high
engagement.

Rank eligible candidates using unresolved stakes, engagement, relationships,
deadlines, location relevance, repetition, and cooldown. Limit the candidate set
provided to the director. Exact weights and focus limits are calibration choices
for W3, not permission to hide or discard existing story state.

Each decision schedules at most one new beat and may choose none. Prevent
conflicting concurrent arrangements within the same thread. Beat proposals can
represent a follow-up, letter, clue, invitation, or quest seed. Only capabilities
implemented by deterministic owners can be materialized.

ScenarioDirector accepts the validated beat and its allowed narrative context
when a quest is needed. SceneBuilder and quest runtime remain authoritative.
Prose cannot complete objectives or fabricate past actions. Revalidate changed
state before applying proposals generated from older snapshots.

## 8. Failure handling and observability

Deterministic gameplay remains playable with all generation and image services
offline. Reuse guardrail retry/degrade behavior rather than adding a second retry
policy.

- Failed dream generation allows awakening or later retry without undoing sleep.
  Saved confirmed requests can undergo deterministic validation offline.
- Letter delivery continues offline. Eligible reply generation remains pending;
  no response is promised or fabricated.
- Failed summaries leave original records intact. Recall and snapshot rebuilding
  run without network services.
- Exhausted beat validation produces no new content and leaves the thread intact.
  Failed quest compilation creates no partial quest or replacement filler.
- Durable derived work is idempotent. A process restart cannot duplicate memories,
  replies, creative submissions, or scheduled beats.

Every important generation stores a context snapshot identifying capability,
prompt/schema/rendering versions, immutable source references, section hashes,
budget accounting, and truncation decisions. Mutable references also need the
revision read at generation time. A hash identifies content; it is not a claim
that an omitted payload can be reconstructed.

Full debug payloads require explicit opt-in and controlled storage. Normal logs
contain identifiers and counts, not player text, secret values, complete persona,
or complete prompts. All production logging uses `world.observability` with
stable event names, context dictionaries, and exception chains per the existing
catalog. Subproject designs extend the catalog where a new boundary is introduced.

Record actual input/output tokens, provider cached tokens when available, stable
prefix estimates, selected source IDs, retries, degrade reason, and latency.
Provider-specific cache controls belong to the transport adapter and profile
capabilities, not the narrative domain.

## 9. Verification and acceptance

Follow the repository's fixture, shard-ownership, traceability, and focused-test
rules. No permanent test calls a live model or image service.

Required behavior evidence:

1. Paired informed/uninformed roles establish that knowledge filtering precedes
   retrieval, including undelivered and collected-but-unread letter boundaries.
2. Project-owned synthetic labeled retrieval cases establish relevant recall,
   rejection of unrelated salient episodes, and intentional historical retrieval.
   Measure Recall@1, Recall@2, false positives, and latency before setting gates.
3. Rendered-prompt tests establish stable ordering, append-only prefixes across
   turns, shared global prefixes across actors, and total budget limits. Test
   these behavioral invariants, not copied prompt wording or source text.
4. Time-skip integration crosses delivery deadlines and establishes guaranteed NPC
   delivery, player branch-only acquisition, unrestricted rereading, and
   duplicate-settlement safety.
5. Dream-session tests establish the sixth-exchange boundary, explicit
   confirmation, resumability, no duplicate submission, no second sleep
   settlement, and no writes to a live `SexualState` handler or other persistent
   character effects. Offline fallback establishes awakening without additional
   model output, not suppression of explicit content.
6. Proposal tests establish rejection of unsupported effects, stale-state conflicts,
   letter-driven quest completion, and writes across unauthorized owners.
7. Snapshot tests establish source provenance and revision identity across retries,
   compaction, and summary supersession.
8. Offline smoke scenarios establish sleep, delivery, recall, and the deterministic
   game still work while generation is unavailable.

Pure behavior fixtures remain synthetic. Tests naming shipped lore require the
existing data-contract registration. Register every new Evennia test module in
exactly one shard. Obtain canonical main-spec requirement IDs from the traceability
tool rather than constructing them.

Before each implementation handoff, run the focused tests, actual changed-path
smoke scenario, contract gate, and applicable OpenSpec validation. Broad browser
and complete evidence gates remain CI-owned.

## 10. Roadmap and dependency boundaries

There are **five workstreams, W0 through W4**. W0 through W3 are decomposed into
**nineteen OpenSpec change proposals committed on master** (validated with
`openspec validate --all --strict`: 284 passed, 0 failed). W4 remains deferred
without artifacts; its prerequisites are documented in
`openspec/changes/narrative-subsystem-ownership/design.md`. Proposals exist;
none is applied or implemented yet.

### W0 — Explicit architecture amendment

Amend the AI engine design and repository ownership instructions to name
`world/narrative/` and its persistent responsibilities. Preserve existing owners
and the generative/read-only boundary. This is the prerequisite for all later
implementation.

### W1 — Yohanna's memory vertical slice

Order: durable event identity and commit integration; owner-scoped memory and
projection; tokenizer/ranker/retriever and labeled calibration cases; context and
snapshot invalidation; NPC dialogue integration.

The demonstration NPC is **尤漢娜‧庫柏 (Yohanna Cooper)**. Her hereditary
barrel-making family name connects the authored character naturally to the guild
artisan circle. Other personality and background details are authored during W1
under the naming and lore conventions. Do not import the handoff's missing-family
or mine-investigation plot, promises, identifiers, or example dialogue.

Acceptance chain:

1. The player protects Yohanna in an initial combat encounter.
2. Deterministic commit records the corresponding narrative event.
3. Projection creates an episode in Yohanna's cognition, with valid observation
   and provenance.
4. Several game days later, the player talks to her again.
5. Fast Recall selects that episode for a related topic and rejects unrelated
   topics.
6. Dialogue can reference the shared experience using the selected context.

This verifies mechanics, not a particular authored personality or line of prose.
Permanent mechanics tests use synthetic actors. A local controlled generation
smoke establishes context assembly and downstream response; live model wording is
not a deterministic automated acceptance assertion.

W1 does not require StoryThread or StoryDirector. Its durable source references
provide later integration without a fake thread implementation.

### W2 — 銀羽驛行 correspondence

Order: letters and delivery settlement; sending/collection/reading surface;
owner-scoped free-text replies; shared memory integration.

Acceptance: a player and NPC can continue information exchange without meeting,
with guaranteed delayed delivery and the approved collection boundary.
Correspondence is functional without StoryThread. Explicit thread linkage is
added by W3 once that subsystem exists, rather than making W2 depend on a future
placeholder.

### W3 — Continuity and collaborative story direction

Order: thread lifecycle and linkage of existing events/memories/letters; dialogue
epoch and stable-prefix integration; creative sessions and versioned requests;
attention ranking; StoryDirector beat scheduling; ScenarioDirector compilation.

NPC dialogue epoch work can proceed as an independent bounded change after W1;
it does not depend on implementing the dream interface first.

Acceptance: automatic existing-story continuation and confirmed player-originated
new directions become validated, executable beats. The dream technical workflow
uses the approved six-exchange contract with the explicit presentation contract
of Section 6.4.

### W4 — Maintenance and expanded recall

Add Working-to-Archive consolidation, decay, supersession lineage, permissioned
Deep Recall, and administrative inspection. Preservation of originals is required
from W1; expensive consolidation is not a prerequisite for the first slice.

Evaluate embeddings only after labeled failures demonstrate an unmet retrieval
need. Cargo delivery requires its own future design, not a hidden W4 task.

### Dependency summary

The delivery sequence is W0 → W1 → W2 → W3. W4 maintenance builds on the
foundations it actually uses and need not block W2 or W3. Individual proposals must
identify their real prerequisites; workstream labels do not imply that every
change in a workstream is mutually dependent.

### Proposal register

| Change | WS | Responsibility | Depends on |
| --- | --- | --- | --- |
| `narrative-subsystem-ownership` | W0 | Authorize `world/narrative/` as owner of persistent narrative data (documentation-only, `skip_specs`) | — |
| `narrative-event-commit` | W1 | Persist selected encounter facts and restart-safe projection work at real gameplay commits | ownership |
| `narrative-owner-memory` | W1 | Owner-scoped cognition with immutable provenance and recoverable revisions | event-commit |
| `narrative-fast-recall` | W1 | Precision-first Traditional Chinese BM25 recall with labeled calibration fixtures | owner-memory |
| `narrative-context-snapshots` | W1 | Rendered cognition budgets, immutable source snapshots, cache invalidation | fast-recall |
| `yohanna-memory-dialogue` | W1 | Durable NPC dialogue integration and the Yohanna protection/revisit demonstration | context-snapshots |
| `correspondence-delivery` | W2 | Fixed one-game-hour scheduling and atomic guaranteed delivery settlement | yohanna-memory-dialogue (rollout gate) |
| `correspondence-player-surface` | W2 | Branch send/collect and portable reading of collected letters | delivery |
| `correspondence-npc-replies` | W2 | Optional pending NPC replies with channel-specific effect gates | player-surface |
| `correspondence-memory-projection` | W2 | Delivered/read letter cognition, claims kept distinct from facts | npc-replies |
| `narrative-story-threads` | W3 | Factual thread lifecycle and real event/memory/letter/dialogue linkage | memory-projection |
| `dialogue-epochs-stable-prefixes` | W3 | Dialogue compaction epochs and stable versioned prompt prefixes | yohanna-memory-dialogue |
| `dream-authoring-records` | W3 | Private drafts and explicitly confirmed validated request versions | story-threads |
| `dream-session-lifecycle` | W3 | Durable six-completed-exchange accounting and confirm/draft departure | authoring-records |
| `dream-explicit-presentation` | W3 | Approved explicit exchanges using a server-owned session arousal track | session-lifecycle, context-snapshots |
| `dream-sleep-surface` | W3 | Optional dream attached to sleep; browser/text confirm-draft-awaken surfaces | explicit-presentation |
| `narrative-attention` | W3 | Deterministic filter/rank of invested-story and confirmed-request candidates | authoring-records |
| `story-director-beats` | W3 | At most one validated executable beat per decision, idempotent scheduling | attention |
| `scenario-beat-compilation` | W3 | Beat-scoped ScenarioDirector entry with no-content degradation | story-director-beats |

Main-spec reconciliations recorded during proposal: destructive replacement of
`npc-dialogue` bounded-window and byte-identical-payload contracts (W1, refined
by epochs); `world-clock` stage-order insertion of a correspondence settlement
stage; beat-scoped no-template-fallback entry beside the generic
`scenario-director` degradation contract; layer-scoped guardrail acceptance for
the approved explicit dream capability without touching the live
`SexualState` handler.

### Parallel batches

Topological waves; within a wave, changes are dependency-independent.

| Batch | Changes (parallel-capable) | Notes |
| --- | --- | --- |
| 1 | `narrative-subsystem-ownership` | Single documentation gate |
| 2 | `narrative-event-commit` | |
| 3 | `narrative-owner-memory` | |
| 4 | `narrative-fast-recall` | |
| 5 | `narrative-context-snapshots` | |
| 6 | `yohanna-memory-dialogue` | |
| 7 | `correspondence-delivery` ∥ `dialogue-epochs-stable-prefixes` | Disjoint conflict groups; epochs stay independent of the dream UI |
| 8 | `correspondence-player-surface` | |
| 9 | `correspondence-npc-replies` | |
| 10 | `correspondence-memory-projection` | |
| 11 | `narrative-story-threads` | |
| 12 | `dream-authoring-records` | |
| 13 | `dream-session-lifecycle` ∥ `narrative-attention` | Disjoint conflict groups |
| 14 | `dream-explicit-presentation` ∥ `story-director-beats` | Share prompt-registry/composition and authoring-lifecycle surfaces: serialize or use one integration owner |
| 15 | `dream-sleep-surface` ∥ `scenario-beat-compilation` | Disjoint conflict groups |

Every change additionally touches the shared repository files
`.github/evennia-shards.json`, spec-traceability annotations, and the
observability event catalog. Those are merge-coordination points for any
parallel pair, not dependency edges.

Shared code-surface conflict groups across waves: projection
progress/linkage (event-commit, owner-memory, delivery, memory-projection,
story-threads); context/history (context-snapshots, yohanna-memory-dialogue,
npc-replies, memory-projection, story-threads, epochs, explicit-presentation);
prompt registry/composition (yohanna-memory-dialogue, epochs, npc-replies,
explicit-presentation, story-director-beats, beat-compilation); authoring
lifecycle (authoring-records, session-lifecycle, explicit-presentation,
sleep-surface, story-director-beats); beat execution registry
(story-director-beats, beat-compilation).

Public W3 acceptance requires both the complete dream branch and the complete
director branch.

## 11. Non-goals and planning gate

Non-goals are cargo mechanics, vector databases, all-world NPC background
simulation, remote quest acceptance, narrative-text quest completion, automatic
unrelated-story creation, authoring-driven rewrites of committed history, and
age-based gameplay branching. Explicit sexual presentation in the dream session
is approved in Section 6.4 and is not a non-goal.

The nineteen proposals above are committed and strictly validated, and none is
implemented. Implementation follows the batch order in Section 10: apply
`narrative-subsystem-ownership` (W0) first, and never start a change before its
listed dependencies are applied.
