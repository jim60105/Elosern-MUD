## Context

See proposal.md for motivation. The approved parent and S3 designs are authoritative; the engine design's §3.1 single-writer amendment and AGENTS.md invariants remain intact. S1 and both S2 changes are archived on master. Existing access/envelope/pagination/fetch, separate Vite build, component layer, facade request events and GmCallDrawer are prerequisites, not work to rebuild. `fast_recall` accepts string owner/requester ids, thread/inclusion options, and returns core/working/recalled selections plus generation; it already enforces thread permission and emits facade events.

## Goals / Non-Goals

**Goals:** Deliver exactly the S3 entity matrix and diagnostic workflows as one bounded change, using existing queries and one reusable list/detail shell. Keep corrupt sections visible and prove both direct and indirect reads are immutable.

**Non-Goals:** No database migration, compatibility alias, new rule computation, authored registry browser, edit operation, polling, external inference, or extraction of a pure dialogue-prompt builder. Do not weaken narrative permissions to implement operator recall.

## Decisions

### 1. Thin entity readers, not a second game engine

Create `web/gm/readers/{accounts,characters,npcs,monsters,rooms,quests,narrative,art,raw,search}.py`. Readers return JSON-serializable dictionaries and own transport projection only. Use `account_roster`; `status_query/`, `displayed_stats`, `title_view`, `lineage_query`, affinity/party/possession queries; NPC persona/schedule/dialogue reads; monster individual/behaviour/site queries; map reads; quest log/runtime/GeneratedQuestStore; narrative query helpers/models; ArtAssetRecord/gallery. The approved S3 §4 table is the complete field inventory, repeated in the delta spec. No derived balance constants or mutable initialization calls belong in readers. Monster numeric provenance must remain explicit; wallet conversion uses integer arithmetic only.

Each summary is a dictionary of independent named sections, with failure represented in that section as `{"error":{"code":"…","message":"…"}}`. Resolve existence/kind before projection; a local section failure does not turn the whole entity into a 404 or empty success. Catch failures at section boundaries with facade exception logging (named imports, identifiers in context), not silent suppression or freeze-list additions.

### 2. Non-creating access inventory and indirect helper audit

Default-autocreating descriptors visible in the current typeclasses that inspection may touch are:

| Owner | Properties requiring non-creating reads |
| --- | --- |
| LivingEntity | race, subrace, sex |
| PlayerCharacter | age, apparent_age, creation_pending, guild_rank, quest_log, wallet |
| NPC | dialogue_memory, schedule |
| LLMNPC | max_chat_memory_size, thinking_timeout, thinking_messages (if surfaced) |
| Monster | loot_table, behaviour_tree |
| SceneArchetypeMixin / AnchorRoom | scene_archetype, anchor_key |
| InstanceRoom | expire_tick, named, interacted, pin_reasons, owned_entities, origin_room |

Read these through `attributes.get(key, default=...)` with the descriptor's category/default semantics, never by accessing the descriptor. Non-autocreating descriptors currently include combat_traits, creation_draft, npc_title, species_key, variant_key and threat_tier; do not bypass monster resolution semantics when projecting derived identity. During implementation extend the inventory for inherited Evennia properties and every helper/handler accessed. Lazy TraitHandler/BuffHandler/component construction can also persist backing data: inspect the call chain, avoid creating handlers when backing state is absent, and expose honest defaults/errors. If an authoritative helper cannot be read safely, add a narrowly scoped pure read seam in its owning package, preserving calculation reuse; never implement copied calculations in web/gm or invoke initialization and roll it back.

### 3. Generic raw projection

Read all Attributes with key/category, categorized tags and existing components, typeclass, location and db_date_created without provisioning components. Recursively JSON-convert values; Evennia references become $ref/typeclass/key and unsupported or cyclic values become $unserializable/type-name/bounded repr (200 characters). A failed conversion is local to its value. Raw lookup accepts any Evennia object, not only curated types; non-curated references land on raw inspection. Account raw data reads Account Attributes/metadata in its detail representation rather than assuming an ObjectDB dbref; narrative/quest/art record raw tabs project stored fields in detail data. No synthetic Evennia metadata is invented for those records.

### 4. APIs and identifier routing

