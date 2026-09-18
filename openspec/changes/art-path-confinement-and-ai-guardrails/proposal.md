## Why

Two security-invariant duplications live outside the presentation zone:

- **Art store-root confinement is written three times.** `world/art/paths.py` already hosts
  the strict discipline (`resolved_under_root` / `resolved_under_store_root`: relative
  clean components, symlink-component refusal, strict-under-root resolve). Yet
  `web/art_media.py:68-80` and `world/art/worker.py:111-124` each carry their own weaker
  `_store_root` + `_resolved_under_root` (resolve-and-contain only). A confinement fix or
  bypass discovery today has to be applied to three divergent implementations — the exact
  shape of risk an escape check must not have.
- **AI guardrail registration boilerplate ×5.** `world/ai/{narrator,npc_dialogue,scene_flavor,character_creation,scenario_director}.py`
  each hand-roll `_uninstall_fallback` / `_uninstall_validator` / `_uninstall_all_own_hooks` /
  `register_*` with identity-based rollback, identical except the layer name. A rollback bug
  fixed in one layer silently persists in four. Additionally `_reject_mutable_containers`
  exists twice (`world/ai/action_options.py:134`, `world/ai/scenario_director.py:104`),
  semantically byte-identical.

## What Changes

- `web/art_media.py` and `world/art/worker.py` drop their private confinement copies and
  route every disk-touching path through `world.art.paths` (see design D2: the worker/media
  copies converge on the STRICTER shared check; legitimate identities are unaffected, the
  only widened refusal is a planted symlink component — the invariant the duplication
  endangered).
- `world/ai/guardrail.py` gains a `GuardrailHooks` registry helper
  (`GuardrailHooks(layer, fallback, validators)` with `install()` / `uninstall_own()`);
  the five layers keep their public `register_*` functions and data declarations only. The
  module-level `_degrade_fallbacks` / `_semantic_validators` dicts stay where tests patch
  them.
- New `world/ai/immutable.py::reject_mutable_containers(value, path)`; the two layer copies
  become imports (same `TypeError` message text).
- No player-facing behavior change; no new log event ids; no test file renamed; no shard-manifest edit.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None — `skip_specs: true`. The governed behaviors are already in `art-gallery-model`
(sole-writer / deletion-never-dangles requirements, whose confinement tests already exercise
`world.art.paths`), `art-queue-worker`, `art-output-format-pipeline`, and the AI guardrail
capabilities (`action-options-layer`, `ai-action-options-schema`, layer registration suites);
every requirement stays exactly as shipped and keeps its existing traceability annotations.

## Impact

`web/art_media.py`, `world/art/worker.py`, `world/ai/guardrail.py`,
`world/ai/{narrator,npc_dialogue,scene_flavor,character_creation,scenario_director}.py`,
`world/ai/action_options.py`; new `world/ai/immutable.py`. Shard labels are package-wide
(`world.art`, `world.ai` in shard `quests-skills-art-ai-lore`; `web.webclient.tests` /
`web.art` coverage unchanged) — new helper modules are non-test files, no manifest edit.

## Batch

- depends-on: (none)
- Independent of the other wave-A/B/C changes (disjoint files).
- No overlap with `martial-arts-catalog` / `elementless-damage-effect` /
  `divine-mystery-catalog` (skills/rulebook files only) or with the in-flight
  `elementless-damage-effect` reference to `world/ai/character_creation.py:423` — that
  change only *cites* the line as a consumer; it edits no `world/ai/` file.

## Non-goals

- `_db_safe` (`world/lore/sync.py:49` vs `world/quests/compile.py:863`): explicitly out of
  scope — the `compile.py` comment records the tuple-vs-list difference as deliberate, and
  its author declined the private-helper import on purpose.
- `server/conf/at_server_startstop.py`'s `_register_*_layer` seams keep their exact call
  signatures (tests `test_narrator.py:505+` / `test_npc_dialogue_registration.py:285+`
  drive them directly).
