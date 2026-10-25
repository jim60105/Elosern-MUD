# Authored Dialogue Engine Design

Date: 2026-10-25
Status: Design and YAML/generated revisions approved in conversation; planning only.

## Goal and scope

Replace fixed single-response topics with AVG-style conversations across static NPC dialogue and generated dream-collaboration NPCs. Deliver a shared declarative scene player, conditional dialogue, possessed-companion conversations, topic chains, server-persisted reading and unread notifications. Playing published content requires no LLM. All existing static fixed-topic dialogue and the generated PhaseTopic response representation are replaced without compatibility paths or migrations.

The user explicitly authorizes discarding all existing fixed dialogue prose: it contains no important narrative that must survive. Preserve functional service and deterministic effect contracts, not old wording or informational composition. Rewrite every existing authored topic as a natural multi-line scene. Do not make unintended commitments on behalf of the player.

## Mandatory authoring prerequisite

Before implementation-time dialogue writing or review, the writer MUST read `tmp/story_settings/world_info.md`, together with the repository NPC-content skill and relevant canonical lore/profile registries. Pay particular attention to elves' social standing relative to other races, the rarity of elves, and the setting's distinctive religious beliefs. Do not replace these with generic fantasy assumptions. The design session deliberately does not read that file, at the user's request. If the file is unavailable at implementation time, content authoring is blocked until the source is available; do not invent substitute lore.

Dialogue must be in-character Traditional Chinese. NPCs never name commands, UI controls, or game mechanics. Register follows the speaker and setting. Unlock explanations belong to UI, not compulsory explanatory story branches.

## Architectural decision

Use a declarative scene engine, not an executable scripting language. Reusable scene data describes ordered speech and narration; a shared frontend player presents it. Dialogue-specific rules select a scene and authorize topic content. Existing deterministic owners apply game effects. No arbitrary script execution, new quest engine, in-scene branching choices, or per-line persistence is introduced.

Alternatives considered were a dialogue-only line list and a server-stepped or fully executable script engine. The selected design adds reusable presentation and condition selection without network round trips for every line or resumable script execution.

## Ownership and control

### Approved static YAML and generated DB source architecture

Static dialogue content lives in the flat `world/lore/dialogue/content/<NpcProfile.key>.yaml` directory. The existing stable profile key supplies filename ownership, independently of dbid, display name or service/dialogue key. The YAML contains no duplicate npc_id owner field. Sorted safe scanning discovers each file without manual registration, rejects duplicate mapping keys/unsafe tags/unknown profiles/schema or reference errors, validates the complete candidate, then publishes one immutable snapshot once at startup. No hot reload. This is a dialogue-specific exception to the architecture source's D9 Python-lore decision; unrelated lore remains Python.

YAML primitives and generated JSON use one pure immutable scene/topic parser and validator. Static profile existence is checked by the static provider only. Generated identities use package_id+role_id plus permitted phase and local topic/scene ID, never a static profile or global registry insertion. Exact collision-free identity encoding, source-aware ID bounds, primitive schema and wire/storage APIs are fixed in `openspec/changes/authored-dialogue-contracts/design.md`, Shared contract v2.

Generated content remains in existing immutable world/quests scene-package DB payloads. The production dream dispatch -> scene-specific ScenarioDirector prompt/schema -> deterministic package validation/publication path must produce complete actor-first scenes, variants, qualification/refusals and predecessors. PhaseTopic(keyword,response,effect_verb,effect_reference) and the resolver's topic.response extraction are explicitly cut over; generated NPCs have no permanent one-line exception. LLM output proposes data only. No git/source-directory writes, generated YAML, model-owned effects or private/generated entries in the static registry.

Both providers feed the same scene selection, all condition families, hidden/locked/open gates, safe hints, pure/qualified chains, possessed acting-body/owner semantics, manual playback, reading/completion and notifications. Runtime references must be canonical permitted or package-scoped. Existing world/quests publication, role binding, phase revision, knowledge and guarded escort/reunion authority remain deterministic. Existing effect allowlists/domain gates remain unchanged; qualification and effect authorization precede formal success body delivery. Freeform generation keeps its selected phase's permitted context and never receives locked formal bodies or unrelated private phases.

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

Persist reading and pure-chain progress by owning player, stable logical host and topic identity. Static hosts use profile identity; generated hosts use immutable package-role identity with phase-scoped topic IDs. Physical dbids remain presence/wire identities. Possession, save/reload and rematerialized bindings share the logical record. Phase changes retire deliveries/receipts without erasing reading when that same phase later returns. Track formal completion separately from refusal, opening and service playback. Refusal never reads protected content or satisfies formal predecessors.

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

## Proposal inventory

The 26 bounded planning changes comprise the original 24 revised proposals plus
`authored-dialogue-yaml-loader` and `authored-dialogue-generated-packages`. Each
row is one engineer-day of implementation, owns the listed artifacts only, and
carries its own tests and documentation. The authoritative interfaces are in
`openspec/changes/authored-dialogue-contracts/design.md`, Shared contract v2.

