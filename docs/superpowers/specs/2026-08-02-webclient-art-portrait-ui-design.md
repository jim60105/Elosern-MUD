# WebClient Scene Art and Portrait UI — Focused Design

**Date:** 2026-08-02
**Status:** Approved as part of the Browser-First MUD WebClient Suite
**Parent:** `2026-08-02-webclient-ui-design.md`
**Delivery units:** `art-assets`, then `webclient-art-panel`
**Dependencies:** `art-assets` depends on SceneBuilder, room scene-archetype seams, character/import age
gates, and bestiary/portrait-policy registries. `webclient-art-panel` depends on `art-assets` and
`webclient-oob-foundation`.

---

## 1. Intent

The engine design already reserves asynchronous, archetype-keyed scene art. This design broadens the
queue into a generic art-asset mechanism and adds contextual character portraits without changing scene
reuse. The browser displays the current scene as supporting atmosphere and overlays the currently focused
speaker or combat target. Missing or failed art is always a presentation degradation, never a gameplay
failure.

The work is split so the deterministic queue/worker/store can be verified without a browser, and the
panel can later consume only completed asset records and statuses. `art-assets` lands after SceneBuilder
so the generated named-NPC portrait lifecycle integrates with its real validated spawn path rather than a
forward-declared fake hook.

> **Amended 2026-08-05 (change `art-assets`).** Two scope clarifications for the `art-assets` delivery
> unit:
> 1. **Named-NPC portrait lifecycle scope.** `art-assets` delivers the validated portrait-policy seam on
>    the deterministic SceneBuilder spawn path (a spawned occupant carrying an explicit named portrait
>    policy schedules its unique-portrait ensure after the spawn transaction commits; today's role-based
>    scene NPCs carry no policy and resolve to no portrait), plus the unique-portrait lifecycles for
>    player-created and validated-import named characters — both reachable from real gameplay inputs.
>    Making generated quests *themselves* spawn named NPCs with unique portraits is deferred: it requires
>    an optional per-NPC portrait-policy field on `QuestBlueprint`/`StageSpawnRequirement`, which needs a
>    scenario-director dependency that `art-assets` does not have. The spawn-path seam this change
>    delivers is real and validated, exercised today by the generic no-policy path.
> 2. **Worker drain is claim-based and non-blocking.** Queue records gain an `in_progress` claim status
>    with a lease timestamp; the queue lock is held only for fast DB transactions (claim/settle), never
>    while the external worker subprocess runs (which executes on a background Twisted thread). A
>    successful worker result must exactly equal the engine's pre-computed expected output identity for
>    its job. This keeps the single-job GPU boundary while guaranteeing art never blocks play.
>
> **Amended 2026-08-05 (change `webclient-art-panel`).** Exploration-menu descriptors and the
> dialogue-speaker focus publisher are deferred to the `webclient-exploration-menu` delivery unit (23d),
> which is not a `webclient-art-panel` dependency and had not landed. `webclient-art-panel` (23f)
> delivers the complete read-only portrait catalog for currently focusable present entities — combat
> participants in combat mode, dialogue hosts and explicit named-policy characters present in the room
> in exploration mode — plus the combat descriptors that reference it (the `context_actions` participant
> `portrait_ref`), the scene renderer, and the targeted OOB art updates. The exploration mode therefore
> renders the catalog seam immediately, but a portrait card appears only once a 23d exploration descriptor
> publishes a client-local focus against that same catalog; until then, no focus means no portrait card.
> 23f acceptance covers catalog selection, no-focus, and combat focus; the end-to-end "exploration
> speaker" journey is completed by 23d against the same opaque present-entity catalog-key contract,
> with focus remaining entirely client-local.

---

## 2. Goals and Non-Goals

### Goals

- Preserve scene art keyed by `SceneArchetype`, not by room.
- Add explicit portrait subjects with stable identity and reuse policy.
- Give players and explicitly named NPCs unique portrait keys.
- Reuse one portrait for generic monsters of one bestiary archetype.
- Enforce the adult data invariant before any character portrait job is created.
- Use one serialized queue, external worker command, idempotent store, and staff retry path.
- Push art status/URL changes through the foundation OOB protocol.
- Provide truthful placeholders and accessible alternative text while offline or pending.

### Non-Goals

- No per-room scene images.
- No unique portrait for every generic monster instance.
- No generated combat animation, item art, map tiles, or gallery/history panel.
- No client call to Stable Diffusion.
- No player-triggered retry or regeneration.
- No gameplay state mutation based on image content or generation outcome.
- No live image service in tests.

---

## 3. Art Subject Model

### 3.1 Namespaced identity

| Subject kind | Key | Source of truth |
|---|---|---|
| Scene | `scene:<scene-archetype-key>` | immutable SceneArchetype registry |
| Named character | `portrait:character:<stable-character-key>` | explicit character portrait policy and stable key |
| Generic monster | `portrait:monster:<monster-archetype-key>` | immutable bestiary archetype registry |

