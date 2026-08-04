## Context

Change 21 landed SceneBuilder (`world/quests/scene_builder.py`), the deterministic
requirements→prototype→spawn materializer, and every seam the approved art-portrait design
(`docs/superpowers/specs/2026-08-02-webclient-art-portrait-ui-design.md`) needs to integrate with now
exists: the shared `SceneArchetypeMixin` scene_archetype seam on `GridRoom`/`TerrainRoom`/`InstanceRoom`
(change 12/13/14), the adult age invariants (`age >= 18` and `apparent_age >= 18`) enforced by the
import schema (change 4) and by player-character creation (change `player-character-creation`), the
immutable `SCENE_ARCHETYPE_REGISTRY` and `MONSTER_TIER_REGISTRY`, and the real validated NPC spawn path.
What does not exist is the deterministic art-assets backend the roadmap labels change 22: **scene and
portrait subjects, the generated named-NPC portrait lifecycle, a serialized queue, the worker contract,
the adult portrait gate, the `@art` commands, the scheduler, and placeholders** — and change 23f's panel
can only consume completed asset records and statuses.

The focused design splits delivery so "the deterministic queue/worker/store can be verified without a
browser". The store root `server/.art/` is already gitignored; `compose.yaml` still mounts the old
bootstrap path `/app/world/art`, which would mask the importable `world/art/` package once it becomes
real code — this change fixes that mount as part of landing the package.

Constraints that shape every decision:

