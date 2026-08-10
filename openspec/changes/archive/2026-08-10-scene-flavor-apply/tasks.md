## 1. Deterministic scene-builder changes

- [x] 1.1 Add the pure `build_flavor_context(requirement, definition, room, origin_room)` helper
      in `world/quests/scene_builder.py` returning a plain bounded dict with exactly
      `scene_sentence` / `quest_context` / `room_name` / `region` (anchor placement display name
      when `anchor_near` is set, else empty), or `None` when the scene has neither a requirement
      sentence nor a resolvable archetype sentence. No `world.ai` / `ollama` / `llm_client`
      fragment may appear (deterministic-path ban).
- [x] 1.2 Add `apply_scene_flavor(room, text) -> bool` in `world/quests/scene_builder.py`: the sole
      writer of `room.db.scene_flavor`; verifies the room's database row authoritatively
      (`ObjectDB.objects.filter(pk=room.pk).exists()`) before writing; no-op (`False`) when the
      room is gone or already carries a flavor; catches database/object-deletion exceptions to
      `False`; never touches `room.db.desc`; never raises from flavor application.
- [x] 1.3 Extend `SceneMaterialization` with an optional `flavor_context: dict | None` field and
      populate it in `_materialize_instance` only for freshly spawned instance scenes.

## 2. Composition root and command wiring

- [x] 2.1 Add `server/scene_flavor_service.py` mirroring `ai_director_service.py`: an adapter that
      validates the plain dict (exactly the four keys, all string values) before wrapping it into
      the layer's context; function-local client build (live `OpenAICompatClient` when the
      `scene_builder` profile is enabled, the non-`None` offline stub otherwise, deferred
      `world.ai` imports); `schedule_scene_flavor(room, flavor_context)` firing
      `generate_scene_flavor(context, client)` as a fire-and-forget Deferred whose success path
      calls `apply_scene_flavor` and pushes to present `PlayerCharacter`s, and whose failure path
      logs a bounded diagnostic and resolves to nothing. Every synchronous step (dict validation,
      client construction, context wrapping, obtaining the Deferred) wrapped in `try/except` that
      logs and returns normally.
- [x] 2.2 Wire `commands/scene.py::CmdEnterScene`: after a successful materialization with a
      non-`None` flavor context **and a successful traversal into the scene**, register the
      scheduling through `transaction.on_commit(...)` so a nested outer rollback never fires a
      generation and the completion push reaches the player already inside the room (no blocking,
      no new user-facing output; rubber-duck timing fix).

## 3. Appearance rendering

- [x] 3.1 Extend `typeclasses/objects.py::ObjectParent.get_display_desc` (the shared appearance
      hook used by `return_appearance` for the text 看 command, the `at_look` seam, and the
      webclient `explore.look` path) to render `self.db.scene_flavor` as a paragraph after the
      room description and before the 「出口」 line when present; flavor-less rooms render
      byte-identical output. Adopt `ObjectParent` into `GridRoom`, `TerrainRoom`, and
      `InstanceRoom` (**before** the contrib base in each MRO — C3 would otherwise shadow the
      zh-tw hooks) so every room typeclass — including the flavor-bearing `InstanceRoom`, which is
      not a subclass of `Room` — renders the zh-tw frame and the flavor paragraph while
      `XYZRoom.return_appearance` and `WildernessRoom.get_display_desc`'s `ndb.active_desc` path
      survive through `super()` (design D4 correction).

## 4. Tests

- [x] 4.1 scene_builder tests: fresh instance scene yields the four-key context; bound stage and
      sentence-less scene yield `None`; `apply_scene_flavor` writes once, no-ops on re-application,
      never touches `desc`, never raises; a stale cached room reference with the row deleted (or a
      simulated lookup failure) returns `False` with no write and no error.
- [x] 4.2 Composition tests under `server/conf/tests/`: enabled profile schedules exactly one
      generation on commit (FakeLLMClient) and applies + pushes on success; a nested outer
      transaction that rolls back never fires a generation; disabled profile resolves to no flavor
      with no network request; synchronous failures (unregistered layer, malformed context dict,
      client-construction failure) log and return normally without raising to the caller; Deferred
      failure paths log and resolve to nothing.
- [x] 4.3 Appearance tests: flavor paragraph appears after the description on the text look
      command, the `at_look` seam, and `explore.look`; flavor-less rooms are byte-identical.
- [x] 4.4 Write the substantive behavior tests above first; add `covers_requirement` annotations
      for the new `scene-flavor` / `scene-builder` / `localized-appearance` requirements only after
      the change is archived and the canonical requirement IDs exist in the main specs (then run
      `uv run --locked python -m tools.spec_traceability check`).
- [x] 4.5 Run the focused Evennia package tests for `world/quests`, `commands`, and the
      appearance/explore-look paths.

## 5. Validation

- [x] 5.1 Run `openspec validate scene-flavor-apply --strict` and confirm all artifacts pass.
