# Design

## Context

Observed shape.py has only KeywordResponse(keyword,response) and DialogueDefinition(greeting,responses), both frozen. Lore registry must never import rules. This change supplies a complete pure data API and validators without switching live tables; runtime cutover is the next change.

## Goals / Non-Goals

**Goals:** Immutable reusable scenes and complete typed topic declarations. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

## Shared contract v1 (proposed APIs, authoritative for this batch)

These are proposed interfaces, not claims about current implementation. Later designs reference this section and implement only their named fields. Python lore stays registry-only; world/rules owns dialogue/session/effects and world/narrative owns reading records. No executable scripts, per-line server cursor, new quest effects, compatibility adapter or data migration.

### Immutable declarations

Add `world/lore/scenes.py` with frozen `Speech(speaker: Literal["actor","host"], text: str)`, `Narration(text: str)`, `Scene(scene_id: str, revision: str, lines: tuple[Speech | Narration, ...])`. IDs match `[a-z][a-z0-9_.-]{0,95}`; revisions are explicit nonempty ASCII tokens <=32. Lines are 1..2000 code points and scenes 1..32 lines / <=16000 total code points. Dialogue formal scenes and variants begin with an actor Speech containing a complete utterance; narration and consecutive same-speaker lines are legal thereafter. Opening/guild dynamic service scenes need not begin with actor. No interpolation, executable callbacks, embedded HTML, or choices inside a scene. Text is plain data; existing trusted text-output escaping rules still apply to editable greetings.

In `world/lore/dialogue/shape.py`, add frozen `SceneVariant(variant_id, priority: int, when: Condition, scene: Scene)` and `AuthoredTopic(topic_id, keyword, label, fallback: Scene, variants=(), requires=None, unavailable="hidden", refusal=None, predecessors=(), disclosure="qualified")`; `AuthoredDialogue(greeting: str | None, topics: tuple[AuthoredTopic,...])`. Topic identity is `<dialogue_key>.<ASCII suffix>`, <=96 chars, independent of localized keyword/label, tone and revision. Predecessors are stable topic IDs within the same host definition; reject dangling references/cycles. `disclosure` is `qualified` or `pure_chain`. Pure chains have predecessors, no requires, no effects, and contain only public informational scenes; reject a qualified descendant included in a pure-chain bundle. Qualified descendants remain separate server selections. Select the highest matching integer priority; priorities are unique within a topic; otherwise use the unconditional fallback. Variants alter complete linear wording, not effects or reading identity. Refusal required for visible lock, forbidden for hidden disclosure. Formal topic count <=16 with ALL entries reachable by scrolling the choices surface; retire the old first-four truncation on every authored surface.

`Condition` is the tagged frozen union owned by `world/lore/dialogue/conditions.py`: `All(children)`, `Any(children)`, `RaceIs(race_key)`, `SocialIdentityIs(identity_key)`, `GuildRankAtLeast(rank_key)`, `QuestIs(definition_key, state)`, `AffinityAtLeast(stage_key)`, `Carries(item_key, minimum=1)`, `CompanionPresent(source_kind, source_key)`, `TimePeriod(start_daypart, end_daypart)`, `SkillOwned(skill_key, min_proficiency=None)`, `Exposure(minimum=None, maximum=None)`. Groups have 1..16 children and maximum depth 4; at least one Exposure bound, canonical ordered inclusive comparison. Runtime evaluators arrive in physical/progression slices, with no placeholder evaluator. All declaration keys are validated against the canonical registry in the owning condition slice before shipped conditions use them.

### Context and selection

Add `world/rules/dialogue_context.py::resolve_dialogue_context(actor, host, *, session=None) -> DialogueContext(actor, owner, host, context_id, phase_revision)`. Ordinary player owner=actor. Possession resolves owner through `world.rules.party_scope.resolve_commander(actor)` and validates `is_companion(actor, owner)`, authenticated driving session when supplied, mirrored possession, actor/host co-location, capability, host schedule and host!=actor. Do not trust a client owner/actor id. Guild/quests/reading and host.relations affinity use owner; race/social/skills/inventory/exposure use actor. Companion membership uses owner and presence uses actor.location. Session remains on the ACTING body's existing db.dialogue_session seam. Switching control invalidates that body's conversation instead of resuming it on another body; durable reading is owner-shared.

