# NPC Persona Authoring and In-Game Editing — Design

**Date:** 2026-10-01  
**Status:** Conversation-approved design; implementation requires the dependent OpenSpec changes.  
**Scope:** Complete NPC characterization, replacement of provisional NPC content, deterministic and generative dialogue alignment, and a browser author-level editor opened from the interaction surface.

## 1. Goal and approved decisions

Every NPC must have a compact, individual character card that explains who they are and how they speak. Free-form LLM dialogue consumes that card. Scripted dialogue is written against the same card and is displayed verbatim, including when generative services are unavailable.

The player can select an NPC on the interaction surface, choose **編輯人物設定**, and edit the complete card in a dedicated window. This is an author-level capability available to an ordinary authenticated player, not an in-fiction discovery or affinity mechanic. Hidden identity is visible and editable there with a spoiler notice. Reading it does not change the player character's knowledge or quest state.

The user explicitly superseded the initial proposal to preserve existing NPC prose: **all existing NPC personas and authored NPC dialogue are provisional and must be rewritten in this change set**. A sample-only rollout, filling only empty fields, or preserving the old personalities as a compatibility baseline does not meet acceptance. After the initial replacement, subsequent player edits are durable and must never be overwritten by routine initialization or restart.

The approved compact card covers identity, appearance, personality, speech style, brief life story, habits/preferences, and optional social connections. Hidden identity is optional. NPCs do not need the player's full character-creation template. NPC-specific rewriting must not rewrite player preset cards or existing player characters, even when a companion currently obtains its persona from a player preset.

The user authorized writing this Superpowers document and then proceeding directly to `os-propose`; a separate writing-plans phase and another chat approval pause are not prerequisites for proposal authoring. No implementation is authorized by this document-writing request.

## 2. Current implementation and evidence

The following are current implementation facts, not proposed functionality:

- `world/rules/persona.py` provides a read-only `PersonaStore` over `entity.db.persona`, mounted by `typeclasses/entities.py`. It supports text and structured values. Its default prompt bounds are 600 Unicode code points per field and 2,000 for the combined block.
- `LLMNPC._persona_block()` in `typeclasses/npcs.py` already reads an NPC's persona into its dialogue system prompt. `world/ai/npc_dialogue.py` selects `personality`, `life_story`, `habit`, `identity`, `appearance`, and `social_connection`; it does not currently select a speech-style field.
- `PlaceDefinition` in `world/lore/settlements/places.py` contains host name/title, race/subrace/sex, profession, service identity, and component kwargs, but no individual persona reference. `world/rules/guild_economy.py` creates and reuses service hosts by component service identity.
- A read-only registry census on 2026-10-01 found **25 place hosts: 17 in capital_altoria and 8 in village_ciaran**. The dialogue registry contains **25 tables and 100 keyword responses**. These are the current baseline, not a permanent hard-coded ceiling or the total population of NPCs.
- `world/lore/dialogue/{guild,altoria,ciaran}.py` supplies `DialogueDefinition(greeting, responses)` rows. `world/rules/dialogue.py` returns authored strings. An unknown keyword currently uses a shared misunderstanding line.
- Additional creation paths include imported NPCs (`world/imports/loader.py`), starting companions (`world/rules/starting_companions.py`), temporary examination opponents (`world/rules/guild_exams.py`), and quest scene occupants (`world/quests/scene_builder.py`). Quest characterization currently carries only the three persona prose fields through a restricted schema and durable compile payload.
- Starting companions currently copy `PresetPersona.to_record()` from a player preset and add their relationship to the owning player. This shared source must be separated for NPC characterization without changing companion mechanics or the player preset's own persona.
- The player's current editor, `world/rules/persona_edit.py` and the character drawer, edits four player prose fields. It does not authorize arbitrary NPC editing and must not be reused by forwarding an untrusted NPC id as the player character.
- The interaction presentation already uses a selected target and its verb menu, including `DockVerbPopover.vue`. Existing drawers provide headers, focus management, and overlays. The new entry belongs to this interaction flow; no separate global NPC management page is needed.
- The existing OOB success-result `data` slot can carry bounded nested JSON, but prohibits reserved keys such as `revision`, `actor`, and `session` at every depth. Editor data must fit that contract instead of weakening it.