Keys are validated before queue access. Prefix and subject key are stored separately in typed data even if
the serialized identity uses a colon namespace. A subject cannot change kind while retaining the same
full key.

### 3.2 Named-character policy

Unique portrait eligibility is explicit metadata established by character creation, validated import, or
NPC prototype creation. It is not inferred from capitalization, display-name uniqueness, quest role,
database key shape, or whether an LLM wrote the NPC.

The player's created character receives a stable character portrait key. Imported named NPCs receive one
only after the import record passes schema and age checks. Generated named NPC prototypes must carry a
validated portrait policy from the SceneBuilder schema before spawn; generic NPCs/monsters use a known
archetype or no portrait.

### 3.3 Subject descriptions

The registry/provider produces one deterministic natural-language description from allowed immutable or
validated character data. The LLM may help an external worker elaborate a prompt, but the engine's job
contains the canonical subject description and identity. It never includes secret state, mutable combat
resources, or disguised stats as physical truth.

Scene descriptions remain the one-sentence scene-archetype descriptions approved by the engine design.

---

## 4. Adult Portrait Gate

A character portrait subject is eligible only when canonical validated data establishes:

- `age >= 18`; and
- `apparent_age >= 18`.

Both values are checked immediately before enqueue in addition to import/creation validation. Missing,
malformed, or underage values reject the job with a named diagnostic and produce no queue record or
prompt. Prompt construction cannot replace an adult apparent age with younger language.

The permanent regression suite includes underage records for each field and asserts that neither reaches
the worker fixture. The browser receives only an unavailable placeholder and no rejected prompt content.

---

## 5. Enqueue Authority and Lifecycle

`world/art/service.py` owns art-subject synchronization and queue writes. Art records are presentation
assets, not canonical gameplay state, but no presenter, browser plugin, worker, or `world/ai` module may
write them.

The deterministic enqueue seams are:

- startup art synchronization idempotently ensures every registered SceneArchetype and generic bestiary
  portrait subject has an asset/queue record;
- successful player creation and validated character import schedule an eligible unique portrait ensure
  through `transaction.on_commit()`;
- validated named-NPC prototype spawn schedules its eligible unique portrait ensure after the spawn
  transaction commits;
- successful room entry calls `ensure_scene_asset()` for the room's validated archetype, covering dynamic
  registry content added after startup without allowing the art presenter to write;
- startup synchronization scans existing explicit unique portrait policies, recovering an enqueue that
  failed after an earlier gameplay commit.

Queue failure never rolls back character creation, import, NPC spawn, or movement. It logs a bounded
diagnostic and leaves the asset missing for the next idempotent lifecycle ensure. Underage or invalid
portrait data is a permanent eligibility rejection, not a transient queue failure. Generic bestiary
subjects use immutable adult-safe archetype descriptions and do not derive age from a spawned instance.

---

## 6. Asset Record and Queue

An asset record contains:

- full subject key and kind;
- deterministic source-description hash;
- status: `missing`, `pending`, `done`, or `failed`;
- same-store relative output identity, never a public URL supplied by the worker;
- attempt count, last error code, and relevant world/queue timestamps;
- expected aspect ratio;
- no live object reference.

The queue is keyed by subject identity. Enqueue is idempotent for an existing pending or done record.
Forced staff regeneration explicitly resets the record under the queue lock. A changed source-description
hash is reported for staff review; it does not silently replace a completed image during ordinary play.

Scenes and portraits share one lock and one worker concurrency slot. This preserves the approved
single-job GPU boundary. Scheduling remains settings-configurable and disableable.

---

## 7. Worker Contract

The prior scene-only conceptual input is replaced with:

```json
{
  "kind": "portrait",
  "key": "portrait:monster:gray_wolf",
  "description": "An adult gray-wolf monster archetype in the approved visual style.",
  "out_path": "server/.art/portrait/monster/gray_wolf.png",
  "aspect_ratio": "3:4"
}
```

Scene jobs use `kind="scene"` and `aspect_ratio="16:9"`. Worker output includes exact key, success/failed
status, output identity on success, and bounded error text on failure. The engine validates that every
output corresponds to an input job and that the resulting file remains under the configured art store.

The project is unreleased. The new contract replaces the old design contract directly; no format
negotiation, dual reader, or migration layer is added.

Generated files live under the gitignored `server/.art/` root. The `art-assets` delivery changes the
container art volume mount from `/app/world/art` to `/app/server/.art`; mounting over `/app/world/art`
would hide the importable `world/art/` service package. Media views map validated assets to same-origin
URLs without exposing this filesystem root.

The external worker may call local Stable Diffusion, use a prompt-writing agent, or use a fixed fixture.
That choice remains outside the engine. The worker cannot mutate character, room, quest, map, clock, or
combat state.

---

## 8. Art Presenter

The read-only art presenter resolves:

