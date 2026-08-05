## Context

The `art-assets` delivery unit (roadmap 22) has landed and owns the complete deterministic art
backend: namespaced subjects, the adult portrait gate, `world/art/service.py` as sole asset/queue
writer, the claim-based serialized queue, the external worker contract, the scheduler, the `@art`
staff commands, same-origin media URLs, and the read-only resolution primitives in
`world/art/presenter.py` (`resolve_scene`, `resolve_character`, `resolve_subject`). The
`webclient-oob-foundation` delivery unit (23a) has landed and provides the exact versioned OOB
envelopes, the per-session presentation coordinator, the duplicate-rejecting presentation registry
(panels `status`, `context_actions`, `local_map`, `services`, `creation`), the allowlisted action
dispatcher, the client state store, the KeyboardRouter, and the GoldenLayout shell whose `art`
component is still the foundation placeholder ("場景圖像的生成與顯示尚未開放"). `webclient-combat-menu`
(23b) landed the `context_actions` panel with a deliberately null `portrait_ref` seam in
`world/rules/combat_view.py`, and `webclient-character-creation-ui` (23g) landed the `creation`
panel. `webclient-exploration-menu` (23d) has **not** landed, so there is no exploration dock or
exploration presenter context yet.

Roadmap item 23f (`webclient-art-panel`) delivers the graphical consumption of the art backend: a
read-only `art` panel, the scene renderer, the contextual portrait overlay, and targeted OOB art
updates. It depends only on 22 and 23a. Every constraint that shapes this design:

1. **Presentation is read-only and server-authoritative.** Presenters never mutate state; the browser
   renders server-authored payloads and never constructs a subject key, URL, status, or alternative
   text; the adult gate is never weakened and rejected content never reaches a worker or the browser.
2. **`world/art/` stays a deterministic, web-free package.** The repository deterministic-path
   contract scans `world/art/` for `world.ai`/`ollama`/`llm_client` fragments (green, unchanged), and
   `world/art/` must not import `web/`. Any completion notification must therefore cross that boundary
   through a decoupled mechanism.
3. **Art is presentation, never gameplay.** Offline acceptance: with the worker command fixed to fail
   and every LLM profile unavailable, movement, dialogue, combat, quests, and services proceed while
   every art state degrades to the approved placeholders.
4. **The focused design is the contract.** `docs/superpowers/specs/2026-08-02-webclient-art-portrait-ui-design.md`
   §8, §9, and §10 fix the panel, catalog, focus model, OOB updates, and failure semantics. The combat
   panel's `portrait_ref` seam (`docs/superpowers/specs/2026-08-02-webclient-combat-ui-design.md` D1)
   is the pre-declared integration point: "A later art change may introduce a new panel schema version
   rather than letting the browser construct portrait keys."

## Goals / Non-Goals

**Goals:**

- Register one read-only version-1 `art` panel, available in `exploration` and `combat` modes and
  unavailable (common form) in `creation` mode.
- Deliver the scene renderer (16:9 cover-style crop, label and alternative text outside the bitmap,
  click/Enter full view, Escape close) with truthful placeholders and the dimmed, labelled
  retention of a prior scene while the current one is pending.
- Deliver a bounded `portrait_catalog` of currently present focusable entities — combat participants
  in combat mode, dialogue hosts and named-policy characters in the current room in exploration mode —
  each resolving to a server-authored, adult-gated portrait value or a truthful placeholder card.
- Keep contextual focus entirely client-local and verified; no focus mutation message; focus survives
  a snapshot only when the catalog ID survives.
- Populate the `context_actions` participant `portrait_ref` by advancing that panel to schema
  version 2, keeping server and browser on the exact same reference contract.
- Push targeted `art` panel updates when a worker completes an asset, only to connected sessions whose
  current scene or catalog references that subject key.
- Extend Node, Evennia, and managed Playwright gates with the full art degradation and acceptance
  matrix, all offline.

**Non-Goals:**

- No exploration dock/menu, dialogue-speaker menu, movement, look, or interaction surfaces — those
  are 23d; this change ships the catalog seam they will reference, plus the scene renderer that works
  for every mode today.
- No per-room scene images (D10), no gallery/history panel, no stacked portraits, no combat
  animation, item art, or map tiles.
