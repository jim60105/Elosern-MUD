# Authored Dialogue Engine Design

Date: 2026-10-25
Status: Design approved in conversation; written specification awaiting user review.

## Goal and scope

Replace fixed single-response topics with authored AVG-style conversations. Deliver a reusable declarative scene player, conditional dialogue, possessed-companion conversations, topic chains, server-persisted reading state, and unread notifications. No LLM is required. All existing authored fixed-topic dialogue is replaced in this change set, not retained as a compatibility path.

The user explicitly authorizes discarding all existing fixed dialogue prose: it contains no important narrative that must survive. Preserve functional service and deterministic effect contracts, not old wording or informational composition. Rewrite every existing authored topic as a natural multi-line scene. Do not make unintended commitments on behalf of the player.

## Mandatory authoring prerequisite

Before implementation-time dialogue writing or review, the writer MUST read `tmp/story_settings/world_info.md`, together with the repository NPC-content skill and relevant canonical lore/profile registries. Pay particular attention to elves' social standing relative to other races, the rarity of elves, and the setting's distinctive religious beliefs. Do not replace these with generic fantasy assumptions. The design session deliberately does not read that file, at the user's request. If the file is unavailable at implementation time, content authoring is blocked until the source is available; do not invent substitute lore.

Dialogue must be in-character Traditional Chinese. NPCs never name commands, UI controls, or game mechanics. Register follows the speaker and setting. Unlock explanations belong to UI, not compulsory explanatory story branches.

## Architectural decision

Use a declarative scene engine, not an executable scripting language. Reusable scene data describes ordered speech and narration; a shared frontend player presents it. Dialogue-specific rules select a scene and authorize topic content. Existing deterministic owners apply game effects. No arbitrary script execution, new quest engine, in-scene branching choices, or per-line persistence is introduced.

Alternatives considered were a dialogue-only line list and a server-stepped or fully executable script engine. The selected design adds reusable presentation and condition selection without network round trips for every line or resumable script execution.

## Ownership and control

Keep generative and presentation layers non-authoritative. `world/lore/` owns immutable authored registries; `world/rules/` owns dialogue eligibility and session writes. Persistent narrative reading records belong to the authorized narrative subsystem, through explicit deterministic APIs. Existing quest, equipment, affinity, and other domain owners retain their writes.

Distinguish the acting body, owning player character, and conversation host. Race, social identity, skills, carried items, and exposure use the acting body. Guild rank, quest state, affinity, and reading progress use the owning player. Affinity means the existing host-to-player relationship, including gains during possession; do not add NPC-to-NPC affinity.

Enable initiating authored conversations while possessing a lawful companion. This amends the old possession dialogue prohibition. Preserve present shopping behavior: possessed trades already use the commander's purse and the named member's bag. Do not reintroduce historical shopping restrictions or change unrelated action availability.

## Authoring model and conditions

A topic has a stable identity, a short menu label, ordered scene lines, optional prioritized content variants, optional refusal scenes, availability policy, and predecessor topics. A speech line explicitly identifies acting body or host; narration identifies neither. Authored topics start with a complete acting-body utterance. Consecutive lines may share a speaker. Conditions select among complete linear scenes; they do not create mid-scene choice branches. Provide a general fallback and deterministic explicit variant priority.

Conditions support conjunction and disjunction over:

- Acting-body race and structured social identity, never parsed persona prose.
- Owning player's minimum guild rank.
- Host affinity toward the owning player.
- Owning player's specified quest state, including accepted/in-progress, completed, and reward-claimed states where supported by the existing quest lifecycle.
- Acting body carrying a specified item; inspection does not consume it.
- A specified companion being a current party member and physically present.
- In-world time period, never real-world wall time.
- Acting-body ownership of a specified skill and, where applicable, its proficiency threshold.
- Acting-body effective exposure, using existing ordered vocabulary and `effective_exposure()`, including worn-equipment bias; support lower, upper, and inclusive range bounds.

Use authoritative existing registries and readers. Do not invent alternate rank orders, skill arithmetic, exposure bands, or blanket social hierarchies. Social treatment must respect the mandatory world source, including elves' standing and rarity. Reaction scenes are authored per NPC; exposure alone does not automatically change affinity.

Unlock hints are generated from the same condition declarations and their canonical display labels. Public hints intentionally disclose requirements, not protected scene bodies or private numeric relationship records.

## Topic availability and disclosure

Availability is hidden, visibly locked, or open. Hidden topics are absent from the menu. Locked topics expose only their permitted label, lock marker, requirement hint, and refusal scene; selecting one plays the refusal. Open topics deliver their authorized scene.

