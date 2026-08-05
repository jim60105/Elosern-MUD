## 1. Frozen art view, shared roster query, and portrait resolution helper

- [x] 1.1 Add a shared frozen roster query `combat_participants(actor)` to `world/rules/combat_view.py`
      (ordered participant identities from persisted `player_ids` then `enemy_ids`, no portrait data)
      that `build_combat_view` and `build_art_view` both consume; implement `world/rules/art_view.py`:
      frozen `ArtSceneView`/`ArtEntityView` and `build_art_view(actor)` that (a) read the actor's
      current location's validated `scene_archetype` via `SceneArchetypeMixin` (unresolvable → `None`),
      (b) select combat participants from `combat_participants` or exploration present entities from
      the room's `contents` filtered to dialogue hosts (`world.rules.dialogue`) and explicit
      named-policy characters in deterministic room-contents order, capped at `MAX_PORTRAIT_CATALOG =
      32`, and (c) classify each entity's portrait subject decision (named character / generic monster
      / none) with bounded display name and stable role label. Never writes state, never reads
      `disguised_stats` or persona.
- [x] 1.2 Implement the single `portrait_catalog_key(identity) -> str` mapper in
      `world/rules/art_view.py` (one bounded decimal-string form) and use it both to key the art
      catalog and (in task 3.1) to fill combat `portrait_ref`; assert the conversion in server/Node
      parity fixtures.
- [x] 1.3 Add `world/art/presenter.py::resolve_entity(entity)` that dispatches by kind: a generic
      monster (`threat_tier` resolving in `MONSTER_TIER_REGISTRY`) resolves
      `portrait:monster:<threat_tier>` through `monster_subject_for` + `resolve_subject` with no adult
      gate; a character resolves through `resolve_character` (explicit named policy + `age >= 18` and
      `apparent_age >= 18`); anything else yields the unavailable placeholder. No rejected subject ever
      returns a prompt, subject key, or URL.
- [x] 1.4 Write `world/rules/tests/test_art_view.py` (pure `unittest.TestCase`) covering combat vs
      exploration entity selection, shared-roster ordering, dialogue-host/named-policy filtering,
      non-present and policy-less exclusion, catalog cap with deterministic truncation, and scene
      archetype `None`/invalid handling; and `world/art/tests/test_presenter.py` additions covering
      `resolve_entity` for named character, `age = 17`, `apparent_age = 17`, missing and malformed age
      values, generic monster, and unknown `threat_tier`, each with a counting fixture worker assertion
      that no rejected subject reaches a worker.

## 2. Art panel presenter, exact validator, and registry registration

- [x] 2.1 Implement `web/webclient/presentation/art.py`: exact schema-version-1 validator and
      `art_presenter(context)` composing `world.rules.art_view.build_art_view` with
      `world.art.presenter.resolve_scene` / `resolve_entity`. The scene payload carries archetype,
      `display_name_zh` label, subject key, status, same-origin URL, aspect, alternative text, and
      nullable placeholder; catalog entries carry subject key (nullable), status, URL/placeholder,
      aspect, alt, and `context` (name + role). Output is validated against the exact bounded schema
      before return; outside `exploration`/`combat` raise `PanelUnavailableError`. Never expose
      `out_path`, store root, or rejected prompt content.
- [x] 2.2 Register the `art` panel (schema version 1, stable unavailable reason
      `("art_unavailable", "場景圖像目前無法顯示")`) in `web/webclient/presentation/registry.py` alongside
      the existing panels.
- [x] 2.3 Write `web/webclient/presentation/tests/test_art_panel.py` (`EvenniaTest`) covering
      done/missing/pending/failed/scheduler-disabled/missing-file scene states, same-origin URL only,
      combat catalog mirroring `context_actions` participants, exploration present-entity catalog
      contents, gate-rejected entries as unavailable placeholders with no URL, creation-mode
      unavailable form, presenter isolation, and a worst-case/all-ceilings serialization size test.

## 3. Context actions schema version 2 with populated portrait_ref

- [x] 3.1 Populate `portrait_ref` in `world/rules/combat_view.py` via the shared `portrait_catalog_key`
      mapper and the shared roster query (catalog key when the participant is in the art catalog —
      including placeholder entries — else `None`); keep the `CombatViewError` contract and
      participant order unchanged.
- [x] 3.2 Advance `web/webclient/presentation/combat_panel.py` to `context_actions` schema version 2:
      accept and emit a nullable `portrait_ref` equal to the art catalog key, dropping the version-1
      "must be null" branch; update the participant validator and presenter.
- [x] 3.3 Extend combat-action completion so an admitted combat action publishes `status`,
      `context_actions`, **and** `art` replacements at one newer revision (the affected-panel set the
      dispatcher sends), so a defeated/fled/settled participant leaves the portrait catalog in the
      same `ui_update`.
- [x] 3.4 Update `web/static/webclient/js/elosern/protocol.js` to the version-2 `context_actions`
      validator (nullable string catalog key, bounded), and update every version-1 combat fixture in
      `web/webclient/presentation/tests/`, `web/static/webclient/js/tests/`, and the browser fixtures
      to version 2; keep the dual-direction parity test green.

## 4. Decoupled completion notification and targeted OOB art push

- [x] 4.1 Change `world/art/worker.py` so `_run_and_settle_batch` returns the subjects whose
      `settle()` actually applied a terminal `done`/`failed` status (settle already returns `None` for
      a stale no-op), and `drain()` emits a project-local Django signal `asset_completed` (payload:
      completed full subject key only) from the `deferToThread` **success callback** (reactor thread),
      never from the settle path itself; `drain_synchronous()` emits on its calling thread for
      deterministic tests. No `web/` or `world.ai` import anywhere under `world/art/`.