- No change to the `world/art/` lifecycle, queue, worker, scheduler, `@art` commands, media route, or
  adult gate beyond the additive completion-notification seam and one additive presenter helper.
- No gameplay state mutation from image content or generation outcome, no player-triggered
  regeneration, no client call to Stable Diffusion, and no focus message sent to the server.
- No mobile acceptance, no new runtime dependency, no database migration, no backward-compatibility
  adapter, and no Telnet change.
- No change to the OOB protocol envelope set or global bounds; `ui_update` already supports
  server-initiated panel replacement, so this change adds no new message name.

## Decisions

### D1. One read-only `art` panel, schema version 1, thin presenter over a frozen view

The production presentation registry registers a single `art` panel (`schema_version: 1`). Its
available payload contains exactly `schema_version`, `available`, `kind` (`"scene"`), `scene`, and
`portrait_catalog`:

```jsonc
{
  "schema_version": 1,
  "available": true,
  "kind": "scene",
  "scene": {
    "archetype": "tavern_interior",
    "label": "酒館內部",                          // SceneArchetype.display_name_zh
    "subject_key": "scene:tavern_interior",
    "status": "done" | "missing" | "pending" | "failed" | null,
    "url": "/art/scene/tavern_interior.png" | null,
    "aspect_ratio": "16:9",
    "alt": "…",
    "placeholder": { "kind": "missing"|"unavailable", "label": "未生成"|"無法提供" } | null
  },
  "portrait_catalog": {
    "42": {                                       // opaque present-entity catalog key
      "subject_key": "portrait:character:42" | "portrait:monster:gray_wolf" | null,
      "status": "done" | … | null,
      "url": "/art/…" | null,
      "aspect_ratio": "3:4",
      "alt": "…",
      "placeholder": { "kind": "missing"|"unavailable", "label": "…" } | null,
      "context": { "name": "…", "role": "敵方" | "隊友" | "對話對象" | "人物" }
    }
  }
}
```

The presenter (`web/webclient/presentation/art.py`) is a thin serializer over the frozen view (D2)
and the `world/art/` resolution primitives, and it validates its own output against the exact bounded
schema before returning it — the same pattern as `services.py`/`combat_panel.py`/`creation.py`.
Outside `exploration`/`combat` it raises `PanelUnavailableError` so the registry emits the common
unavailable form. The `scene` object mirrors `world.art.presenter.resolve_scene` output plus the
registry label and archetype key; the catalog entries compose `world.art.presenter` output with the
entity display context.

**Why one panel instead of scene and portrait sub-panels:** the panel registry and client store model
whole-panel replacement; one `art` panel keeps the allowlist delta and snapshot handling minimal and
lets the scene and its contextual catalog travel in one atomic adoption, which is exactly what the
focused design's "room or present-entity-set changes replace the art payload" needs.

### D2. A frozen no-mutation art view derives scene and present-focusable entities

`world/rules/art_view.py` exposes a frozen read-only view, mirroring `combat_view.py` / `service_view.py`:

- `ArtView.scene_archetype: str | None` — the actor's current location's validated `scene_archetype`
  (via `SceneArchetypeMixin`); `None`/unresolvable means the scene payload is the unavailable
  placeholder.
- `ArtView.entities: tuple[ArtEntityView, ...]` — the bounded, deterministic, currently present
  focusable set. `ArtEntityView` carries the opaque identity, bounded display name, stable role label,
  and the resolved portrait subject decision (character named-policy / monster archetype / none).
- Mode selection is explicit: in combat mode the entity list comes from one shared frozen roster
  query — `world/rules/combat_view.py` exposes `combat_participants(actor)` returning the ordered
  participant identities from persisted `player_ids` then `enemy_ids` without any portrait data — that
  `build_combat_view` and `build_art_view` both consume, so the two panels can never drift on roster
  or order; in exploration mode it comes from the current room's `contents` filtered to dialogue hosts
  (`world.rules.dialogue.is_dialogue_host`) and characters carrying an explicit named `portrait_policy`,
  in deterministic room-contents order, capped at `MAX_PORTRAIT_CATALOG` (32, matching the inventory
  row bound) with deterministic truncation.