1. **Single-writer / deterministic-path boundary.** No module under `world/ai/` may import a state
   writer or live transport; no deterministic package may carry a `world.ai`/`ollama`/`llm_client`
   fragment (AST-scanned contract test). The approved design §5 grants `world/art/service.py` the sole
   write authority over asset/queue records and states plainly that "no presenter, browser plugin,
   worker, or `world/ai` module may write them" — so `world/art/` is a deterministic subsystem that
   owns its own presentation-asset records (the same shape as the `world/maps` / `world/quests`
   sibling owners the engine design's §3.1 amendment names), and its only writers are the deterministic
   lifecycle seams.
2. **The engine never calls SD and never blocks play.** The worker is an external command boundary
   (design §7). Queue/scheduler/`@art run` work asynchronously; a worker that is down, slow, or missing
   degrades presentation only.
3. **Art is presentation, never gameplay.** No gameplay state change may depend on image content,
   generation outcome, worker availability, or the scheduler. The offline acceptance criterion: with the
   worker command fixed to fail and every LLM profile unavailable, movement, dialogue, combat, quests,
   and services proceed while every art state degrades to the approved placeholders.
4. **No schema expansion of the generative blueprint.** Change 22 depends on 3, 4, 12, 14, 21 — not on
   change 20 (scenario-director). Extending `QuestBlueprint`/`StageSpawnRequirement` with a named-NPC
   portrait field would require that dependency, so the named-NPC policy seam is exposed on the
   deterministic spawn path (real, exercised, generic-today) and the blueprint-level extension stays an
   Open Question.

> **Design-document note (this change).** The engine design §8's `SceneArchetype` sketch carries an
> `image: path | None` field. The approved art-portrait design supersedes that surface: the asset
> record in the store owns the same-store relative output identity, and `SceneArchetype` stays an
> immutable registry entry. This change therefore does **not** add an `image` field to
> `SceneArchetype`; it reads the registry as-is and keeps output identity in `world/art/`.
>
> **Second design-document note (this change).** The roadmap row for change 22 and the focused design's
> enqueue-seam list both name "the generated named-NPC portrait lifecycle". Change 22 delivers the
> **validated portrait-policy seam on the deterministic spawn path** (post-commit ensure for a spawned
> occupant carrying an explicit named policy) plus the unique-portrait lifecycles for player-created
> and validated-import named characters — both reachable from real gameplay inputs. Making generated
> quests *themselves* spawn named NPCs with unique portraits is deferred: it requires an optional
> per-NPC portrait-policy field on `QuestBlueprint`/`StageSpawnRequirement`, which needs a
> scenario-director (change 20) dependency this change does not have. This scope split is recorded as
> a dated amendment in the focused design document so the source of truth and the roadmap agree.

## Goals / Non-Goals

**Goals:**

- Provide the complete deterministic `world/art/` backend as one verifiable delivery unit:
  - `subjects.py` — namespaced subject identity (`scene:<archetype>`,
    `portrait:character:<stable-key>`, `portrait:monster:<archetype>`), typed prefix/key storage, key
    validation before queue access, the explicit named-portrait-policy rule, and deterministic
    adult-safe subject descriptions.
  - `adult.py` — the immediate-before-enqueue adult gate: both `age >= 18` and `apparent_age >= 18`
    re-checked from canonical validated attributes, with named rejection and no queue record/prompt.
  - `service.py` — the sole asset/queue writer and the lifecycle seams: idempotent startup sync of
    scene + generic-monster subjects, startup recovery of explicit unique portrait policies,
    post-commit scheduling for player creation, validated character import, and named-NPC spawn, and
    room-entry `ensure_scene_asset()`.
  - `queue.py` / `store.py` — the asset-record contract (status, source hash, relative output identity,
    attempt count, last error, timestamps, aspect ratio), the idempotent subject-keyed queue, the
    shared scene+portrait serialization lock, and forced staff regeneration under the lock.
  - `worker.py` — the external worker contract (JSON jobs in, JSON results out), output-to-input
    validation, path confinement under the store root, and a bounded timeout.
  - `scheduler.py` — a settings-configurable, disableable periodic drain Script.
  - `presenter.py` — read-only resolution primitives (status, same-origin URL, aspect, alternative
    text, truthful placeholder kind/label) that 23f's panel will consume; never exposes `out_path`.
- Add the `@art status/run/retry/requeue` staff command family.
- Add `web/art_media.py` + a route that serves validated art-store identities same-origin without
  exposing the filesystem root.
- Wire the named-NPC portrait lifecycle into the real SceneBuilder spawn path (validated portrait-policy
  seam, post-commit, non-blocking), exercising the generic no-policy path today, and deliver the
  unique-portrait lifecycles for player-created and validated-import named characters.
- Fix the container art mount from `/app/world/art` to `/app/server/.art` in `compose.yaml`,
  `Containerfile`, and the container-contract test.
- Keep both repository contract tests green with no edits; run every new test offline with a fixture
  worker command.

**Non-Goals:**

- Any browser/panel work, OOB art push, zoom/full-view, or present-entity focus catalog — that is
  change 23f (`webclient-art-panel`), which depends on 23a's combat/exploration presenter contexts.
- Per-room scene images (D10 holds), unique portraits per generic monster instance, combat animation,
  item art, map tiles, or a gallery/history panel.
- Any client call to Stable Diffusion, and any live image service in tests.
- Player-triggered retry/regeneration; only staff may force it.
- Any gameplay state mutation based on image content or generation outcome.
- Any LLM call in the engine art path. The worker may use an agent or a fixture — that lives outside
  the engine and is not this change's code.
- Extending `QuestBlueprint`/`StageSpawnRequirement` for named NPCs so generated quests themselves
  spawn named NPCs with unique portraits (deferred; would require a change-20 dependency — see the
  second design-document note and the amendment to the focused design).
- Adding an `image` field to `SceneArchetype` (the store owns output identity).
- Backward-compatibility adapters or persisted-data migrations; the project is unreleased.

## Decisions

### D1. `world/art/` is the deterministic presentation-asset subsystem; `service.py` is its sole writer

`world/art/` is real package code (not the old one-line `__init__.py`). It is deterministic: it imports
only `evennia`, `django`, `world/lore`, `world/rules` (for nothing state-writing), `typeclasses`, and
stdlib — never `world.ai`/`ollama`/`llm_client`. Asset/queue records are presentation assets, not
canonical gameplay state (focused design §5), and `service.py` is the only module that writes them.
The other new modules — `subjects.py`, `adult.py`, `queue.py`, `store.py`, `worker.py`,
`scheduler.py`, `presenter.py` — are read-only with respect to records except through service-owned
helpers (queue operations take the lock and are reached from `service.py`/`commands`/`scheduler`).

**Concurrency model (explicit).** Evennia's Server is a single Twisted reactor process; every Django
ORM write — Script ticks, commands, deferreds, and `transaction.on_commit` callbacks — executes inside
that one process. The process-wide `threading.Lock` therefore serializes every art writer. Records are
created only through an atomic **find-or-create under the lock** (search by the namespaced key, create
only if absent, re-check), and startup sync consolidates any duplicate Scripts that a hypothetical
overlapping hot-reload could leave behind (keep the most-advanced record, delete the rest), so
per-subject uniqueness holds even outside the single-process assumption.

Alternatives considered: putting queue records in `world/rules/` (rejected — art is a separate,
browser-facing subsystem with its own lifecycle; the amended single-writer invariant is
"no `world/ai` module applies a state change", not "only `world/rules`"), treating art records as
ordinary game state written by `world/rules` (rejected — that would drag presentation bookkeeping into
the rules core and couple rules to `server/.art/` paths), and a new Django model with a unique index
(rejected — it would introduce the project's first custom model and migration into a codebase that
persists everything through Evennia typeclasses/Scripts; the find-or-create + consolidation rules give
the same per-subject guarantee with no migration surface).

### D2. Subject model: typed namespaced keys, validated before queue access, explicit portrait policy

`subjects.py` defines:

```python
class ArtSubjectKind(StrEnum):
    SCENE = "scene"
    CHARACTER = "portrait:character"
    MONSTER = "portrait:monster"

@dataclass(frozen=True)
class ArtSubject:
    kind: ArtSubjectKind
    key: str            # the un-prefixed subject key; never contains ":"
    def full(self) -> str: return f"{self.kind.value}:{self.key}"
```

`parse_subject(full_key)` splits on the known prefixes and rejects an unknown prefix, a `:`, or a
control character in the subject key, or an empty key. Scene subjects re-validate the archetype against
`SCENE_ARCHETYPE_REGISTRY`; monster subjects re-validate against `MONSTER_TIER_REGISTRY`. A subject
cannot change kind while keeping the same full key because the serialized identity is constructed from
the typed pair — a `portrait:character:x` and a `scene:x` are different `ArtSubject` objects and
different records. No queue access accepts a raw string; everything goes through a parsed `ArtSubject`.

**Portrait policy** is explicit metadata, never inferred. It lives on the character as a
`portrait_policy: dict | None` `AttributeProperty`:

- `None` → no portrait (today's generic role-based scene NPCs).
- `{"mode": "named", "stable_key": "<str>"}` → unique character portrait subject
  `portrait:character:<stable_key>`.
- `{"mode": "generic"}` → reserved; resolves to no unique portrait.

The policy is established only by the deterministic lifecycle that owns the character:

- **Player creation** (`commands/character_creation.py`, after `activate_player_character` succeeds):
  writes `{"mode": "named", "stable_key": str(character.pk)}` and schedules the ensure.
- **Validated import** (`world/imports/loader.py`, inside the all-or-nothing batch, after schema and
  age validation pass): writes `{"mode": "named", "stable_key": record["key"]}` and schedules the
  ensure. Imported records also gain persisted `age`/`apparent_age` attributes (additive; the loader
  does not store them today), which the gate reads.
- **SceneBuilder spawn**: the spawn path passes an optional policy marker; today's role-based occupants
  carry none → `None` → no portrait (D9).

Monsters never carry a policy: their subject is derived from the immutable bestiary archetype
(`threat_tier`) at presentation time, and startup sync ensures the records — no per-spawn enqueue, no
age derivation from a spawned instance (focused design §5).

Stable keys: the character database pk for players and the import record `key` for imported NPCs. Both
are deterministic, unique, and stable for the life of the database. (An explicit `portrait_key`
attribute is not needed; the policy's `stable_key` field *is* the explicit key.)

### D3. Adult portrait gate: canonical attributes, checked immediately before enqueue

`adult.py` provides `portrait_eligibility(entity) -> tuple[int, int]` that reads `age` and
`apparent_age` from the character's canonical attributes and raises a named `PortraitRejected`
(recording which field failed) when either value is missing, non-integer, or `< 18`. `service.py`
runs this gate for every `portrait:character` subject **at schedule time and again immediately before
any queue record is written** — the design's "in addition to import/creation validation". A rejection:

- produces no queue record and no prompt text (nothing is ever persisted or written to a worker);
- is deterministic: because the gate is a pure function of the canonical age attributes, every attempt
  on the same underage data rejects with the same named diagnostic — no separate persisted rejection
  marker is needed, and there is no retry storm because attempts occur only on lifecycle events, never
  periodically;
- is logged with the named diagnostic for staff; the browser will only ever see the unavailable
  placeholder (this change owns the placeholder primitive; 23f renders it);
- automatically unblocks if the canonical age data is later corrected (re-import or a staff update),
  at which point the next lifecycle attempt passes.

The permanent regression suite feeds `age = 17` and `apparent_age = 17` records into the player
creation, import, and (forged) spawn paths and asserts neither reaches the worker fixture. Scenes and
generic-monster subjects use immutable adult-safe registry descriptions and never pass through the
character gate. The staff `@art retry`/`@art requeue` paths for a `portrait:character` subject also
route through the gate: they resolve the living entity that owns the explicit policy for the stable
key and re-run `portrait_eligibility` before any record write, so a corrected-to-underage character
cannot be re-enqueued or force-regenerated (critique hardening).

### D4. Asset records and queue: Script-backed, subject-keyed, idempotent, one lock, claim-based drain

Asset records live in an Evennia `DefaultScript` subclass `ArtAssetRecord` (the same idempotent
Script-mirror pattern `world/lore/sync.py` uses for lore), keyed `art:<full-subject-key>`, carrying:

- `kind`, `subject_key` (typed `ArtSubject` fields persisted primitively),
- `source_hash` = `sha256(canonical_description)` at enqueue time,
- `status` ∈ `missing` / `pending` / `in_progress` / `done` / `failed`,
- `output_identity` (same-store relative path, e.g. `scene/forest_path.png`,
  `portrait/monster/gray_wolf.png`, `portrait/character/<stable_key>.png`) — never a worker-supplied
  URL and never an absolute path,
- `attempt_count`, `last_error_code`, `enqueued_at`, `claimed_at` (wall clock, the worker-lease
  timestamp), `completed_at` (world tick + wall clock),
- `aspect_ratio` (`16:9` scenes, `3:4` portraits),
- `prior_output_identity` — the last valid output retained across a failed forced regeneration,
- no live object reference.

`queue.py::ensure(service, subject, description)` is idempotent: an existing `pending`, `in_progress`,
or `done` record is left alone; `missing`/`failed` becomes `pending` (a failed record re-enqueues on
the next ensure, which is the retry path the design describes — `@art retry` forces the same
re-enqueue). A changed `source_hash` for a `done` record is recorded for staff review and does **not**
silently replace the completed image during ordinary play. `requeue(subject)` — staff-only — resets the
record to `pending` under the queue lock and preserves the prior output for rollback.

**Claim-based drain (the lock never covers the worker wait).** Drains work in three phases:

1. **Claim** (fast, under the lock): select up to `ART_SCHEDULER_LIMIT`/`--limit` `pending` records,
   atomically flip each to `in_progress`, set `claimed_at`, increment `attempt_count`, and release the
   lock. A concurrent `ensure` sees `in_progress` and leaves the record alone.
2. **Run** (no lock): the worker subprocess executes on a background Twisted thread
   (`deferToThread`), so neither the scheduler Script tick nor any gameplay command nor an
   `on_commit` callback ever blocks on a slow worker (D5's bounded timeout still applies).
3. **Settle** (fast, under the lock): apply each validated result — `done` with the exact expected
   identity, or `failed` with a bounded error — and release the lock.

A record stuck in `in_progress` past its lease (`claimed_at` older than the worker timeout plus a
margin) is reclaimed to `pending` by the next drain, startup recovery, or `@art run`, so a crash
mid-worker never loses or permanently blocks a job.

**Serialization and uniqueness:** scenes and portraits share exactly one queue lock (process-wide
`threading.Lock` in `world/art/`) and one worker concurrency slot. Combined with D1's atomic
find-or-create and the startup duplicate-consolidation rule, a subject has exactly one record, and
overlapping schedules, concurrent staff commands, or a hot-reload overlap cannot corrupt it.

**Single in-flight worker guard (critique hardening).** Exactly one external worker subprocess may be
in flight at a time: a drain first acquires a `_worker_in_flight` slot under the queue lock and a
second drain attempted while a worker is running claims nothing and returns 0. The slot is released
in a `finally` after the batch settles, so a crash never wedges the queue.

**Stale-settle guard (critique hardening).** `settle()` applies only to a record that is still
`in_progress`. A worker whose job was later requeued (reset to `pending`) or lease-reclaimed is a
no-op, so an older worker result can never overwrite a newer forced regeneration (lost update is
impossible).

### D5. Worker contract and store confinement

The engine's only job is to hand validated jobs to an external command and validate the results
(engine design §11 / focused §7):

```
ART_WORKER_CMD = [sys.executable, "-m", "tools.art_worker"]   # settings-overridable
```

- `worker.py::drain(batch)` claims the batch (D4), runs the worker subprocess on a background
  Twisted thread via `deferToThread` with a bounded timeout, and settles the results. Neither the
  scheduler Script tick, `@art run`, nor any gameplay/`on_commit` path blocks on a slow worker — the
  claim is synchronous and fast, the run is background, and the settle is fast.
- A job is `{"kind", "key", "description", "out_path", "aspect_ratio"}`. The engine **pre-computes
  the exact expected relative identity** for each job from the subject kind and key (e.g.
  `scene/forest_path.png`, `portrait/monster/gray_wolf.png`, `portrait/character/<stable_key>.png`)
  and writes that identity as `out_path`; `description` is the canonical subject description (D6).
- A result is `{"key", "status", "output_identity", "error"}`. A result is **accepted only when** its
  key corresponds to an input job, its status is `success`/`failed`, and its `output_identity`
  **exactly equals** the pre-computed expected identity for that job (not merely "inside the root"),
  with an existing regular file under the store root (symlink-resolved). Anything else is rejected.
- The batch protocol is **one-to-one**: every input job must reach exactly one terminal result.
  Missing, duplicated, or unparseable results (truncated/non-JSON output, a valid JSON value that is
  not an object, worker crash) mark the unfinished claimed jobs `failed` with a bounded protocol
  error so a job can never be stuck in `in_progress` or silently double-completed. The settle loop is
  wrapped so an unexpected settle error also fails every unfinished subject.
- A rejected or timed-out item records a bounded failure and the record's prior valid output (if any)
  is retained (focused §10 "retain prior valid asset record").
- Store layout is enforced by the confinement check: `scene/`, `portrait/monster/`,
  `portrait/character/` subdirectories under the root.

The worker may call local Stable Diffusion, use a prompt-writing agent, or write a fixture file — that
choice is entirely outside the engine and outside this change's code (the design's swap point). The
shipped default worker (`tools/art_worker.py`, referenced by `ART_WORKER_CMD`) is a deterministic
offline placeholder that writes a fixed 1x1 PNG for each job, so the engine is verifiable and fully
offline out of the box; deployments override `ART_WORKER_CMD` for a real image service. In tests,
`ART_WORKER_CMD` points at a small fixture script that either writes a real file or fails
deterministically; no network is ever opened.

### D6. Deterministic adult-safe subject descriptions

The registry/provider produces one deterministic natural-language description from allowed immutable
or validated data; this is the description the store hashes and the worker sees:

- **Scene:** the archetype's one-sentence `scene_sentence` (immutable registry).
- **Generic monster:** the bestiary archetype's description + `display_name_zh` + example names
  (immutable registry; adult-safe by construction).
- **Character:** a template from `display_name`, race/subrace, and adult age (e.g. "A
  <race-subrace> adult named <display_name> in the approved visual style.") — never persona text,
  never secret state, never mutable combat resources, never `disguised_stats` presented as physical
  truth (focused §3.3). Where stable validated appearance fields exist on the character, they may be
  included; appearance that is absent is omitted, never invented by the engine.

The description is deterministic so the hash is stable across reloads and the "changed description"
staff review signal is meaningful.

### D7. Lifecycle seams and queue-failure isolation

`service.py` owns every enqueue seam:

1. **Startup sync** (`server/conf/at_server_startstop.py::at_server_start`): `art_sync_all()` ensures
   a record for every `SCENE_ARCHETYPE_REGISTRY` entry and every `MONSTER_TIER_REGISTRY` entry
   (generic monster subjects). Idempotent: existing `pending`/`done` records are untouched.
2. **Startup recovery**: `art_sync_all()` also scans living characters with an explicit `named`
   portrait policy and ensures each subject — this recovers an enqueue that failed after an earlier
   gameplay commit (focused §5). The adult gate re-runs; a subject that is permanently ineligible is
   skipped with a diagnostic.
3. **Player creation** — `commands/character_creation.py` registers
   `transaction.on_commit(lambda: art_schedule_portrait_ensure(character))` after activation commits;
   creation failure or rollback never emits a job.
4. **Validated import** — `world/imports/loader.py` registers the same on-commit schedule inside the
   all-or-nothing batch; a rolled-back import emits nothing.
5. **Named-NPC spawn** — `world/quests/scene_builder.py` registers the on-commit schedule for a
   spawned occupant carrying an explicit named policy (D9). Today's role-based occupants carry none.
6. **Room entry** — `typeclasses/rooms.py` `at_object_receive` on `GridRoom`/`InstanceRoom` calls
   `ensure_scene_asset(archetype)` for a validated `scene_archetype`, covering dynamic registry content
   added after startup. Wilderness `TerrainRoom` has no arrival hook (change 13's documented decision)
   and its archetypes are covered by startup sync.

Every seam is failure-isolated: an art failure logs a bounded diagnostic and never rolls back
creation, import, spawn, or movement (focused §5). `transaction.on_commit` guarantees the schedule
fires only after the owning transaction actually commits. The on-commit callbacks themselves are
**exception-safe wrappers**: Django runs them synchronously on the committing thread after commit, so
any exception they raise would otherwise surface to the creation/import workflow after the data is
already committed — each callback therefore catches art errors, logs a bounded diagnostic, and never
propagates, so a committed creation/import is always reported as success.

### D8. Scheduler, `@art` commands, and media URLs

- **Scheduler** (`world/art/scheduler.py` + `typeclasses/scripts.py::ArtDrainScript`): a persistent
  `DefaultScript` that drains `ART_SCHEDULER_LIMIT` pending jobs every
  `ART_SCHEDULER_INTERVAL_SECONDS`; disabled entirely when `ART_SCHEDULER_ENABLED = False`
  (records stay `missing`/`pending`, placeholders remain, gameplay proceeds). Not a world-clock event
  source: art is wall-clock, independent of the player-driven clock's settlement order.
- **`@art` commands** (`commands/art.py`, staff-locked): `@art status [scene|portrait]` lists/filters
  records (status, subject, aspect, attempt count, bounded error codes — never persona text, never
  absolute paths); `@art run [--limit N]` drains now asynchronously and reports the number enqueued;
  `@art retry` re-enqueues `failed` records; `@art requeue <full-subject-key>` parses and validates
  the full key, then resets it under the queue lock. Players have no access.
- **Media URL** (`web/art_media.py` + `web/urls.py` route `/art/<path:identity>`): serves only an
  identity referenced by a `done` asset record — never an arbitrary path under the store root — after
  applying the same confinement/`realpath` check D5 uses; rejects `..`, **symlinks (even one that
  stays inside the root)**, unexpected directories or extensions (the identity must match
  `scene/<key>.png`, `portrait/monster/<key>.png`, or `portrait/character/<key>.png`), and
  out-of-root or missing identities with 404. The presenter builds URLs only from validated stored
  identities and never surfaces `out_path` or the store root.

### D9. Named-NPC portrait lifecycle is wired into the real spawn path

The SceneBuilder spawn path (`world/quests/scene_builder.py::_spawn_occupants`) gains the
portrait-eligibility seam: after occupants are spawned and registered (inside the same outer atomic
materialization), any occupant carrying an explicit named portrait policy schedules
`transaction.on_commit(...)` → `service.schedule_portrait_ensure(occupant)`. The schedule is
post-commit (design §5: "after the spawn transaction commits"), so an art failure can never roll back
a materialized scene, and a rolled-back materialization emits no job (its on-commit callback never
runs).

Today every scene occupant is a role-based generic NPC or monster with **no** policy, so the hook is
exercised on the generic path and resolves to no-portrait — this is a real, validated spawn-path
integration, not a forward-declared fake. Adding an optional named-NPC policy to the generative
blueprint is deliberately out of scope (it needs a change-20 dependency).

### D10. The store root and container mount are corrected in the same change

`ART_STORE_ROOT` is `GAME_DIR/server/.art` (already gitignored). `compose.yaml` changes
`evennia-art:/app/world/art` → `evennia-art:/app/server/.art`; `Containerfile` replaces the
`/app/world/art` `install -d`/`VOLUME` entries with `/app/server/.art` (keeping non-root, group-0
writable semantics); `tests/test_container_contract.py` asserts the new mount. This lands with the
package so a mount can never shadow the importable `world/art/` module.

## Risks / Trade-offs

- [An art job that hangs blocks the scheduler/`@art run`] → D4/D5: the worker subprocess runs on a
  background Twisted thread with a bounded timeout; the queue lock is held only for fast DB
  transactions (claim/settle), never across the worker wait, so a stuck worker delays nothing in
  gameplay and an expired lease reclaims the job.
- [`world/art/` imports would violate the deterministic-path contract test] → D1: the package carries
  no `world.ai`/`ollama`/`llm_client` fragment; the contract test scans it and stays green, locked by
  a test.
- [The adult gate could be bypassed through a forged spawn or policy write] → D2/D3: the gate reads
  canonical attributes and runs again immediately before any enqueue; a missing/underage value
  produces a named rejection with no record, and permanent underage regressions cover both fields on
  every lifecycle path.
- [Startup sync on a large bestiary/archetype set could be slow] → D4: sync is idempotent Script
  upsert of a bounded registry; the registries are small and this mirrors the existing `sync_all()`.
- [Import records gain new persisted `age`/`apparent_age` attributes] → D2/D9 Migration Plan: additive
  and harmless; existing NPCs simply have `None` age until re-imported and therefore fail the gate
  with a named diagnostic rather than enqueueing — safe default for the unreleased project.
- [A worker output could point outside the store root or to another subject's file] → D5: a
  successful result must exactly equal the pre-computed expected identity for that job with an
  existing regular file (symlink-resolved); the media view serves only `done`-record identities and
  repeats the same check before serving.
- [A worker crash could leave a job stuck or silently double-complete] → D4/D5: the batch protocol is
  one-to-one (missing/duplicate/unparseable results fail the unfinished claimed jobs), and an
  `in_progress` lease older than the timeout is reclaimed by the next drain/recovery.
- [Changed source-description hash silently replaces a done image] → D4: a changed hash is recorded
  for staff review and never auto-replaces a completed asset during ordinary play.
- [The queue could grow unbounded on persistent worker failure] → D4/D8: records stay `failed` and
  re-enqueue only on ensure/retry; staff `@art status` surfaces the bounded error for action.
- [The named-policy spawn branch has no real gameplay input today] → Second design note: the seam is
  validated and test-exercised on the real spawn path, and generated *named* NPCs are explicitly
  deferred; player-created and imported named characters exercise the named path in real gameplay.
- [Role-based scene NPCs never get unique portraits] → D9/Non-Goals: intentional — D15 reserves unique
  portraits for players and explicitly named NPCs; generic NPCs/monsters use an archetype or none.
- [The `/art/<identity>` media route could serve arbitrary files] → D5/D8: the view serves only
  identities referenced by `done` records, rejects `..`/symlinks/unexpected extensions, and 404s for
  missing or out-of-root identities.
- [A committed creation/import could surface an art error after commit] → D7: on-commit callbacks are
  exception-safe wrappers that never propagate art failures to the owning workflow.
- [OOB art push is absent] → Non-Goals: it belongs to 23f (depends on 23a's OOB foundation); this
  change delivers the records/statuses/URLs 23f consumes.

## Migration Plan

1. Add `server/conf/settings.py` art settings: `ART_STORE_ROOT`, `ART_WORKER_CMD`, `ART_WORKER_TIMEOUT_SECONDS`,
   `ART_SCHEDULER_ENABLED`, `ART_SCHEDULER_INTERVAL_SECONDS`, `ART_SCHEDULER_LIMIT`.
2. Build `world/art/` package (`subjects.py`, `adult.py`, `queue.py`, `store.py`, `service.py`,
   `worker.py`, `scheduler.py`, `presenter.py`), each with package-local tests under
   `world/art/tests/` using `EvenniaTest` for record/DB surfaces and a fixture worker command.
   Include the claim status + lease-reclaim path, the one-to-one batch protocol, and the
   find-or-create + duplicate-consolidation rules in the queue tests.
3. Persist `age`/`apparent_age` on import (`world/imports/loader.py`), establish the explicit
   `portrait_policy` on player creation and validated import, and register the on-commit schedules.
4. Add the SceneBuilder spawn-path portrait seam (D9) and the room-entry `ensure_scene_asset()` hooks.
5. Add `commands/art.py` (+ cmdsets registration), `web/art_media.py` + URL, startup
   `art_sync_all()` (+ recovery) in `at_server_startstop.py`.
6. Change the container art mount in `compose.yaml`/`Containerfile` and update
   `tests/test_container_contract.py`.
7. Verify: `world.art` suite; `world.quests`/`world.imports`/`commands`/`server.conf` affected suites;
   the repository-wide contract tests (deterministic-path + container); the full Evennia suite;
   `compileall`; `tools.spec_traceability check`; `openspec validate art-assets --strict` and
   `openspec validate --all --strict`; `git diff --check`.

No persisted-game-data migration applies: the new attributes (`portrait_policy`, imported `age`/
`apparent_age`) are additive with `None` defaults, and art records are presentation Scripts with no
player-facing gameplay meaning. Rollback is a clean removal of the new package, commands, route,
settings, the SceneBuilder/loader/creation hooks, and the mount change.

## Open Questions

- Whether the generative `QuestBlueprint`/`StageSpawnRequirement` should later carry an optional
  named-NPC portrait policy so generated quests can spawn uniquely-named NPCs with unique portraits.
  This change deliberately defers it (it would need a change-20 dependency) and records the scope split
  as a dated amendment in the focused design document; the spawn-path seam it delivers is real and
  validated, exercised today by the generic no-policy path.
- The exact stable-key scheme for a future explicit `portrait_key` (beyond pk/import-record key) if
  characters are ever renamed or imported under changing keys; today the policy's `stable_key` is set
  once at the owning lifecycle and is stable by construction.
