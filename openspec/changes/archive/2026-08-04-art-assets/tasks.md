## 1. Settings and package scaffolding

- [x] 1.1 Add art settings to `server/conf/settings.py`: `ART_STORE_ROOT` (default
      `os.path.join(GAME_DIR, "server", ".art")`), `ART_WORKER_CMD`, `ART_WORKER_TIMEOUT_SECONDS`,
      `ART_SCHEDULER_ENABLED`, `ART_SCHEDULER_INTERVAL_SECONDS`, `ART_SCHEDULER_LIMIT`; add a
      settings test that asserts the store root exists under `GAME_DIR` and the defaults are sane.
- [x] 1.2 Replace the placeholder `world/art/__init__.py` docstring with the package module set
      (`subjects.py`, `adult.py`, `queue.py`, `store.py`, `service.py`, `worker.py`, `scheduler.py`,
      `presenter.py`) and confirm `python -m compileall world/art` passes.

## 2. Subject model

- [x] 2.1 Implement `world/art/subjects.py`: `ArtSubjectKind`, frozen `ArtSubject(kind, key)`,
      `full()`, `parse_subject()`, `scene_subject_for(archetype)`,
      `monster_subject_for(archetype)`, `character_subject_for(entity)` (reads the explicit
      `portrait_policy`), and named `ArtSubjectError`; re-validate scene/monster archetypes against
      the immutable registries.
- [x] 2.2 Implement the deterministic adult-safe description provider in `world/art/subjects.py`
      (scene `scene_sentence`, bestiary archetype text, and a character template over
      `display_name`/race/subrace/adult age that excludes persona, combat resources, and disguised
      stats as physical truth).
- [x] 2.3 Write `world/art/tests/test_subjects.py` (pure `unittest.TestCase`) covering known/malformed
      key parsing, kind immutability, registry validation, explicit-vs-inferred portrait policy, and
      description determinism/content bounds.

## 3. Adult portrait gate

- [x] 3.1 Implement `world/art/adult.py::portrait_eligibility(entity)` reading canonical `age` and
      `apparent_age` attributes and raising named `PortraitRejected` with the failing field for
      missing/malformed/under-18 values.
- [x] 3.2 Write `world/art/tests/test_adult.py` (`EvenniaTest`) covering `age = 17`,
      `apparent_age = 17`, missing/malformed values, a valid adult passing, and a fixture-worker
      assertion that no rejected subject ever reaches the worker (using a counting fixture).

## 4. Asset records, queue, and serialization lock

- [x] 4.1 Implement `world/art/store.py`: `ArtAssetRecord(DefaultScript)` keyed
      `art:<full-subject-key>` with the full record contract (kind, subject key, source hash, status
      `missing`/`pending`/`in_progress`/`done`/`failed`, relative output identity, prior output
      identity, attempt count, last error code, enqueued/claimed/completed timestamps, aspect ratio)
      and no live object reference.
- [x] 4.2 Implement `world/art/queue.py`: `ensure(subject, description)` (idempotent for
      pending/in_progress/done, missing/failed → pending, hash-change staff-review signal),
      `requeue(subject)`, `claim(limit)` (pending → in_progress with lease, attempt++),
      `reclaim_expired_leases(timeout)`, `settle(...)`, `failed_keys()`, and the single process-wide
      `queue_lock` shared by scene and portrait operations; enforce atomic find-or-create and the
      duplicate-consolidation rule.
- [x] 4.3 Write `world/art/tests/test_queue.py` (`EvenniaTest`) covering idempotent ensure,
      failed→pending re-enqueue, requeue reset preserving prior output, hash-change behavior, the
      claim/lease/reclaim cycle, duplicate consolidation, and serialization of two concurrent drains
      that never hold the lock across a worker wait.

## 5. Worker boundary and store confinement

- [x] 5.1 Implement `world/art/worker.py`: pre-compute the exact expected relative output identity per
      claimed job, run `ART_WORKER_CMD` on a background Twisted thread (`deferToThread`) with JSON-lines
      stdin/stdout and a bounded timeout, enforce the one-to-one batch protocol (missing/duplicate/
      unparseable results fail the unfinished claimed jobs), and accept a result only when its key
      matches an input job, its status is `success`/`failed`, and its `output_identity` exactly equals
      the expected identity with an existing regular file under `ART_STORE_ROOT` (symlink-resolved); a
      rejected item records a bounded failure and retains the prior valid output.
- [x] 5.2 Add a deterministic fixture worker command under `world/art/tests/fixtures/` (writes the
      exact expected file for a matching job, or fails on a marker) and wire tests to it via
      `ART_WORKER_CMD` override.
- [x] 5.3 Write `world/art/tests/test_worker.py` covering a successful fixture run, mismatched-key
      rejection, status rejection, expected-identity mismatch, out-of-root/symlinked path rejection
      with prior-output retention, timeout producing a bounded failure, and a crash/truncated batch
      leaving no job stuck in `in_progress`.

## 6. Service, lifecycle seams, and startup wiring

- [x] 6.1 Implement `world/art/service.py`: `art_sync_all()` (idempotent scene + generic-monster
      subject records plus startup recovery of explicit named portrait policies with gate re-check),
      `schedule_portrait_ensure(entity)`, `ensure_scene_asset(archetype)`, and the
      `transaction.on_commit` scheduling helpers; all writes flow through `queue.py` under the lock.