The view performs no writes, never lazily constructs handlers, never reads `disguised_stats` or
persona, and returns frozen values. Pure tests exercise entity classification and ordering without an
Evennia session. **Why in `world/rules/` rather than the presenter:** the project's established read
model pattern keeps every JSON-safe interpretation in one frozen rules module (combat view owns the
`portrait_ref` seam this change populates), keeps the presenter a thin serializer, and gives 23d a
single deterministic source for the same present-entity set so the exploration menu and the art panel
cannot drift. **Why a shared roster query instead of calling `build_combat_view` from the art view:**
`build_combat_view` is a full panel view and would create a two-view cycle once combat's
`portrait_ref` is filled from the art catalog decision (`build_combat_view → build_art_view →
build_combat_view`). The roster query is the one-directional dependency: `build_combat_view` and
`build_art_view` both read it, and both read the catalog-key mapper (D3/D4) — neither calls the
other's full view.

### D3. Centralized portrait subject resolution dispatches by entity kind

The catalog-key mapper is one shared function in `world/rules/art_view.py`:
`portrait_catalog_key(entity_identity) -> str` renders the opaque present-entity catalog key as the
single bounded decimal-string form (e.g. `"42"` from identity `42`); both `build_art_view` (to key
the catalog) and `build_combat_view` (to fill `portrait_ref`) use exactly this function, so a focus
lookup can never silently miss because of an `42` vs `"42"` mismatch. The string form is asserted by
server/Node parity fixtures.

`world/art/presenter.py` gains one additive helper `resolve_entity(entity) -> dict` that classifies
the present entity and resolves the portrait value:

- A **generic monster** (an entity whose `threat_tier` attribute resolves in `MONSTER_TIER_REGISTRY`)
  resolves `portrait:monster:<threat_tier>` through `monster_subject_for` + `resolve_subject`. No
  adult gate applies — generic bestiary subjects use immutable adult-safe archetype descriptions and
  never derive age from a spawned instance (focused design §4/§5).
- A **character** resolves through the existing `resolve_character` path: explicit named
  `portrait_policy` + immediate `age >= 18` and `apparent_age >= 18` gate + `resolve_subject`. A
  missing policy or a gate rejection (missing, malformed, or under-18 `age` or `apparent_age`) yields
  the unavailable placeholder with no subject key, no URL, and no prompt content.
- Anything else yields the unavailable placeholder.

Subject-kind classification therefore stays in the art domain (the `world/art/` subject-model owner),
the web presenter never branches on typeclasses, and the adult gate remains exactly one
immediate-before-enqueue/presentation check. The scene payload always resolves through the existing
`resolve_scene(archetype)`.

**Why a new helper instead of reusing `resolve_character`:** `resolve_character` reads
`portrait_policy` and the character gate; a generic monster carries no policy and would resolve to
"無肖像" forever, contradicting the approved generic-monster archetype portraits (engine design §8
amendment, D15). The helper keeps that classification in one deterministic place.

### D4. `context_actions` advances to schema version 2 with a populated nullable `portrait_ref`

The combat panel was designed with `portrait_ref` as the reserved seam and today's schema-version-1
validator rejects any non-null value. This change advances `context_actions` to schema version 2:
each participant's `portrait_ref` SHALL equal the art catalog key (D3's single string form) whenever
that participant is present in the art catalog — **including** a catalog entry that resolves to a
placeholder card (a gate-rejected character or a generic monster) — and SHALL be `null` only when the
participant is absent from the catalog. Because the combat catalog contains every present
participant, `portrait_ref` is populated for all participants in combat; the `null` branch stays for
the same reason the field was nullable — it is the explicit server-authored "no portrait card"
signal and remains correct if a future schema excludes entities from the catalog. The subject
reference is never a subject key: generic monsters share one subject per archetype, so only the
opaque entity-level catalog key can uniquely bind the participant's name/role context to its catalog
entry.

The change is an internal, versioned panel schema evolution — panel `schema_version` exists precisely
to express this — applied together across `world/rules/combat_view.py` (populate the field via the
shared catalog-key mapper, reading the same roster query D2 defines), `web/webclient/presentation/combat_panel.py`
(accept and emit the reference, dropping the version-1 "must be null" branch), `web/static/webclient/js/elosern/protocol.js`
(version-2 validator), and the version-1 test fixtures. The project is unreleased, so no
compatibility overload or dual reader is added. The browser still never constructs a subject key or
URL: it treats `portrait_ref` as an opaque key into the art catalog it already holds.

