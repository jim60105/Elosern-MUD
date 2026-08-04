## Why

The engine design (§8, D10, D11) reserves asynchronous, archetype-keyed scene art with an external
worker boundary, and the approved Browser-First WebClient suite (D15) adds a separate portrait subject
type with an adult age gate. Change 21 delivered the real validated spawn path (SceneBuilder in
`world/quests/`) that a generated named-NPC portrait lifecycle must integrate with, but none of the
deterministic art backend exists: there is no subject model, no adult portrait gate, no enqueue
service, no serialized queue, no worker contract, no asset store, no `@art` commands, no scheduler,
and the container still mounts a volume over the importable `world/art/` package path. Change 23f's
panel can only consume completed asset records and statuses, so `art-assets` must land first and be
fully verifiable with no browser and no live image service.

## What Changes

- Add the deterministic `world/art/` package implementing the approved `art-assets` delivery unit
  (`docs/superpowers/specs/2026-08-02-webclient-art-portrait-ui-design.md`):
  - **Art subject model** (`world/art/subjects.py`): namespaced subject keys — `scene:<archetype>`,
    `portrait:character:<stable-key>`, `portrait:monster:<archetype>` — with prefix and subject key
    stored as typed data, key validation before any queue access, and a rule that a subject can never
    change kind while keeping the same full key.
  - **Adult portrait gate** (`world/art/adult.py`): every character portrait enqueue re-checks
    canonical validated `age >= 18` **and** `apparent_age >= 18` immediately before enqueue. Missing,
    malformed, or underage values reject with a named diagnostic, produce no queue record and no
    prompt, and never reach a worker fixture. Permanent regression tests cover `age = 17` and
    `apparent_age = 17`.
  - **Enqueue authority and lifecycle** (`world/art/service.py`): the sole writer of asset/queue
    records, reachable only through deterministic seams — idempotent startup synchronization that
    ensures every registered `SceneArchetype` and generic bestiary portrait subject has a record;
    startup recovery that rescans explicit unique portrait policies; `transaction.on_commit()`
    scheduling for successful player creation and validated character import; post-commit scheduling
    for validated named-NPC prototype spawn (the SceneBuilder spawn path); and `ensure_scene_asset()`
    on successful room entry. Queue failure never rolls back creation, import, spawn, or movement.
  - **Asset records and one serialized queue** (`world/art/queue.py`, `world/art/store.py`): records
    keyed by subject identity carrying kind, source-description hash, status
    (`missing`/`pending`/`in_progress`/`done`/`failed`), same-store relative output identity, attempt
    count, last error code, world/queue timestamps, and expected aspect ratio — never a live object
    reference. Enqueue is idempotent for pending/in_progress/done records; forced staff regeneration
    resets under the queue lock. Scenes and portraits share one lock and one worker concurrency slot.
  - **Worker contract** (`world/art/worker.py`): the swap point. A job is
    `{kind, key, description, out_path, aspect_ratio}`; output is `{key, status, output_identity,
    bounded error}`. Drains are **claim-based and non-blocking**: the queue lock is held only for fast
    DB transactions (ensure/claim/apply results), never while the external worker subprocess runs —
    the subprocess runs on a background Twisted thread, so the scheduler Script tick, `@art run`, and
    `on_commit` enqueues never block play. A claimed record enters `in_progress` with a lease
    timestamp; a crash or timeout lease is reclaimed to `pending` by the next drain/recovery. The
    engine pre-computes the exact expected relative output identity for each job, and a successful
    result must equal it exactly (not merely stay under the store root) with an existing regular file;
    every input job must reach exactly one terminal result, and missing/duplicate/unparseable results
    mark the unfinished claimed jobs failed. The worker may call local SD, a prompt-writing agent, or a
    fixed fixture — that choice stays outside the engine, and the worker cannot mutate game state.
  - **Read-only presenter primitives** (`world/art/presenter.py`): resolve a validated subject to its
    status, same-origin media URL, aspect, and alternative text, or to a truthful placeholder kind and
    label; never expose `out_path`. The present-entity focus catalog that joins combat/exploration
    presenter contexts remains change 23f's.
  - **Scheduler** (`world/art/scheduler.py`): a settings-configurable, disableable periodic drain.
  - **Media URL serving** (`web/art_media.py` + route): map validated stored output identities to
    same-origin URLs without exposing the `server/.art/` filesystem root.
- **Fix the container art volume.** Change the art mount from `/app/world/art` to `/app/server/.art`
  in `compose.yaml` and `Containerfile` (and the container-contract test), so the importable
  `world/art/` package is never masked by a mount. The `.gitignore` entry `server/.art/` already
  exists.