Separate pure reading chains from qualified additional topics. A pure chain may be delivered in full and revealed by the frontend after predecessor completion. Its server-persisted progress supports synchronization, not anti-cheat proof. It cannot authorize quest rewards or protected information. Any protected descendant must use server eligibility and must not be included in a pre-delivered chain.

For qualified topics, the server evaluates conditions before delivering protected bodies and rechecks selection against current context. Equipment changes and other relevant committed state changes refresh availability. Already playing scenes keep their selected variant unless the dialogue context is invalidated; they do not switch wording halfway through.

## Playback

Selecting a topic validates context and settles its existing deterministic effects once before playback. Playback and replay do not apply effects or advance world time.

The player clicks the message surface or presses Space/Enter. While typing, activation completes only the current page. A subsequent activation advances to the next page or line. Long lines retain one speaker across their pages. Starting each line synchronously updates text, name, and portrait emphasis. During possession use the acting companion's portrait and name. Narration emphasizes no speaker.

Hide topic choices while the scene is being read. Retain text-speed and reduced-motion preferences, but do not auto-advance these scenes. After the last page is fully visible, a further activation returns to choices and reports completion. Preserve the attributed transcript for review. Text-only clients emit the whole attributed scene in order; successful emission counts as completion for this non-paged interface and records the same reading progress. This does not constitute proof that a human read it.

## Reading state and notifications

Persist reading and pure-chain progress on the server, keyed by owning player, host NPC, and stable topic identity. Possession shares this state. Track formal-topic completion separately from refusal playback. Reading a refusal neither reads the protected topic nor satisfies a formal-topic predecessor.

Initially available unread topics show an unread marker. Locked topics show the lock rather than an unread marker. Newly unlocked formal content becomes unread even if the refusal was read. Changing only a scene's tone/identity variant does not reset topic completion. Relocking and reopening an already read topic does not repeatedly mark it unread.

On completion, synchronize state to other relevant connections. The server accepts completion only for delivered content in the relevant context; it does not validate timing or every line. Keep effect settlement and protected qualification independent of this acknowledgement.

Newly opened topics carry unread markers and produce one non-focus-stealing notification per unlock batch. Defer notifications until the current scene returns to choices. Reconnecting does not replay notification popups, but persistent unread markers remain. Track notification delivery separately from read completion so reload does not create repeated announcements.

## Recovery and invalidation

Persist the most recently delivered scene through the deterministic session seam, not its current line index. If the host and context remain valid, reload or reconnect starts that delivered scene at line one. Replaying does not submit a new topic selection, repeat effects, or reset existing completion.

Pending completion acknowledgements live only in frontend memory. Retry failed synchronization without forcing immediate rereading; do not claim saved state or reveal server-qualified content prematurely. Refresh, tab closure, or leaving the character may discard pending state. Server records then win: unread markers or an unadvanced chain may require rereading. No localStorage, IndexedDB, or durable retry queue is added.

Leaving midway is not completion. Existing movement, combat, host-departure/deletion, and invalidated-phase cleanup retire stale playback and choices. Preserve existing phase authority and historical transcript; do not continue obsolete scripts after invalidation. Refused eligibility or operational failure must not leak content or partially apply game effects. Existing logging facade and boundary-event requirements apply.

## Verification and acceptance

Use synthetic deterministic fixtures for behavioral tests and existing data-contract conventions for shipped-content review. Verify speaker/page transitions, consecutive same-speaker lines, narration, text-speed preferences, keyboard focus, and actual browser portrait emphasis. Exercise a real multi-line scene and a possessed companion unlocking a race-qualified scene.

Verify condition boundaries and combinations; item inspection without consumption; co-located companion requirements; in-world time; skill/proficiency; effective exposure changes from worn equipment; owning-player guild/quest/affinity semantics. Confirm server responses omit protected bodies before qualification and reject forged or stale selection.

Verify complete-versus-refusal reading, server synchronization, pure-chain ordering, first unlock notifications, repeated relock behavior, pending acknowledgement failure/retry/discard, reconnect replay, context invalidation, and exactly-once effects on replay. Exercise the same authored content offline and through the text interface. Update affected player command documentation, test ownership manifests, and OpenSpec contracts, preserving existing repository gates.

## Delivery decomposition

Design the complete contract together, then plan dependent implementation slices: declarative scene model and shared playback; possessed dialogue and condition evaluation; persistent reading/availability synchronization and notifications; complete authored-content replacement and end-to-end verification. Split content slices by existing registry domains if needed for one-workday OpenSpec changes. Every approved condition and all existing authored topics remain in scope across the full change set; this is sequencing, not a partial delivery.

Before proposals or implementation, obtain user review of this written specification. The next brainstorming step is the writing-plans skill, subject to the repository's specification-driven OpenSpec workflow. No implementation is authorized merely by committing this document.