`world/rules/dialogue.py::select_authored_topic(actor, host, topic_id, *, selection_id, expected_context_id, session=None) -> SceneDelivery` is the sole authored formal/refusal selection path used by command and web adapter. Context is resolved and eligibility rechecked before effects. The existing web action remains `explore.talk_scripted`, with exact payload `{npc_id, topic_id, context_id, selection_id}` for authored topics; generated current-phase topics retain their existing keyword payload and quest-authority seam, selected by server source type (a closed validator union, never two competing authored APIs). Text keyword lookup resolves a stable topic then invokes this same selection function. `selection_id` is <=64 chars, web dispatch request identity reused on transport retry, newly allocated per genuine text command. Repeating a selection id within the current context returns the committed delivery, with no second effect. Reject reuse for another topic. A new deliberate selection may grant existing talk affinity under existing caps; replay and completion never do. Unknown keywords, hidden topics and refusal never grant affinity. Guild 回報 listing is still read-only and the quest-id turn-in stays in the guild service, not an authored reward action.

### Delivery, replay and wire

Frozen `SceneDelivery(delivery_id, selection_id, context_id, actor_id, owner_id, host_id, topic_id, scene_id, scene_revision, phase_revision, kind, lines, updated_tick)` with kind `formal|refusal|opening|service`; all ids JSON-safe scalars, delivery/context ids opaque <=64 chars. Owner identity is server-only and omitted from the wire. `topic_id` is nullable only for opening/service. Context id changes on new host/control/open/phase invalidation, not on an availability refresh. Scene revision identifies exact authored bytes; a session stores the delivered scene snapshot, never a current line cursor. A replay republishes that delivery_id and bytes beginning at line one without selecting again. Reject obsolete context, invalid host, changed phase, or changed actor/control; do not expose stale lines. Variant stays fixed after equipment/condition refresh while context remains valid. Revocation of eligibility alone refreshes choices; previously authorized playback stays fixed. Existing movement/combat/host departure/deletion clear seams retire delivery and choices together while historical attributed transcript remains.

`open_or_refresh_dialogue` remains the sole session writer, extended with keyword-only `delivery=None`; existing generated/freeform `line` calls remain valid native paths. It stores exact discriminated `{kind:"line", npc_id,line,updated_tick}` or `{kind:"scene", npc_id,delivery,updated_tick}` session records. No parsing old authored response records or permanent KeywordResponse alias. Selection effects, compensation snapshots and session-delivery publication share the owning transaction; operational failure restores cached Attributes as well as durable state. The idempotency receipt lives in the current session with delivery; existing action-envelope generation/epoch/revision admission rejects older selections after an intervening selection, even if its per-topic last receipt was replaced; replay/ack calls have no effect invocation. Existing generated story effect APIs retain their authority and rejection contract and never gain authorization from authored reading.

Bump the dialogue panel from schema_version 2 to 3 across Python and UMD/Vue validators in one runtime change. Exact available top-level fields are `{schema_version,available,kind,host,actor,bond_stage,context_id,delivery,choices,pure_chain,reading_revision,unlock_batch}`. `host` and `actor` each use existing `{identity,display_name,portrait_ref}` contract with `portrait_catalog_key`; numeric affinity never ships. `delivery` is null or `{delivery_id,context_id,topic_id,scene_id,scene_revision,phase_revision,kind,lines}`; line wire forms are `{kind:"speech",speaker:"actor"|"host",text}` or `{kind:"narration",text}`. Existing generated/freeform line presentations become a native one-host-line delivery, without changing model generation or settlement. `choices` are <=16 exact `{topic_id,keyword_id,label,availability,requirement_hint,unread,predecessors,action_payload}` rows. Hidden rows absent, locked rows have no formal scene, open qualified rows have no pre-delivered body until selection. `action_payload` is server-authored exact action payload without selection_id (dispatcher adds request identity); native generated rows use their existing keyword source. `pure_chain` holds only public authorized successor scene descriptors, never effects/qualified bodies. Defaults before owning slices are `pure_chain:[]`, `reading_revision:0`, `unlock_batch:null`, choice unread:false and open/no hint. These defaults describe unsupported optional features, not fake runtime implementations. Client schema_version 2 support is removed. All canonical portraits come from the same committed art snapshot; no client dbid-to-catalog mapping.