- **Add the `@art` staff commands** (`commands/art.py`): `@art status` (list/filter scene or
  portrait), `@art run [--limit N]` (drain asynchronously, never blocking play), `@art retry`
  (failed records), and `@art requeue <subject-key>` (validated full key, forced regeneration). Staff
  only; status output never includes persona text or unrestricted local paths.
- **Wire the named-NPC portrait lifecycle into the real spawn path.** SceneBuilder's occupant spawn
  gains the validated portrait-eligibility seam: a spawned occupant carrying an explicit validated
  portrait policy schedules its unique-portrait ensure after commit; today's role-based scene NPCs
  carry no policy and resolve to "no portrait" (placeholder), so the hook is exercised by the generic
  path without inventing named NPCs. The player-created and validated-import named characters DO get
  unique portraits through real gameplay inputs. No `QuestBlueprint`/`StageSpawnRequirement` schema
  change — making generated quests themselves produce *named* NPCs would require a scenario-director
  (change 20) dependency this change does not have, so it is explicitly deferred and documented in a
  dated amendment to the focused design document.
- **Amend the focused design document** (`2026-08-02-webclient-art-portrait-ui-design.md`) with a
  dated note recording the scope split above: change 22 delivers the validated portrait-policy seam
  and the unique-portrait lifecycles for player-created and imported named characters; generated
  *named* NPCs await an optional per-NPC portrait-policy field on the blueprint.
- No backward-compatibility adapters or persisted-data migrations; the project is unreleased with no
  users in the wild.

## Capabilities

### New Capabilities

- `art-subject-model`: Namespaced art subject identity (`scene:`, `portrait:character:`,
  `portrait:monster:`), typed prefix/key storage, key validation before queue access, the explicit
  named-character portrait-policy rule (eligibility is metadata, never inferred from display name,
  quest role, key shape, or LLM authorship), and deterministic adult-safe subject descriptions.
- `adult-portrait-gate`: The immediate-before-enqueue check of both `age >= 18` and
  `apparent_age >= 18` for every character portrait subject; named rejection without a queue record
  or prompt; permanent underage regression tests for each field.
- `art-asset-lifecycle`: `world/art/service.py` as the sole asset/queue writer and its deterministic
  seams — idempotent startup sync of scene and generic-monster subjects, startup recovery of explicit
  unique portrait policies, post-commit player-creation/import scheduling, post-commit named-NPC
  spawn scheduling, and room-entry `ensure_scene_asset()` — with queue failure never rolling back
  gameplay.
- `art-queue-worker`: The asset record contract, the idempotent subject-keyed queue, the shared
  scene+portrait serialization lock, the external worker contract with input/output validation and
  path confinement under `server/.art/`, the settings-configurable disableable scheduler, and
  same-origin media URL serving.
- `art-staff-commands`: The `@art status` / `@art run` / `@art retry` / `@art requeue` family,
  restricted to staff, with status output that never leaks persona or filesystem paths.

### Modified Capabilities

- `scene-builder`: The occupant spawn path gains the portrait-eligibility seam — a spawned occupant
  carrying an explicit validated portrait policy schedules its unique-portrait ensure after commit,
  and today's role-based scene NPCs (no policy) resolve to no portrait. The materialization
  atomicity/idempotency contract is unchanged.

## Impact

- Adds the `world/art/` package (`subjects.py`, `adult.py`, `service.py`, `queue.py`, `store.py`,
  `worker.py`, `scheduler.py`, `presenter.py`) with package-local tests under `world/art/tests/`.
- Adds `commands/art.py` (`CmdArtStatus`/`CmdArtRun`/`CmdArtRetry`/`CmdArtRequeue`) registered in
  `commands/default_cmdsets.py`, with tests under `commands/tests/`.
- Adds `web/art_media.py` and an URL route in `web/urls.py` serving validated art-store identities
  same-origin, with tests under `web/tests/`.
- Modifies `world/quests/scene_builder.py` (portrait-policy seam + post-commit scheduling, unchanged
  atomicity), `world/ai/profiles.py` is **not** touched (the external worker is the art prompt-agent
  seam; no LLM profile is consumed by this change).
- Modifies `compose.yaml`, `Containerfile`, and `tests/test_container_contract.py` to mount art at
  `/app/server/.art` instead of `/app/world/art`.
- Modifies `server/conf/settings.py` (art store root, scheduler toggle/frequency, worker command),
  and `server/conf/at_server_startstop.py` (startup art synchronization).
- Adds media/URL configuration; no new Python dependencies and no network dependency in tests (the
  worker boundary is exercised with a fixed fixture command and the age gate blocks every character
  portrait job before any worker call).
- Preserves both repository contract tests green with no edits: `world/art/` is deterministic (no
  `world.ai`/`ollama`/`llm_client` fragment) and no `world/ai/` module writes art state.