- [x] 4.2 Implement `web/webclient/presentation/art_push.py`: subscribe to `asset_completed` with a
      stable `dispatch_uid`, iterate connected WebClient sessions with an attached coordinator and
      active puppet under per-session exception isolation, re-render the `art` panel from canonical
      state, and publish `coordinator.panel_update(context, {"art": payload})` only when the rendered
      scene subject key or any catalog entry subject key equals the completed key; creation-mode and
      non-referencing sessions receive nothing, and no exception propagates back to `world/art/`.
- [x] 4.3 Wire the subscription from `server/conf/at_server_startstop.py::at_server_start` using the
      deferred-import seam pattern (re-entrant safe via `dispatch_uid`), and add `EvenniaTest` coverage
      in `web/webclient/presentation/tests/test_art_push.py`: targeted push to a referencing session,
      no push to a non-referencing/creation-mode session, late completion for an old room replacing
      nothing, reconnect resolving from the store, signal payload containing only the subject key, the
      subscriber never running on the worker thread, one bad session not stopping the others, and the
      push never interleaving between a completion presentation and its action result.

## 5. Client art model, renderer, and client-local focus

- [x] 5.1 Implement `web/static/webclient/js/elosern/art_panel.js` (DOM-independent): exact payload
      validation mirroring the server validator, scene reduction (asset/placeholder/
      pending-with-prior dimmed retention), catalog model keyed by opaque catalog IDs, client-local
      `focusKey` state with the snapshot-adoption rule (keep on survival; else exploration none /
      combat first valid participant), and open/close full-view state for scene and portrait.
- [x] 5.2 Replace the placeholder `art` component registration in
      `web/static/webclient/js/plugins/goldenlayout.js` with the art renderer: 16:9 cover-style scene,
      label and alternative text outside the bitmap, dimmed `目前場景圖片生成中` retention, 3:4 portrait
      card at bottom right with name + role context and its own full-view control, click/Enter open /
      Escape close, truthful placeholders, text-node insertion (no trusted HTML), and reduced-motion
      compliance.
- [x] 5.3 Add a tiny client-local focus subscription (in-memory, no packet) published by the combat
      dock's highlighted participant today and consumed by the art renderer; update
      `web/static/webclient/js/plugins/combat_dock.js` to publish the current focus key; keep
      `web/static/webclient/js/elosern/keyboard_router.js` focus semantics unchanged.

## 6. Node tests

- [x] 6.1 Add `web/static/webclient/js/tests/art_panel.test.js` covering payload validation
      acceptance/rejection, scene placeholder and pending-with-prior states, catalog reduction, focus
      adoption/survival rules, no-focus means no card, full-view open/close, and the parity fixtures.
- [x] 6.2 Update `web/static/webclient/js/tests/protocol.test.js` and `combat_menu.test.js` for the
      `art` panel allowlist entry and the `context_actions` version-2 validator, and run
      `node --test web/static/webclient/js/tests/*.test.js`.

## 7. Evennia integration coverage

- [x] 7.1 Add `EvenniaTest` coverage under `web/webclient/presentation/tests/` and `commands/tests/`
      (as needed) proving: full snapshot includes the `art` panel in exploration and combat modes and
      the unavailable form in creation mode; text-command and adapter refresh paths include the `art`
      panel; a combat result that removes a participant (defeat/flee/terminal settlement) publishes
      `status`, `context_actions`, and `art` at one newer revision with the participant's catalog
      entry gone; presenter isolation; and no presenter, adapter, or push path mutates traits,
      resources, combat session, art records, map knowledge, or world time.
- [x] 7.2 Run the affected suites: `web.webclient`, `world.art`, `world.rules`, and the repository
      contract tests (`uv run --locked -m unittest discover -s tests -t .`), confirming the
      deterministic-path contract stays green with no edits to it.

## 8. Managed Playwright acceptance

- [x] 8.1 Add `web/tests/browser/test_browser_art.py` covering: scene done (same-origin URL rendered),
      pending-with-prior dimmed retention and label, missing/failed/offline/missing-file placeholders,
      keyboard-only full view open/close with focus restore, portrait overlay with name + role context,
      client-local catalog focus switching with no packet sent, no-focus no-card, a defeated/fled
      participant leaving the catalog in the same combat update, late old-subject completion not
      replacing the panel, adult-gate payload exclusion (`age = 17`, `apparent_age = 17`, missing, and
      malformed all rejected with no rejected content in the browser), and 16:9/3:4 usability at
      1440x900 and 1280x720.
- [x] 8.2 Run the managed browser suite for the art file (reusing a still-running managed server where
      isolation permits) and confirm `uv run --locked python -m unittest discover -s web/tests/browser -t .`
      remains green with deterministic fixtures and no remote/LLM/image requests.

## 9. Repository contracts, traceability, and final verification

- [x] 9.1 Confirm the offline acceptance scenario: with `ART_WORKER_CMD` fixed to fail and every LLM
      profile unavailable, movement, dialogue, combat, quests, and services proceed while every art
      state degrades to the approved placeholders.
- [x] 9.2 Annotate the substantive test for each new or modified main-spec requirement (canonical IDs
      from `tools.spec_traceability list`) with `covers_requirement`, then run
      `tools.spec_traceability check`.
- [x] 9.3 Run `openspec validate webclient-art-panel --strict`, `openspec validate --all --strict`,
      `python -m compileall -q world typeclasses commands server`, and `git diff --check`, and confirm
      no new runtime dependency, database migration, `world.ai` fragment, or backward-compatibility
      layer was introduced.