- current room scene archetype and its asset record;
- every currently focusable present entity from the combat/exploration presenter context;
- each focusable entity's portrait subject key according to explicit policy;
- asset status, server-generated same-origin media URL when done, dimensions/aspect, and alternative text;
- placeholder kind and explanatory label when unavailable.

The presenter never exposes `out_path`. URL construction validates that the stored output identity is
inside the configured media/art root and uses the application's own media route.

The art payload contains the current scene and a bounded `portrait_catalog` keyed by opaque present-entity
IDs. Combat and exploration menu descriptors reference catalog entries. Contextual focus remains entirely
client-local: KeyboardRouter notifies the art renderer, which selects a supplied catalog value. The client
does not send focus to the server and does not construct subject keys, URLs, status, or alternative text.
A full snapshot preserves focus only when that ID remains in the new catalog; otherwise exploration has
no portrait focus and combat selects the first valid target in deterministic presenter order.

---

## 9. Panel Behavior

### 9.1 Scene

The scene uses the panel's 16:9 area with cover-style cropping while preserving a click-to-open full view.
Alternative text and scene label remain visible outside the bitmap. Enter on the focused image opens the
same full view as click; Escape closes it.

If the current scene is pending and a prior scene is already rendered, the panel retains that prior image
visibly dimmed and labelled `目前場景圖片生成中`. Without a prior image it uses the scene placeholder. A
failed or invalid asset always uses the scene placeholder. The panel never silently presents old art as
current.

### 9.2 Portrait overlay

The 3:4 portrait overlays the scene at bottom right without covering the scene label or required status.
It displays the focused entity's name and role/target context. No focus means no portrait card. Missing
portrait means a portrait placeholder card rather than removal if a focused character exists.

The portrait has its own accessible full-view control. The panel does not stack multiple portraits or
provide a history gallery in this suite.

### 9.3 OOB updates

Room or present-entity-set changes replace the art payload from ordinary presentation updates. A local
focus move switches an existing catalog entry and requires no OOB packet. A worker completion sends a
targeted art-panel update only to connected sessions whose current scene or portrait catalog references
that subject key. Late completion for an old room or no-longer-present entity may be cached but must not
replace the current panel.

---

## 10. Failure and Degradation

- Scheduler disabled: records remain missing/pending; placeholders remain; gameplay proceeds.
- Worker unavailable/timeout: bounded failure record and staff-visible diagnostic; no browser traceback.
- Invalid output key/path/status: reject worker batch item and retain prior valid asset record.
- Missing file for a done record: presenter treats it as unavailable and logs storage inconsistency.
- Malformed age/portrait policy: do not enqueue and do not leak source data.
- OOB disconnected during completion: reconnect snapshot resolves current asset status from store.
- Browser image load fails: show fallback text/placeholder and do not repeatedly fetch without a new URL
  or user reload.
- LLM unavailable: deterministic description and fixed worker/degradation behavior remain valid.

---

## 11. Staff Operations

The existing planned `@art` family is broadened to understand namespaced subjects:

- status lists/filter by scene or portrait;
- run drains the shared queue with optional bounded limit;
- retry retries failed records;
- requeue accepts one validated full subject key and forces regeneration;
- ordinary players have no access to these controls.

Status output never includes sensitive persona text or unrestricted local paths.

---

## 12. Tests and Acceptance

### Subject and queue tests

- Valid/invalid namespaced keys and duplicate registration.
- Scene reuse across rooms with one archetype.
- Unique player/named NPC key and shared generic-monster key.
- Explicit named policy; no inference from display name.
- Enqueue/done idempotence, shared serialization lock, retry, and forced requeue.
- Startup scene/generic sync, creation/import post-commit, named-NPC post-commit, room-entry ensure, and
  startup recovery triggers.
- Queue failure does not roll back gameplay; rolled-back creation/import/spawn emits no post-commit job.
- Output path confinement and mismatched worker output rejection.
- Source-description hash behavior.

### Adult invariant tests

- `age=17` rejects before queue/worker.
- `apparent_age=17` rejects before queue/worker.
- Missing/malformed values reject.
- Valid adult fixture reaches a fake worker with adult description.
- Browser payload never contains a rejected prompt.

### Presenter/panel tests

- done, missing, pending, failed, scheduler-disabled, and missing-file states.
- Same-origin URL only; no filesystem path.
- Exploration speaker and combat target focus.
- Catalog contains only currently present focusable identities and verified portrait presentation data.
- Keyboard focus switches catalog entries without a server focus packet.
- Late old-subject completion does not replace current art.
- Prior scene, when retained, is dimmed and explicitly labelled.
- Keyboard full view, Escape, alternative text, and placeholder accessibility.
- 16:9 scene and 3:4 portrait remain usable at both supported desktop viewports.

### Offline acceptance

With the worker command fixed to fail and all LLM profiles unavailable, movement, dialogue, combat,
quests, and services continue through their deterministic paths while every art state degrades to the
approved placeholders.