The architectural source is `2026-07-29-ai-mud-engine-design.md`. Current capability specs remain authoritative over historical implementation notes except for the explicit amendments in section 13.

## 3. Alternatives and decision

| Approach | Benefits | Costs | Decision |
|---|---|---|---|
| Shared compact NPC card using the existing persona storage and reader | Explicit voice, uniform editing and validation, one runtime narrative source | All NPC creation paths and existing content need integration | Selected |
| One free-text NPC biography | Small initial schema change | Easy to omit voice; difficult to validate completeness or provide a useful editor | Rejected |
| Require the full player card for every NPC | Maximum field reuse | Excessive writing and form complexity for ordinary and temporary NPCs | Rejected |

Runtime LLM rewriting of scripted dialogue was separately rejected by the user. There is no paraphrasing request, automatic script regeneration, or online dependency on the scripted path.

## 4. Compact card contract

### 4.1 Canonical NPC shape

Use the existing `entity.db.persona` attribute. A compact NPC card has exactly these seven top-level fields:

| Field | Shape | Requirement |
|---|---|---|
| `identity` | Object with `public` and `hidden` text fields | `public` required; `hidden` may be empty |
| `appearance` | Text | Required; a short visual description including relevant clothing |
| `personality` | Text | Required; traits plus a value, tension, or concrete interpersonal tendency |
| `speech_style` | Text | Required; wording/register, sentence rhythm, addressing habits, and relevant conversational behavior |
| `life_story` | Text | Required; a brief history consistent with established world facts |
| `habit` | Text | Required; concrete habits, preferences, or aversions |
| `social_connection` | Text | May be empty; describes relevant existing relationships, not executable relation grants |

A compact card is deliberately simpler than the player's structured appearance and social-connection shapes. The shared `PersonaStore` already supports these text values. Its generic/player shape handling remains intact. NPC compact-card validation belongs to a dedicated pure contract shared by NPC producers and the editor, not a global restriction on every living entity's persona.

Example shape, using illustrative prose rather than a shipped NPC's final characterization:

```json
{
  "identity": {
    "public": "在村中修補農具的鐵匠，遇到難修的工具仍願意接手。",
    "hidden": ""
  },
  "appearance": "袖口常有炭灰，圍裙補過數次；工作時把長髮束在頸後。",
  "personality": "寡言、重視承諾，對誇大的說法缺乏耐心；願意花時間幫人解決實際困難。",
  "speech_style": "句子簡短，直呼對方名字，不用敬語。先問工具哪裡壞了，再解釋能怎麼修。",
  "life_story": "接手家中的鍛爐後，長年替鄰人修補農具，比起製作華麗武器更熟悉日常器物。",
  "habit": "回答前會先檢查手邊的器物；喜歡合用的舊工具，討厭浪費材料。",
  "social_connection": ""
}
```

The display name, immutable NPC title, race/subrace/sex, canonical ages, profession, and service bindings remain existing mechanical/identity data. They are read-only context in the editor, not additional mutable fields in this card. Writing that the NPC is a different race or holds an office does not change those facts.

### 4.2 Validation and prompt budget

- All leaves are plain text. Normalize line endings and trim outer whitespace; do not interpret text as markup, commands, templates, or executable instructions. Rendering must escape text for its output surface.
- Each text leaf is bounded by the existing 600-code-point limit. Required leaves reject empty content. Optional leaves persist as empty strings so an intentional clear has an unambiguous representation.
- The rendered identity section, including its public/hidden labels, must fit the same per-section bound used by the NPC prompt reader. The complete labeled card must fit the existing 2,000-code-point persona block without truncation. Count labels and separators, not just form values.
- Validation and rendering share one field order and label policy. The editor reports both per-field and combined remaining capacity. Over-budget values are rejected with a named field or total-budget reason, never silently cut by the editor or accepted only to disappear from the prompt.
- The NPC prompt explicitly includes all seven fields, with `speech_style` adjacent to `personality`. Add its Traditional Chinese label. Optional empty values contribute no placeholder prose.
- General `PersonaStore` fallback and truncation behavior for other consumers remains unchanged. The stronger compact-card validation makes truncation unnecessary for valid NPC cards.
- Read APIs never initialize or repair a persona. Missing/corrupt persisted data produces an explicit unavailable editor result and an operational event; initialization and repair belong to deterministic lifecycle writers.