- [x] 6.2 Wire `art_sync_all()` into `server/conf/at_server_startstop.py::at_server_start` (after the
      existing deterministic startup), deferring `world.art` imports like the other registration
      seams.
- [x] 6.3 Write `world/art/tests/test_service.py` (`EvenniaTest`) covering startup sync on a fresh DB,
      idempotence over existing pending/in_progress/done records, duplicate consolidation, recovery of
      a missing named-policy subject, ineligible-subject deterministic skipping, and that a failing art
      hook never rolls back the accompanying gameplay transaction.

## 7. Lifecycle hooks in creation, import, spawn, and room entry

- [x] 7.1 Persist `age`/`apparent_age` and establish the explicit named `portrait_policy` on validated
      imports in `world/imports/loader.py`, scheduling the on-commit ensure inside the all-or-nothing
      batch with an exception-safe wrapper; add tests under `world/imports/tests/` proving committed
      batches schedule exactly one job per eligible record, rejected batches emit none, and an art
      callback exception never surfaces as an import error.
- [x] 7.2 Establish the explicit named `portrait_policy` and schedule the on-commit ensure after
      successful player activation in `commands/character_creation.py`; add tests proving a committed
      creation schedules one job, a rolled-back creation emits none, and an art callback exception
      still reports creation success.
- [x] 7.3 Add the portrait-eligibility seam to `world/quests/scene_builder.py::_spawn_occupants`
      (post-commit schedule only for an occupant carrying an explicit named policy; generic occupants
      schedule nothing), with tests proving generic occupants produce no job, named-policy occupants
      schedule after commit, and a rolled-back materialization emits nothing.
- [x] 7.4 Add the room-entry `ensure_scene_asset()` hook to `GridRoom`/`InstanceRoom`
      `at_object_receive` in `typeclasses/rooms.py` (validated archetype only; `None`/unresolvable is a
      no-op); add tests proving entry ensures the record and an art failure never blocks the move.

## 8. Scheduler, presenter, and media URL

- [x] 8.1 Implement `world/art/scheduler.py::ArtDrainScript(DefaultScript)` honoring
      `ART_SCHEDULER_ENABLED`/`INTERVAL`/`LIMIT` and running drains through the claim-based background
      worker path, registered via settings script path; write tests covering the disabled scheduler
      leaving records pending, the enabled scheduler draining up to the limit, and lease-reclaim of a
      stale `in_progress` record.
- [x] 8.2 Implement the read-only `world/art/presenter.py` resolution primitives (status, same-origin
      URL from a validated stored identity, aspect, alternative text, and truthful placeholder
      kind/label; never `out_path`); write `EvenniaTest` tests covering done/missing/pending/failed/
      scheduler-disabled/missing-file states and the placeholder for gate-rejected subjects.
- [x] 8.3 Add `web/art_media.py` and a same-origin route in `web/urls.py` that serves a stored output
      identity through the same confinement check, 404ing for missing/out-of-root/absolute identities;
      write `web/tests/` view tests.

## 9. Staff commands

- [x] 9.1 Implement `commands/art.py::CmdArtStatus`/`CmdArtRun`/`CmdArtRetry`/`CmdArtRequeue`
      (`@art status [scene|portrait]`, `@art run [--limit N]`, `@art retry`, `@art requeue
      <full-subject-key>`) with staff locks, register them in `commands/default_cmdsets.py`, and keep
      status output free of persona text and absolute paths.
- [x] 9.2 Write `commands/tests/` coverage for staff vs non-staff access, bounded drain counts, failed
      re-enqueue, and valid/invalid requeue keys with no record change on invalid input.

## 10. Container mount correction

- [x] 10.1 Change the art volume in `compose.yaml` (`evennia-art:/app/server/.art`) and `Containerfile`
      (create `/app/server/.art` group-0-writable and declare it as the volume, removing the
      `/app/world/art` entries).
- [x] 10.2 Update `tests/test_container_contract.py` to assert the new mount and volume list, and run
      the container contract test.

## 11. Repository contracts and final verification

- [x] 11.1 Confirm the repository deterministic-path contract test stays green with no edits (no
      `world.ai`/`ollama`/`llm_client` fragment under `world/art/`, and no `world/ai` module writes art
      state), and run the offline end-to-end scenario: worker command fixed to fail + every LLM profile
      unavailable → movement, dialogue, combat, quests, and services proceed while every art state
      degrades to the approved placeholders.
- [x] 11.2 Plan requirement traceability: when the delta specs are synced into `openspec/specs/` at
      archive, annotate the substantive test for each new main-spec requirement with
      `covers_requirement` (canonical IDs from `tools.spec_traceability list`), then run
      `tools.spec_traceability check` to confirm every new requirement is covered.
- [x] 11.3 Run the affected package suites (`world.art`, `world.quests`, `world.imports`, `commands`,
      `server.conf`, `web`), the top-level regression/contract tests, `compileall`,
      `tools.spec_traceability check`, `openspec validate art-assets --strict`,
      `openspec validate --all --strict`, and `git diff --check`.