**Combat results update the art catalog atomically.** Because a combat action can defeat, flee, or
settle a session — changing the participant roster — combat-action completion publishes `status`,
`context_actions`, **and** `art` replacements at one newer revision (amending the `webclient-combat-menu`
"Combat results update canonical panels" requirement in the delta specs). This guarantees a
no-longer-present entity's portrait can never outlive the combat result that removed it, and it is
exactly the focused design's "room or present-entity-set changes replace the art payload".

**Why populate `portrait_ref` rather than letting the browser match by participant identity:** the
approved combat and art designs both specify server-authored catalog references; reusing the reserved
field keeps one explicit contract (menu descriptors reference catalog entries) and keeps the browser a
pure renderer.

### D5. Targeted OOB art updates via a decoupled completion notification

When the worker settles a terminal result, `world/art/` emits a Django signal (project-local
`asset_completed`, payload = the completed full subject key only). A subscriber in
`web/webclient/presentation/art_push.py` (connected from `at_server_start`, deferred-import style like
the other registration seams) performs the push.

**Reactor-thread guarantee (explicit).** The existing worker settles on a background Twisted thread
(`world/art/worker.py` runs `_run_and_settle_batch` inside `deferToThread`; the codebase as landed has
no reactor-thread callback after settlement), so the signal SHALL NOT be emitted from the settle path
itself. Instead:

1. `_run_and_settle_batch` collects and returns the subjects whose `settle()` actually applied a
   terminal status (the existing `settle()` returns the record, or `None` for a stale no-op — exactly
   the "only after the record was really updated" guard the focused design's failure rules require).
2. `drain()` attaches a success callback to the existing `deferToThread` Deferred
   (`_notify_completed_batch`), which runs on the reactor thread and emits `asset_completed` per
   settled subject. `drain_synchronous()` calls the same `_notify_completed_batch` on its calling
   thread for deterministic tests. No subscriber ever runs on the worker subprocess thread.
3. The subscriber is registered with a stable `dispatch_uid`, iterates sessions with per-session
   exception isolation (a bad session logs a bounded diagnostic and cannot stop the others), verifies
   the coordinator is still attached to a live WebClient session with an active puppet, and never
   propagates an exception back into the `world/art/` settle path.

The push itself, for each connected WebClient session with an attached presentation coordinator and an
active puppet, re-renders that session's `art` panel from canonical state (art view + presenter, no
state mutation). If the rendered scene subject key, or any catalog entry subject key, equals the
completed key, it calls `coordinator.panel_update(context, {"art": payload})`, which allocates one new
revision and sends a targeted `ui_update`; otherwise the session's current art does not reference the
subject and no push occurs. Sessions in `creation` mode have an unavailable `art` panel and receive
nothing; sessions whose puppet has since left the room or ended the combat produce a payload that no
longer references the subject and receive nothing — this is exactly the "late completion for an old
room or no-longer-present entity may be cached but must not replace the current panel" rule, enforced
by re-deriving from current canonical state rather than by remembering what was sent.

`world/art/` never imports `web/`; the signal is emitted by the deterministic package and consumed by
the presentation package, preserving the dependency direction and the repository deterministic-path
contract (which scans fragments, not signals). Signal delivery runs on the reactor thread (the
`deferToThread` success callback), so it cannot interleave with action-completion publication; the
coordinator's single revision allocation keeps all published revisions unique and ordered. A guarded
test asserts the signal payload contains only the subject key, that no `world/art/` module imports
`web/` or `world.ai`, that the subscriber never runs on the worker thread, and that a bad session
cannot stop notification to the others.

**Why a signal rather than a poll or a direct callback:** polling on room entry/snapshot would be
reactive only to player movement and would never deliver a mid-scene completion without extra traffic;
a direct call from `world/art` into the coordinator would break the package boundary. The signal is
the smallest decoupled boundary that satisfies "the engine's only job is the queue" and "presenters
and workers never enqueue".

### D6. Client-side art model and renderer are DOM-independent and focus is local

`web/static/webclient/js/elosern/art_panel.js` is a DOM-independent module (Node-testable, no DOM)
that:

- validates the `art` panel payload against the exact schema (dual-direction parity with the server
  validator in `web/webclient/presentation/art.py`, enforced by a parity test as the other panels do);