### 4.3 Persistence and versioning

Keep the runtime card at `db.persona`; do not maintain a second prompt-only or browser-only persona. The deterministic NPC persona service in `world/rules/npc_persona.py` owns a separate `db.npc_persona_meta` record containing the compact-card format version, content-generation marker, monotonic `persona_version`, and initialization provenance. Provenance identifies an authored profile or an offline/generated source; it is not another prose copy. Metadata is never placed inside `db.persona` or rendered into prompts. Only `persona_version` is projected into the editor's fixed response shape.

Every successful editor save that changes any leaf of the normalized card, including either identity leaf, increments `persona_version` in the same database transaction as the card write. A no-op is exact equality of the complete normalized card and succeeds without advancing the version. Changing a card and later changing it back still advances the version twice. A save compares the submitted expected version against the persisted version inside the same transaction as the update, including for a no-op submission. Per-session presentation revisions are insufficient because two browser sessions have independent presentation state.

All NPC persona writers use the same versioning policy, including import materialization, scene creation, the one-time cutover, and editor updates. Writes must be serialized across processes or use a database-backed conditional update; a read/check followed by an unguarded attribute assignment is insufficient. Rollback restores any affected Evennia attribute cache before another reader can observe it.

## 5. Definition ownership and complete content rewrite

### 5.1 Authored profiles

Add immutable, keyed NPC profile definitions under `world/lore/`, using the existing frozen-dataclass and domain-sliced registry pattern. A profile owns a compact card and bounded prewritten voice lines needed for greetings and ordinary fallback responses. Profiles are referenced through stable authoring identities, not display-name lookup.

Service hosts reference profiles through their place/roster definitions and retain the existing `service_id` reuse identity. Examination ranks reference examiner profiles. Starting-companion declarations reference NPC profiles separately from their mechanical player-preset reference. Handwritten quest NPC declarations carry or reference complete compatible characterization.

The profile registry is the authored source of truth; a live NPC's persisted card is the effective instance state after initialization and user edits. Startup must not treat those edits as registry drift to be repaired. A card edit affects only the selected instance, even when two NPCs originated from the same profile.

### 5.2 Required inventory

Before rewriting, enumerate every shipped NPC source and dialogue table. The implementation must maintain a reviewable source-to-profile/dialogue inventory, with no unassigned shipped entry. It includes:

1. All place hosts from every settlement slice, including the separate guild dialogue row.
2. Every authored guild examination opponent.
3. Every distinct starting-companion declaration, including its mandatory relationship to the owning player.
4. Every NPC-bearing offline quest template and authored scene prototype/characterization source.
5. Shipped NPC import examples and other production NPC seed records discovered by the creation-path inventory.
6. NPC greetings, keyword responses, misunderstanding replies, and offline conversational fallback prose supplied by these sources.

The observed 25 tables and 100 keyword responses are an audit starting point, not a substitute for enumerating the remaining sources. Final acceptance compares actual source registries with this inventory so additions during implementation cannot be silently omitted.

### 5.3 Writing rules

Rewrite every listed NPC's card and all corresponding authored dialogue. Do not preserve provisional personality merely because it already exists, copy one profession-wide persona, or make otherwise identical dialogue distinct only by a name/catchphrase substitution.