### Reading and completion

`world/narrative/dialogue_reading.py` is the sole writer of owner.db.authored_dialogue_reading, schema_version 1 with host dbid string -> stable topic id -> `{completed:bool, ever_open:bool, announced:bool}` and a monotonic root revision. It uses existing persistent Evennia Attributes, not a new ORM table/migration. Use first-SQL guarded UPDATE on the owning ObjectDB row, then raw Attribute reads (SQLite-safe npc_persona precedent), merge under that lock and restore Attribute caches on rollback. `reading_for(owner, host_id)` is pure and never creates storage. `complete_delivery(actor, *, delivery_id, context_id, topic_id, scene_revision, session=None)` resolves owner/context and matches a server-issued delivery receipt. Returns `{status:"saved"|"already_saved", reading_revision}`; rejects stale/foreign/undelivered/refusal with stable reason and zero effect/reading change. Refusal completion is a UI return-to-choices event only, never formal read/predecessor progress. Changing variant/revision alone never resets completion. Completion is an acknowledgement of delivery, with no timing/line proof. Pure-chain receipts are issued for each public pre-delivered successor and retained on the current context; acknowledgements require saved formal predecessors. `explore.dialogue_complete` exact payload is `{delivery_id,context_id,topic_id,scene_revision}`. Successful attributed text emission invokes the same completion service; failed/partial emission never completes.

Completion receipts persist independently of latest playback, including earlier topics. Keep at most two formal receipts per topic (latest and previous), <=32 receipts for <=16 topics; a third reselection retires the oldest unacknowledged same-topic receipt. Replacing the latest scene does not invalidate another topic completion. New context/phase/control clears these receipts. Delivery-bound duplicates remain idempotent across connections and reconnect. Returning to choices locally may reveal only pure-chain successors, with pending acknowledgements queued predecessor-first. Protected qualified successors wait for server-saved reading and eligibility refresh. Post-commit fan-out uses existing watcher/panel-pusher discipline, resolves connections for the OWNER including a currently possessed actor, and refreshes each connection's own live context without copying another body's scene.

### Availability and notifications

`world/rules/dialogue_conditions.py::evaluate_condition(condition, context)` and `condition_hint(condition)` share declarations and canonical labels. Missing/corrupt authoritative state fails closed with a facade integrity event, no handler materialization. Hints disclose public stage names rather than private affinity numerals. `world/rules/dialogue_availability.py::project_topics(context)` is pure; `refresh_dialogue_availability(owner, *, cause)` runs only from committed deterministic seams. Qualified predecessor completion and requires govern open/hidden/locked. Pure-chain predecessors govern UI reveal and persisted progress only, never effect authorization. The server checks explicit topic IDs even if a forger bypasses UI ordering.

Before notification support, no unlock mutations occur during projection. The notification slice adds narrative-owned `observe_availability(owner, host_id, open_topic_ids, *, initial, context_id)` and `claim_unlock_batch(owner, batch_id)`. At FIRST observation of a host, set ever_open for presently open topics, show their unread markers, and set announced true without popup. A topic observed locked/hidden first, then open later, gets ever_open true and one announcement eligibility while unread. A first observation after a prior persisted locked snapshot counts as later unlock. Read formal topics remain complete through relock/reopen; unread existing topics keep their marker, and ever_open/announced prevent repeat notifications. Tone-only changes do neither. A batch is a bounded owner/host set of newly-ever-open unread topic ids per one committed refresh, stable batch_id <=64; persisted pending batch is claimed once under owner lock before fan-out to current authenticated watchers, so reconnect never replays a popup. Delivery is at-most-once, not guaranteed across disconnect/fan-out failure; markers remain durable. Wire `unlock_batch` is ephemeral only on that live post-commit update, never snapshots/reconnect. Client deduplicates by batch_id in memory, defers until scene returns to choices, never steals focus, drops batches for retired contexts/characters and leaves durable markers intact.