- reduces the validated payload into a scene view (asset / placeholder / pending-with-prior-image
  dimmed retention) and a portrait catalog keyed by the opaque catalog IDs;
- holds client-local `focusKey` state with the approved snapshot-adoption rule: keep the focus when the
  ID survives the new catalog; otherwise exploration has no focus and combat selects the first valid
  participant in deterministic presenter order;
- exposes open/close full-view state for the scene and the portrait.

The GoldenLayout `art` component (replacing the placeholder `registerUnavailable` registration in
`web/static/webclient/js/plugins/goldenlayout.js`) renders the model: cover-style 16:9 scene, label +
alternative text outside the bitmap, dimmed prior image with `目前場景圖片生成中` when pending, the 3:4
portrait card at bottom right with name + role context and its own full-view control, click/Enter to
open full view, Escape to close, and truthful placeholders throughout. Server-authored labels are
inserted as text nodes, never trusted HTML; reduced-motion preference disables nonessential
transitions.

Contextual focus flows client-locally: the docks publish a `focusKey` through a tiny in-memory focus
subscription, and the art renderer subscribes. Today the combat dock publishes its highlighted
participant; 23d's exploration dock will publish the dialogue speaker against the same catalog. No
focus means no portrait card; a focused entity with a missing portrait shows the portrait placeholder
card. This is the design's "KeyboardRouter notifies the art renderer" without any new message.

**Why a separate DOM-independent module rather than code in `goldenlayout.js`:** every other panel
(combat dock, services dock, creation dock, local map) keeps a DOM-independent model for Node tests
and a thin GoldenLayout renderer; the art panel follows the same split so protocol validation, focus
selection, and snapshot-adoption rules are covered without a browser.

### D7. Degradation, bounds, and verification stay fully offline

- **Bounds:** the catalog is capped at `MAX_PORTRAIT_CATALOG = 32` entries; every string and list is
  bounded below the global protocol limits; a worst-case serialization test proves the structurally
  maximal realistic payload fits far below the 65,536-byte envelope and that an all-ceilings payload
  is rejected — mirrored in Node.
- **Degradation matrix:** scheduler disabled (records stay missing/pending → placeholders), worker
  unavailable/timeout (bounded failure record, staff-visible diagnostic), missing file for a done
  record (presenter treats as unavailable, logs storage inconsistency), invalid output key/path/status
  (retain prior valid record), OOB disconnect during completion (reconnect snapshot resolves from
  store), browser image load failure (fallback text/placeholder, no repeated fetch without a new URL),
  and LLM unavailable (deterministic descriptions and fixed worker behavior remain valid).
- **Offline acceptance:** a regression scenario runs movement, dialogue, combat, quests, and services
  with `ART_WORKER_CMD` fixed to fail and every LLM profile unavailable, asserting every art state
  degrades to placeholders and gameplay never blocks.
- **Gates:** pure `unittest.TestCase` for the art view and client model; `EvenniaTest` for the
  presenter, adapter-adjacent coordinator push, and signal boundary; Node tests for the art panel
  reducer and the `context_actions` version-2 validator; managed Playwright journeys for done, pending,
  failed, offline, missing-file, keyboard full view, catalog focus switching (no packet), late
  completion, adult-gate payload exclusion, and both supported viewports. No test calls an LLM, image
  generator, or remote service.

## Risks / Trade-offs

- [Exploration catalog is a seam without an exploration menu until 23d] → The catalog, resolution,
  bounds, and client-local focus model are fully delivered and tested; 23d will only add menu
  descriptors that reference the same catalog IDs. Default no-focus (no portrait card) is the approved
  behavior, so the panel is correct before 23d and complete after it.
- [`portrait_ref` equals the participant identity key in combat, so it looks redundant] → It is the
  reserved, server-authored catalog reference by design; the null branch and future catalogs that
  exclude entities keep it meaningful, and it guarantees the browser never derives a portrait from
  entity data (D4).
- [A completion signal could race action-completion publication] → Evennia's single Twisted reactor
  serializes all publishes; the coordinator's single revision allocation keeps revisions unique and
  ordered, and a test asserts a push never interleaves between a completion presentation and its
  result (D5).