Ground characterization in existing names, world geography, species context, service role, and established relationships. Give each authored character a recognizable combination of outlook and speech behavior. Full biographies, mandatory secrets, and elaborate networks for every incidental NPC are not required. Cross-reference real world facts rather than inventing new quest rewards, access conditions, NPC relationships, or historical events that contradict current lore.

Preserve mechanical semantics of keyword choices, service guidance, quest listings, inventory, prices, and command availability. Dynamic service information remains authoritative; any authored framing around it must not falsify it. Operational errors remain system messages rather than forced in-character speech.

Companions receive fully rewritten NPC personas; their player-preset counterparts remain unchanged. Preserve actual owning-player relationship facts when constructing their new social text, without copying the provisional persona wholesale.

A deterministic script line is authored against the initial profile and is not recompiled after an in-game persona edit. The editor must state this limitation. There is no fixed-dialogue editor or automatic paraphraser in this scope.

## 6. NPC lifecycle and offline behavior

### 6.1 New instances

Every production creation path completes a valid compact card before publishing an NPC as usable. Validation occurs before persistence where possible and within the owning all-or-nothing creation transaction otherwise. Preserve existing age bounds, name/title validation, stat authority, and service assembly rules.

- **Service hosts and examiners:** resolve the complete authored profile at creation; missing references reject authored data instead of silently using a generic personality.
- **Starting companions:** use the NPC profile plus the factual owner relationship. Do not mutate or copy back into player presets.
- **NPC imports:** validate the compact-card contract using the target typeclass-aware import validation path. The discriminator is the resolved class actually passed to `validate_character` and instantiation: `issubclass(typeclass, NPC)`, not a typeclass string claimed inside the record. New NPC imports provide a complete valid card; all shipped examples are updated. Non-NPC/player imports retain their existing opaque persona contract. Valid NPC import text persists as validated, not summarized or rewritten by a model.
- **Generated quests:** extend the proposal shape, guardrail validator, deterministic characterization validator, compile contracts, durable payload codec, restore path, and scene materializer together. A persona must survive both compile and restore unchanged. Revalidate at materialization so a forged internal requirement cannot bypass validation.
- **Offline quest generation:** use fully authored templates or deterministic selection among coherent, eligible persona bundles. Selection is based on stable instance identity/seed and already known role/world facts, then persisted once. Select whole compatible bundles rather than independently drawing contradictory adjectives, histories, and speech rules. There must be more than one eligible voice where ordinary repeated-role generation needs variation; this is not a promise of mathematically unique personalities for an unbounded population.
- **Other production creation paths:** inventory and connect them to the same initializer. Do not hide a missing writer behind lazy creation in `look`, dialogue, or editor reads.

If LLM characterization is invalid, use the existing bounded proposal failure/degradation path, whose offline alternative now also supplies a complete card. No new network retry subsystem is introduced. No partial NPC or partially applied persona survives a failed spawn.

This design does not convert every plain `NPC` to `LLMNPC`, invent conversation ability for non-speaking entities, or create new quest/merchant capabilities. Every NPC has a persona and an author editor; existing conversational capabilities determine which dialogue paths it can use. `Monster` is a separate family and is not made a character-card NPC by this change.

### 6.2 Existing-instance cutover

The user authorized replacing provisional NPC persona data. Perform one bounded, deterministic content cutover after all replacement profile data and creation-path changes are available. This is an exclusive boot/lifecycle operation: do not admit gameplay, editor actions, imports, or new spawn writers while it runs. Run it before the new generated-quest restore validator reads pre-cutover payloads. Refuse concurrent attempts rather than adding network-style retries or relying on SQLite row locks.

Precompute and validate replacements for every existing `NPC` family instance lacking the new content-generation marker. Resolve known provenance to its rewritten profile; for an unclassified/imported/dynamic instance, construct a complete offline card from its stable identity and existing mechanical/world facts. Do not preserve its old persona text as a fallback. Preserve object ids, location, party and quest bindings, inventory, traits, schedules, names/titles, and other gameplay state. Existing conversation transcripts are not retroactively rewritten.