| # | Change | Direct prerequisites | Owned scope | Planning commit |
|---|---|---|---|---|
| 1 | `authored-dialogue-contracts` | none | Immutable scenes, typed topic declarations, identity encoding, shared reference catalog | `6e676db8` |
| 2 | `authored-dialogue-yaml-loader` | 1 | Sorted safe `content/<NpcProfile.key>.yaml` scan, whole-candidate rejection, immutable snapshot | `940cd538` |
| 3 | `authored-dialogue-runtime` | 1, 2 | Static YAML cutover, source-neutral selection, version-3 protocol | `eef542a3` |
| 4 | `authored-dialogue-playback` | 3 | Shared manual Vue scene player and synchronized stage attribution | `893cec1a` |
| 5 | `authored-dialogue-possession` | 3, 4 | Lawful possessed conversations, acting body versus owning player | `8f1681d5` |
| 6 | `authored-dialogue-social-identity` | 1 | Typed social identity, never parsed persona prose | `eb614701` |
| 7 | `authored-dialogue-physical-conditions` | 3, 5, 6 | Race, items, present companion, in-world time, skills, exposure; reference catalog builder | `30df1917` |
| 8 | `authored-dialogue-progression-conditions` | 7 | Owner guild rank, quest lifecycle, host-to-owner affinity | `133fd60f` |
| 9 | `authored-dialogue-availability` | 8 | Server-qualified hidden/locked/open projection and disclosure | `5d2e5952` |
| 10 | `authored-dialogue-locked-ui` | 9, 4 | Selectable locked refusal and canonical requirement hints | `5f21ee7d` |
| 11 | `authored-dialogue-reading-server` | 9 | Narrative-owned formal reading, delivery receipts, pure-chain sync | `bfab4510` |
| 12 | `authored-dialogue-reading-client` | 11, 10 | Memory-only completion retry and chain progression | `5151ade5` |
| 13 | `authored-dialogue-unread-notices` | 12, 15 | Persistent unread markers and deferred deduplicated unlock batches | `d4d857a1` |
| 14 | `authored-dialogue-refresh-physical` | 9 | Committed physical-source availability refresh | `09bab719` |
| 15 | `authored-dialogue-refresh-lifecycle` | 14 | Committed progression, presence, clock and control refresh | `fbf7dcc6` |
| 16 | `authored-dialogue-generated-packages` | 13 | Dream producer, scene schema, immutable DB publication, generated provider/effect cutover | `f0195978` |
| 17 | `authored-dialogue-content-guild` | 13 | `guild_staff` -> `content/altoria_guild_master.yaml` | `f67a76f6` |
| 18 | `authored-dialogue-content-lower-hospitality` | 13 | Eatery, tavern, lodging | `bfc52191` |
| 19 | `authored-dialogue-content-lower-civic` | 13 | Bathhouse, guardhouse | `d4fdbaef` |
| 20 | `authored-dialogue-content-middle-tools` | 13 | General store, forge, tailor | `d99425a4` |
| 21 | `authored-dialogue-content-middle-exchange` | 13 | Jeweller, alchemist, merchant hall | `7ced2465` |
| 22 | `authored-dialogue-content-upper-faith` | 13 | Temple, sanctum | `9c547f00` |
| 23 | `authored-dialogue-content-upper-civic` | 13 | Noble watch, drill yard, academy | `53ded8b8` |
| 24 | `authored-dialogue-content-ciaran-crafts` | 13 | Ciaran hailiel, vethiel, gwenaera | `02dede6f` |
| 25 | `authored-dialogue-content-ciaran-fare` | 13 | Ciaran lareneth, nireth, valwyn | `8b3617e7` |
| 26 | `authored-dialogue-content-ciaran-commons` | 13 | Ciaran elenis, teliel | `067e73f1` |

Content rows 17-26 each own disjoint `world/lore/dialogue/content/<NpcProfile.key>.yaml`
files plus their exclusive test and review files. No content row edits runtime code,
another slice's YAML, or `NPC_PROFILE_REGISTRY`. The exact file mapping is in the
Shared contract v2 coverage table.

## Parallel implementation batch

A wave begins only after every prerequisite change in earlier waves is merged to
the primary branch; completion on a feature branch is not sufficient. Changes in
one wave touch disjoint owned artifacts and may run concurrently. Apply workers
use `feat/<change-slug>` in `.worktrees/<change-slug>`; the supervisor serializes
merges, shared manifest integration, main-spec synchronization and archive.

| Wave | Changes | Why concurrent |
|---|---|---|
| 0 | 1 | Pure declarations and identity encoding; every later change reads it |
| 1 | 2, 6 | Loader owns the filesystem boundary; social identity owns profile/create/import shape; no shared files |
| 2 | 3 | Sole static cutover and protocol adoption; highest backend blast radius |
| 3 | 4 | Frontend player foundation |
| 4 | 5 | Possession needs the player and the cut-over context |
| 5 | 7 | First condition evaluator, extends the shared catalog |
| 6 | 8 | Extends the same evaluator and catalog sequentially |
| 7 | 9 | Sole projection and disclosure authority |
| 8 | 10, 14 | Locked UI is frontend choices; physical refresh is backend writers |
| 9 | 11 | Narrative reading storage and receipt/pusher backend |
| 10 | 12, 15 | Reading client is frontend store; lifecycle refresh is backend writers |
| 11 | 13 | Notification observation needs both predecessors merged |
| 12 | 16, 17-26 | Generated packages owns the backend generated cutover; ten content slices own disjoint YAML and are mutually independent |

Wave 12 runs eleven workers. Content workers serialize only their shared manifest
entries, which each slice adds in its own commit and the integration owner merges.
Generated packages writes no YAML, so it runs beside all content slices.

Critical paths:

`contracts -> yaml-loader -> runtime -> playback -> possession -> physical-conditions -> progression-conditions -> availability -> reading-server -> reading-client -> unread-notices -> generated-packages`

`... -> availability -> refresh-physical -> refresh-lifecycle -> unread-notices -> content-*`

The user approved these planning revisions. Parent review and planning
validation precede commits. No implementation, apply, worktree or archive is
authorized by this document.