- [Signal delivery on a worker thread could touch the DB unsafely] → The signal is never emitted
  from the settle path; `_run_and_settle_batch` only returns the subjects whose `settle()` actually
  applied a terminal status, and the notification is emitted from the `deferToThread` success
  callback, which runs on the reactor thread (`drain_synchronous` emits on its calling thread for
  deterministic tests). A test asserts the subscriber never runs on the worker thread (D5).
- [A combat result could leave a stale portrait for a removed participant] → Combat-action completion
  publishes `status`, `context_actions`, and `art` together at one newer revision, so a defeated,
  fled, or settled participant leaves the catalog in the same `ui_update` that removed it (D4, combat
  delta).
- [A catalog-key string mismatch could break focus lookup] → One shared mapper
  `portrait_catalog_key` defines the single decimal-string form used by both panels, asserted by
  server/Node parity fixtures (D3).
- [Present-entity enumeration could grow a large room's catalog] → Cap at 32 with deterministic
  truncation and a worst-case serialization test; the combat roster is already bounded by
  `MAX_PARTICIPANTS` (D2/D7).
- [A monster's `threat_tier` could be missing or invalid] → `resolve_entity` validates against
  `MONSTER_TIER_REGISTRY` and falls back to the unavailable placeholder with a bounded diagnostic;
  no record is created and no prompt is built (D3).
- [The dimmed prior scene could be mistaken for current art] → The panel keeps it visibly dimmed and
  explicitly labelled `目前場景圖片生成中`, and a late completion never replaces the current scene
  (spec + D6).
- [Schema-version bump of `context_actions` could break the version-1 client] → Panel schema versions
  exist precisely for this; the client and server validators, fixtures, and tests move to version 2 in
  one change, and the project is unreleased so no compatibility layer is needed (D4).

## Migration Plan

No stored schema change and no data migration: the new `art` panel, the frozen art view, the additive
`resolve_entity` helper, the `context_actions` schema-version bump, the completion signal, and the
client modules are all additive. Implement in dependency order:

1. `world/rules/art_view.py` (the shared combat roster query in `world/rules/combat_view.py`, the
   frozen view + bounds, and the `portrait_catalog_key` mapper) with pure tests; `world/art/presenter.py`
   `resolve_entity` with tests (character / monster / invalid classification, both adult gate fields).
2. `web/webclient/presentation/art.py` (exact validator + presenter), register `art` in
   `web/webclient/presentation/registry.py`, and mirror the validator in
   `web/static/webclient/js/elosern/protocol.js` with a dual-parity test.
3. `context_actions` schema version 2: populate `portrait_ref` in `world/rules/combat_view.py` via the
   catalog-key mapper, update `web/webclient/presentation/combat_panel.py`, the JS validator, and
   version-1 fixtures; extend combat-action completion to publish `art` alongside `status` and
   `context_actions`.
4. Completion notification: `world/art/worker.py` returns the actually-settled subjects and emits
   `asset_completed` from the `deferToThread` success callback; add
   `web/webclient/presentation/art_push.py` subscriber (stable `dispatch_uid`, per-session isolation)
   wired from `at_server_start`; coordinator push tests.
5. Client: `art_panel.js` model + Node tests; GoldenLayout `art` component replacing the placeholder;
   client-local focus subscription; snapshot-adoption focus rules.
6. Managed Playwright art acceptance journeys; offline acceptance scenario; `covers_requirement`
   annotations for every new/modified main-spec requirement; `tools.spec_traceability check`;
   `openspec validate webclient-art-panel --strict` and `--all --strict`; the affected package suites,
   the repository contract tests, `compileall`, and `git diff --check`.

Rollback is the ordinary code-revision rollback: removing the panel registration, the signal and its
subscriber, the view/helper, and the client renderer returns the shell to the placeholder state; no
data restore or dual reader is required because the change persists nothing and never weakens an
existing deterministic check.

## Open Questions

None blocking. Two documented seams keep 23f correct before and after its sibling changes: the
exploration present-entity catalog is populated by this change and will be referenced by 23d's menu
descriptors, and the client-local focus source is the combat dock today with the dialogue speaker to
be published by 23d. Both are covered by the approved focused design and this change's tests. The
deferral of exploration-menu descriptors and the dialogue-speaker focus publisher to 23d is recorded
as a dated amendment in `docs/superpowers/specs/2026-08-02-webclient-art-portrait-ui-design.md`
(§1), following the same dated-amendment convention the `art-assets` change used.