Include durable generated-quest characterizations, including occupants not yet materialized, in the same cutover inventory. Replace their old optional three-field prose with a complete new card, using the durable quest/stage/occupant identity and known role/location facts as the stable source. Preserve quest ids, objectives, binding ids, stages, and mechanical requirements. For an already materialized occupant, use the same replacement baseline as its durable declaration. Do not carry forward provisional personality, life story, or habits merely because the old payload stored them. Recompute a starting companion's factual owner relationship from its existing binding and declaration during this cutover; ordinary editor saves and reads do not regenerate that text.

Apply all planned instance cards, affected durable characterization payloads, and their cutover/version markers in one database transaction, not a sequence of partially completed batches. Failure must leave the prior state intact, restore affected attribute caches, and identify the affected source/entity; it must not mark an incomplete cutover as successful or admit players against a partly rewritten world. Do not delete and respawn NPCs merely to replace their prose. The cutover is the explicit exception to the project's default avoidance of data migrations, not permission to add general migration infrastructure or a runtime legacy-payload compatibility decoder.

After successful cutover, reruns skip marked instances even if a player later cleared optional fields. Brand-new NPCs are marked by their normal initializer. A routine restart, registry reload, profile source edit, or repeated spawn/materialization of the same existing entity never overwrites a marked instance's effective card. A future bulk-reset product feature is outside this scope.

## 7. Dialogue consistency and asynchronous settlement

### 7.1 Prompt and scripted consumers

LLM dialogue reads the current effective NPC card, including that NPC's own hidden identity and explicit speech style. Continue using the existing public-only view of the player's persona; the author editor does not expand what NPCs know about the player. Persona prose is role material, not authority to change rules or issue unvalidated intents.

Prompts distinguish the current persona from historical conversation. Preserve earlier transcripts and confirmed events; use the latest card for subsequent behavior without asserting that past events were rewritten.

Scripted dialogue reads authored tables and profile-specific fallback lines deterministically. In particular, known NPCs must not all use the old shared misunderstanding/greeting line when their normal dialogue has an authored individual voice. Missing/corrupt source references are integrity failures, not an excuse for a fake personalized fallback. Opening or editing a card requires no LLM or image service.

### 7.2 Persona-version completion gate

Capture the NPC identity and `persona_version` used to build each asynchronous NPC exchange. At settlement, compare against the current entity/version before any response-side effects. Compare version inequality, not current-versus-captured prose equality, so changing a card and then changing it back still invalidates the old exchange. A changed persona produces a distinct stale-persona terminal outcome, not the existing degraded/offline outcome.

A stale-persona exchange must not emit its speech, append its NPC response to memory, apply any intent, replace the visible dialogue line, or execute an offline party-invite threshold fallback. It must settle the transport with a safe localized explanation and clear pending/thinking state. Do not retry the exchange automatically.

Apply this gate to every consumer of the exchange seam: free-form talk through browser and text commands, invitation conversations, and any other callsites discovered by references. Gate the shared result/memory path and the final deterministic intent application; guarding just the browser button leaves text and invitation paths inconsistent. Existing movement, possession, schedule, and capability checks remain in force.

Already committed speech and game effects are not undone. A player's input already recorded before the edit may remain in history, but no stale NPC response is added. An unchanged/no-op save does not invalidate an exchange.

## 8. Author editor access and transport

### 8.1 Access policy

Expose a server-authored edit affordance for NPC targets on the existing interaction surface. The selected target must be an actual `NPC` family instance, visible and co-located with the session's current, activated, account-owned player character. Author editing does not require a conversation session, friendly disposition, affinity threshold, service component, or awake/willing-to-talk schedule.

Use normal session/puppet ownership admission and restrict the editor to exploration/dialogue modes; combat, creation, and possession must not accidentally inherit an edit privilege from client-supplied ids. A different account's player character, an arbitrary object, a remote NPC, and a `Monster` are never valid targets. Resolve all gates again on save; the opened window is not a permanent authorization token.

This is an ordinary single-player author tool, not a builder/superuser feature or an in-fiction command. Existing NPC title immutability and player-persona ownership remain unchanged.