Register the approved five route families through gm_path; register `search`, `object/.../raw` and NPC recall before generic kind/id routes so reserved paths cannot be swallowed. Use an explicit supported-kind mapping that distinguishes player characters, NPCs and monsters; ids are Evennia dbrefs for object-backed kinds and the owning model's stable identifier for record-backed kinds. Preserve owner identity for quest records where quest ids are owner-scoped; links carry enough identity to resolve the exact record. Narrative subtype filters distinguish events, threads, letters/state/reply work, dreams/exchanges, decisions, beats, drafts and requests.

Use existing cursor helpers/envelope, default 50/max 200, stable indexed order with unique tie-breaker, and indexed filters (typeclass/tags for objects, owner/category/tick for narrative). List responses contain summaries only, never full raw inventories/revision collections. NPC memory/revision/dialogue collections use the list/detail route families with owner/subtype filters; newest snapshots are capped at ten. Test actual query fields/indexes rather than building in-memory full-world sorts. Search exact #dbref first (raw target if no curated kind), then object key/quest id/source_id precedence. call_id identifiers open the landed S2 drawer; no new transcript-search endpoint or trace-to-call guessing is introduced. Snapshot trace links preserve the existing S2 linkage when available; unresolved evidence stays visible without a fabricated transcript.

### 5. Recall is POST transport, not a writer

Validate body/query length before execution, keep Django CSRF protection, resolve an actual NPC, and call `fast_recall(owner_id=<canonical NPC id>, requester_id=<same>, query=..., thread_id=..., include_superseded=..., include_inactive=...)`. Preserve its default selection/ranking limits and permission gates. Serialize selections, lexical/final scoring fields and generation without reranking. Test equality against a direct call with identical inputs, excluding nondeterministic timing observations. Never call `build_dialogue_context`: it settles correspondence, creates epochs, stores snapshots and appends frames. Existing snapshots and transcript payloads provide actual past prompts.

### 6. Frontend composition and clean cutover

Enable only the runtime section and its complete navigation tree; leave undelivered S4/S5/S6 sections disabled. Build one entity page shell with header/name/identifiers, overview/raw tabs and NPC memory/dialogue tabs. GmEntityLink resolves object/record/source identifiers and opens GmCallDrawer for calls. GmJsonTree is the sole JSON-tree renderer for raw tabs and structured S2 payloads; replace duplicated structured JSON rendering without aliases while retaining textual prompt/code presentation, attempts, role grouping, validation errors, copy JSON and unavailable-transcript states. GmFilterBar/GmPager use cursor/filter state; filter changes restart pagination. Reuse the existing fetch boundary for every request and manual refresh; do not inherit overview polling timers. Display true/disguised panels side by side with the approved display-only label.

### 7. Acceptance and traceability

One fixed-fixture EvenniaTest module per reader (including raw/search), API access/CSRF/route/error tests, and isolated-section failures cover the delta spec. The AST contract rejects writer methods, db/Attribute-property assignments and known-writer imports, including dialogue context assembly. Runtime tests exercise every entity kind, all relevant raw/list/detail/tab/recall paths, and missing stored defaults; compare Attribute counts and every narrative table's row counts before/after without transaction rollback masking writes. Direct recall parity and disguise separation are separate behavioral assertions. Vitest covers linking, JSON markers, filters/paging, manual-only refresh and section errors; Storybook covers each new component and retains drawer coverage. Register all new Python modules in the existing shard manifest. During implementation/sync obtain canonical requirement IDs through `tools.spec_traceability list`, use literal covers_requirement annotations on substantive tests and existing frontend evidence bridges; never guess IDs or add placeholder coverage. Update operational/developer documentation with read routes, immutability limits and manual refresh.

## Risks / Trade-offs

- Read helpers may initialize lazily: descriptor inventory plus static/runtime checks catch different classes of writes; extend pure owning-package reads only when needed.
- Large raw values or graph cycles cannot be allowed to break all inspection: local conversion markers preserve diagnostic evidence without traversing references.
- Web-process session/schedule information may be incomplete: report actual source availability, not invented live values.
- Trace ids may not identify retained calls: only existing resolvable S2 evidence links are actionable, and expired/disabled transcripts retain S2 empty states.
- Shared router/URLs/drawer/stories/shard files can conflict with later S4/S5/S6 work. No active changes existed at proposal creation; prerequisites are already landed.

## Migration and rollout

This pre-release feature adds reads only; no migrations, compatibility paths or state conversion. Apply on the later S3 feature branch, implement/check the full task list, then use the normal verification/archive workflow. This proposal itself changes artifacts only on master.