Frontend pending completion exists only in memory scoped by owner character/control context, no localStorage/IndexedDB/service-worker queue. Retry on same-context transport restoration and explicit retry, serialize pure-chain predecessor acknowledgements, and do not claim saved state before a saved/already_saved response. On refresh/tab close/character exit/context invalidation discard pending state. Reconnect without pending memory replays latest delivered scene at line one; saved server reading wins. Persist no line/page cursor.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.

## Batch coverage and scheduling map

The approved source is docs/superpowers/specs/2026-10-25-authored-dialogue-engine-design.md; the assignment authorizes planning past its written-review gate. The single-writer/offline source is docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md sections 3.1 and D4/D13. Planning never read tmp/story_settings/world_info.md.

| Change | Direct prerequisites | Owned scope |
|---|---|---|
| authored-dialogue-contracts | none | Immutable reusable scenes and complete typed topic declarations |
| authored-dialogue-runtime | authored-dialogue-contracts | Cut over all authored backend/text delivery and version-3 protocol |
| authored-dialogue-playback | authored-dialogue-runtime | Shared manual Vue scene player and synchronized stage attribution |
| authored-dialogue-possession | authored-dialogue-runtime, authored-dialogue-playback | Lawful possessed authored conversations with owner-correct relationships |
| authored-dialogue-social-identity | authored-dialogue-contracts | Typed social identity source without parsing persona prose |
| authored-dialogue-physical-conditions | authored-dialogue-runtime, authored-dialogue-possession, authored-dialogue-social-identity | Actor identity, inventory, present companion, time, skills and exposure conditions |
| authored-dialogue-progression-conditions | authored-dialogue-physical-conditions | Owner guild, quest lifecycle and host relationship qualification |
| authored-dialogue-availability | authored-dialogue-progression-conditions | Server-qualified topic disclosure and committed-state refresh |
| authored-dialogue-locked-ui | authored-dialogue-availability, authored-dialogue-playback | Visible locked topic refusal and accessible canonical hints |
| authored-dialogue-reading-server | authored-dialogue-availability | Narrative-owned formal reading, delivered receipts and pure-chain synchronization |
| authored-dialogue-reading-client | authored-dialogue-reading-server, authored-dialogue-locked-ui | Memory-only completion retry and pure-chain progression |
| authored-dialogue-unread-notices | authored-dialogue-reading-client | Persistent unread markers and deferred deduplicated unlock batches |
| authored-dialogue-content-guild | authored-dialogue-unread-notices | Complete authored rewrite for guild_staff |
| authored-dialogue-content-lower-hospitality | authored-dialogue-unread-notices | Complete authored rewrite for altoria_eatery, altoria_tavern, altoria_lodging |
| authored-dialogue-content-lower-civic | authored-dialogue-unread-notices | Complete authored rewrite for altoria_bathhouse, altoria_guardhouse |
| authored-dialogue-content-middle-tools | authored-dialogue-unread-notices | Complete authored rewrite for altoria_general_store, altoria_forge, altoria_tailor |
| authored-dialogue-content-middle-exchange | authored-dialogue-unread-notices | Complete authored rewrite for altoria_jeweller, altoria_alchemist, altoria_merchant_hall |
| authored-dialogue-content-upper-faith | authored-dialogue-unread-notices | Complete authored rewrite for altoria_temple, altoria_sanctum |
| authored-dialogue-content-upper-civic | authored-dialogue-unread-notices | Complete authored rewrite for altoria_noble_watch, altoria_drill_yard, altoria_academy |
| authored-dialogue-content-ciaran-crafts | authored-dialogue-unread-notices | Complete authored rewrite for ciaran_hailiel_home, ciaran_vethiel_home, ciaran_gwenaera_home |
| authored-dialogue-content-ciaran-fare | authored-dialogue-unread-notices | Complete authored rewrite for ciaran_lareneth_home, ciaran_nireth_home, ciaran_valwyn_home |
| authored-dialogue-content-ciaran-commons | authored-dialogue-unread-notices | Complete authored rewrite for ciaran_elenis_home, ciaran_teliel_home |