### 8.2 Request/response design

Use two allowlisted OOB actions through the existing dispatcher, with exact payload validation:

- `npc.persona.read`: `npc_id`, using the positive safe-integer NPC identity already used by `explore.talk_open` and the selected target. Return a private editor snapshot only on success.
- `npc.persona.update`: `npc_id`, `expected_persona_version`, and the complete `persona` card. This is one atomic submission, not seven independently committed field updates. Both integer fields reject booleans and values outside the protocol safe-integer range.

The read/update success `data` shape contains `npc_id`, `display_name`, `npc_title`, `persona_version`, and `persona`. Use `persona_version`, not the reserved result key `revision`. Do not add actor/session identity or diagnostic keys. Re-resolve `npc_id` from the actor's currently visible room contents; it is an identity, not an authorization token.

All nested persona keys are fixed lowercase identifiers. The result has five top-level data fields against the existing maximum of eight; each card text leaf is at most 600 code points against the protocol's 2,048-code-point string cap. The existing result-data byte ceiling is 63,183 bytes, within the 65,536-byte envelope. The complete card has at most 2,000 code points including rendering labels; its raw text therefore needs at most 12,000 JSON bytes even under six-byte character escaping. Bounded keys, safe integers, and the existing name/title bounds remain below the remaining budget. Verify maximal valid cards containing CJK, astral characters, and JSON escapes through both actual protocol validators. A card with every leaf at 600 simultaneously is invalid under the aggregate limit and is not a required successful payload. Mirror exact domain validation in the browser without weakening global OOB limits.

Normal action outcomes carry stable codes for missing/invalid target, invalid mode/ownership, unavailable persona, field/budget validation, and version conflict. Error results contain no card data; field failures can use stable field-specific codes and localized messages rather than adding an error `data` slot the protocol forbids. A version conflict preserves the local draft and offers an explicit reload through a fresh read action; no silent overwrite or automatic merge.

Only the requesting session receives the full editor result. Ordinary exploration/dialogue snapshots carry the edit affordance, not the full card or hidden identity. Full cards are not echoed into the narrative log, analytics, action messages, or local persistent browser storage. Apply the existing result-cache/epoch retirement rules and clear editor data on close, logout, puppet change, or session replacement.

The adapter performs admission, delegates writes to the deterministic core, and publishes the required safe view refresh only after commit. It never assigns `.db` itself and never invokes a player-character edit API against an arbitrary NPC.

## 9. Editor interaction behavior

The flow is **interaction target → 編輯人物設定 → editor window → save or cancel → original interaction context**. Reuse the project drawer/overlay frame, typography, spacing, and focus primitives. Do not add a new UI framework or a full-screen NPC catalogue.

The heading displays the bound NPC's name/title. Show an author-mode/spoiler notice and a persistent notice that fixed dialogue and existing portraits are not regenerated. Present the seven sections as labeled text controls, with public/hidden identity separated inside the identity section. Make required/optional status, per-field bounds, and total capacity visible. Use a single scrollable column on narrow screens with reachable save/cancel controls; wider layouts may use the existing drawer width without adding a new layout system.

The editor binds to the target and session epoch captured at open, never to a subsequently selected NPC. Its state transitions are loading, ready/clean, ready/dirty, saving, and rejected/unavailable. Correlate every result to the request and bound target. Late reads/saves for a closed editor or another target cannot seed or close the current editor.

- Only a confirmed server save updates the committed baseline and reports success. A failed save leaves the draft intact.
- Disable duplicate submission while saving. Losing the transport must not claim either success or failure without a terminal result; re-read after reconnection before another commit.
- Cancel closes a clean editor. Closing a dirty editor, including Escape or backdrop dismissal, requires confirmation to discard. Do not replace a draft merely because a background panel refreshed.
- If the NPC leaves, is deleted, or access/mode changes, keep the open draft with a clear unavailable state and disallow save. Revalidation remains authoritative. Logout or a puppet/session identity change instead clears the private editor state.
- If another tab saves first, reject the stale version and preserve the draft until the user explicitly chooses reload/discard. Reuse the current read action for reload; do not invent an automatic merge.
- Use labeled controls, a modal dialog name, keyboard focus containment, visible focus, keyboard-accessible buttons, and announced errors/save results. Close returns focus to the opener if it still exists, otherwise to the interaction surface. Text entry must not trigger movement/dock shortcuts. No new gamepad support is required beyond the client's existing navigation facilities.

Editing changes only the selected NPC's persona/version. It spends no currency or game time, grants no quest knowledge, changes no friendship/party membership, and does not trigger image generation. Future explicit portrait generation may use the new appearance through the existing art persona reader.

## 10. Failure handling and observability

Validate registry data and source coverage before activation. Reject malformed authored rows with their profile/source key. Do not start with a mixture of silently accepted old and new content because one slice was missing.

Initialization, cutover, and editor persistence use the deterministic core's transaction conventions and emit commit-bound operational events through `world.observability`. Include available NPC, acting character, source/profile, old/new persona version, and workflow identifiers in context. Never log persona text, hidden identities, or player-facing dialogue. Add the new event definitions to the observability catalog when implementing them, and run focused tests with the observability lint whenever logging changes.

Expected validation, stale context, and conflict rejections have stable localized results. Unexpected failures receive the existing correlation-id treatment. An exception must be re-raised, logged with `exc=`, or carry the repository's reasoned lint exemption; there are no silent failures.

## 11. Verification and completion criteria

### 11.1 Behavior contracts

Use deterministic synthetic fixtures for mechanics; reserve shipped-content checks for properly registered data-contract tests. Test consumer-visible behavior rather than pinned prose, field-copy wiring, or exact implementation text.

Required cases include:

1. Valid compact cards include every required field in the NPC prompt without truncation; unknown keys, missing required text, astral Unicode bounds, identity-section bounds, and combined-budget overflow reject without persistence.
2. Every production creation route produces a complete card, and invalid imports or generated requirements leave no partial NPC/batch. A generated card survives durable compile, restore, and materialization.
3. Offline repeated-role NPC creation can select different coherent voice bundles for distinct stable identities, while an existing instance never rerolls on read/reload. Tests use fixed seeds and assert specific meaningful traits/voice behavior rather than non-empty output.
4. The one-time cutover replaces all provisional personas, preserves object ids and gameplay state, rolls back on failure, and is idempotent. Include existing and not-yet-materialized generated-quest occupants across restore. Editor/import/spawn writes are not admitted during the exclusive cutover. Subsequent player edits and deliberately empty optional fields survive restart.
5. An editor save affects only the selected NPC, with no clock/currency/trait/quest effects; required target/ownership/mode gates are enforced on both read and update. Forged/unknown ids, another account's player character, a Monster, a remote NPC, and an NPC that moved or was deleted after the read all reject without writing or exposing card data in errors. A retired session epoch cannot authorize a save.
6. Two sessions cannot overwrite each other's edits using stale versions. Invalid fields, vanished targets, and storage failures preserve committed state. Retried identical request ids retain existing deduplication semantics.
7. Only the author read/update result exposes hidden identity; ordinary snapshots and logs do not gain the full card. Player persona visibility and editing behavior remain unchanged.
8. An edit made during delayed talk or invitation completion prevents old speech, response memory, intent application, and fallback acceptance. A change to only one leaf is sufficient, as is changing then restoring the original prose. No-op saves leave otherwise valid responses usable. Cover browser and text consumers.
9. Scripted greetings, keyword replies, and ordinary NPC fallback lines work with every LLM disabled. Changing the runtime card does not rewrite their authored text or invalidate legitimate service semantics.
10. Browser coverage exercises a real selected NPC, opens the editor, saves, reopens, and observes persistence. Cover keyboard operation, dirty-close confirmation, error retention, stale-result correlation, target departure, session changes, and cross-tab conflicts.

### 11.2 Content review