Every content change depends on the completed notification pipeline so it is immediately playable with formal read and unlock semantics. Distinct domain files can be authored independently. Same-file groups require serial application or agreed disjoint host hunks: lower-hospitality/lower-civic, middle-tools/middle-exchange, upper-faith/upper-civic, and all three ciaran changes. No runtime source is owned by a content change. New test/review files are slice-exclusive. Shared append-only shard/freeze manifests need a single integration owner or serial final merge; main capability synchronization/archive is always supervisor-serialized. No branch/worktree/apply/archive is created by this planning batch.

| Approved requirement | Owning change(s) and acceptance |
|---|---|
| Frozen reusable speech/narration, stable topic/predecessor IDs, explicit priorities/fallback | contracts; synthetic declaration and DAG tests |
| Offline source-aware selection, generated/freeform native seam, complete text, exactly-once effect/session rollback | runtime; text/web same-scene, duplicate-after-intervening-topic and rollback tests |
| Manual page/line/player portrait, narration, same speaker, preferences, keyboard/focus, transcript, replay/invalidation | playback; focused real AppClient browser portrait and recovery tests |
| Lawful possession, acting body versus owner, host-to-owner affinity; current shopping preserved | possession; mirror rejection, actual possessed scene and commander-purse/member-bag trade |
| Structured social identity and typed construction | social-identity; import/creation/rollback/no-persona-parser |
| Acting race/social/items/present companion/time/skill/proficiency/effective exposure incl worn bias; all/any | physical-conditions; exact boundaries, no consumption, no handler creation and possessed race browser fixture |
| Owner guild rank/quest lifecycle/claimed rewards and host-to-owner affinity | progression-conditions; canonical ordering, six-state semantics, repeatable records, private hints |
| Hidden/locked/open disclosure, hints, no protected pre-delivery, recheck, committed refresh | availability + locked-ui; sentinel omission, stale selection, every condition source refresh, keyboard refusal |
| Narrative owner persistence, formal versus refusal, pure-chain order, delivery receipt/context, text completion, cross-session | reading-server; guarded SQLite merge, two-connection/possession/delayed-A-after-B/text-failure tests |
| Memory-only pending ack retry/discard, no optimistic qualified unlock | reading-client; retry-without-reread, predecessor ordering, fresh reload/server-wins browser acceptance |
| Initial unread versus later unlock, refusal/unlock, relock/reopen, deferred dedup notice, no reconnect popup | unread-notices; first observation, live batch claim, post-scene toast, read and unread reopen |
| ALL 25 hosts / 100 fixed topic bodies plus 25 openings replaced | ten content slices, full four-topic inventory per host and source-backed line review; dynamic deterministic guild service prose remains native service output |
| Elves social standing, rarity, distinctive religion; no generic lore/OOC/player commitments | every content writer AND reviewer mandatory world source gate; explicit faith/civic/ciaran editorial checks |
| Docs, test ownership and repository gates | each owning change updates its docs/traceability/manifests and has focused commands; no empty final test-everything change |

## Integration boundaries

The model-only first change is a complete pure validator API with runnable synthetic tests, not an empty runtime subsystem. Runtime then converts every production caller/table and removes old authored shapes; its temporary old-prose scene data is explicitly replaced across the ten exhaustive content slices. No legacy authored adapter survives the complete batch. Generated package definitions and freeform line sessions remain native interfaces, not deprecated aliases. Backend protocol mirrors land atomically in runtime; manual scene presentation follows as its own fully functional slice. All behavior acceptance is owned by its implementing change, never deferred to a batch placeholder.


## Exact target files

- `world/lore/scenes.py (new)`
- `world/lore/dialogue/shape.py`
- `world/lore/dialogue/conditions.py (new)`
- `world/lore/tests/test_authored_scenes.py (new)`

## Risks / Trade-offs

Runtime cutover touches shape.py and its imports; serialize after this. No production consumers change here. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.lore.tests.test_authored_scenes
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