The source-to-profile/dialogue inventory must cover the complete production roster and all NPC dialogue tables. Review all rewritten cards and lines against world/service facts and the intended voice. Do not retain provisional wording merely to keep old exact-string assertions passing; remove incidental wording tests and retain behavior assertions.

Automated checks can establish coverage and deterministic rendering, not prove that a personality feels distinctive. Record editorial review across the full roster, with representative side-by-side same-profession dialogue and representative free-form prompt/reply review when an approved model is available. No automated gate may require a live model; report any absence of actual model-output review honestly.

### 11.3 Execution gates

Each implementation change runs the smallest affected Python/Evennia, Node, and Vue tests, plus an exercised smoke path. The UI change runs a focused actual-browser scenario, not only component tests. Register every added/moved non-browser Evennia test module in exactly one shard and every new required component in the existing showcase coverage contract.

Before handoff, run the repository contract gate and strict OpenSpec validation. Use the applicable frontend build, component, and showcase gates for the UI changes. The full managed browser suite, complete traceability evidence run, and aggregate coverage gate remain CI-owned. Do not claim a successful live LLM or browser exercise when only deterministic substitutes were run.

## 12. Delivery boundaries for OpenSpec

This is one approved product design, but it spans several workday-sized implementation changes. `os-propose` must split it into dependency-ordered changes, not one unbounded task list. The complete set is required for delivery; foundational seams or a partial NPC roster are not completion.

Use these ownership boundaries when decomposing:

- Compact NPC card contract, pure validation/render-budget policy, deterministic persistence/versioning, and profile registry vocabulary.
- Full authored content rewrite, divided into coherent settlement/character-source slices so each includes its own cards and corresponding dialogue. Profile assembly has one integration owner.
- Creation producers and generated-quest durable schema integration, including NPC imports and NPC-specific companion sources.
- Shared dialogue consumption, authored fallback routing, and the persona-version completion gate across all consumers.
- Server-authorized editor read/update actions and their exact browser protocol/domain validation.
- Interaction entry and editor window with focused browser evidence and user documentation.
- Full-roster validation and activation/cutover, dependent on all replacement content and producers being ready.

The proposal dependency/conflict matrix must identify shared schema, registry assembly, prompt, dispatcher, and UI router files. Decompose large producer or content slices further where one workday is implausible. A cutover or user-facing editor must not be activated against incomplete profile data. Dependent changes must state how their requirements become satisfiable without manufacturing placeholder profiles or weakening CI/main-spec coverage.

No implementation, archive, feature branch, or worktree is created as part of the current document/proposal request. Design and proposal artifacts are committed on the primary branch according to the proposal workflow.

## 13. Explicit architectural amendments and non-goals

This design preserves the generative/deterministic single-writer boundary and the existing read-only `PersonaStore`. It explicitly amends the old architecture document's statement that persona contents are never inspected **only for NPC compact-card structure, text bounds, and completeness**. NPC import validation becomes typeclass-aware; player/non-NPC opaque persona handling remains unchanged. No engine interprets personality prose as a mechanical rule.

The old architectural note that `PersonaStore` is an unimplemented seam is historical; the current reader and injection specs/code listed in section 2 are already implemented. Implementation changes must reconcile affected current capability specs for import validation, NPC characterization, persona injection, scripted dialogue, and UI contracts. Do not rewrite the existing player-persona editing contract to grant arbitrary NPC access.

The one-time full replacement of provisional NPC content is explicitly authorized. It is distinct from future runtime editing and does not create a backward-compatibility layer, general migration framework, or automatic reset-on-upgrade policy.

Out of scope: runtime LLM rewriting of fixed dialogue, fixed-dialogue editing in the browser, bulk/global NPC management, name/title or mechanical-stat editing, rewriting player presets, automatic portrait regeneration, affinity-gated author access, new conversation capabilities for previously non-speaking NPCs, new monsters-as-NPC semantics, new multiplayer/world-ownership architecture, and automatic alteration of quest facts or historical transcripts.
