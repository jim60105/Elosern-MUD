## Why

Three production-utility duplications in the webclient presentation layer are drifting toward divergence:

- The four panel-push modules (`presentation/party_push.py`, `dialogue_push.py`,
  `lore_codex_push.py`, `art_push.py`) are ~50 lines × 4, line-identical except the panel
  key and the log-event strings (`party_push_watchers_failed` / `party_push_failed` and
  siblings). Any fix to the fan-out discipline (epoch guarding, per-session failure
  isolation, the registry-construction degrade path) must currently be applied four times
  and one of the four is always forgotten.
- The creation payload validators `_validate_background` and `_validate_affinity_elements`
  exist twice — `presentation/creation.py:427,459` and `actions/creation_actions.py:227,257`
  — and have **already diverged** (list vs tuple return, `ProtocolValidationError` vs
  `CreationActionError`). Bounds drift between the draft surface and the submit surface is a
  validation-bypass risk: the stricter copy can lag the looser one silently.
- The protocol field validators `_require_exit_ref` / `_require_node_id` are duplicated in
  `presentation/local_map.py:79-91` and `presentation/exploration.py:106-121`. Here
  `_require_node_id` has already diverged in the opposite direction (exploration wraps a
  `KnowledgeError` from `decode_node`; local_map lets it escape) — the divergence is
  observable and its tests pin it, so this change shares the mechanical validator without
  unifying the node-id semantics.

## What Changes

- New `web/webclient/presentation/push.py` with a `make_panel_pusher(panel_key, event_prefix)`
  factory; the four `*_push.py` modules become thin shells calling it. Every log-event id
  stays **byte-identical** (catalog in
  `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4); patch targets in
  existing tests (`patch.object(party_push, "log_warn")`, `patch("web.webclient.presentation.art_push.log_warn")`)
  keep resolving because the shells re-import the facade names.
- New `web/webclient/presentation/protocol_validation.py` hosting shared
  `validate_background(value, error_cls)`, `validate_affinity_elements(value, race,
  error_cls, normalize_empty)`, and the mechanical `_require_exit_ref` (byte-identical at
  both sites today). Each call site keeps its own raise type and return shape — the shared
  helper takes the error class and the empty-value normalization as parameters.
- `_require_node_id` is deliberately NOT unified: exploration keeps its `KnowledgeError`
  wrapping, local_map keeps letting `decode_node`'s error escape. The shared module hosts
  only the common shape check; the error-wrapping stays per-site (see design).
- No player-facing behavior, panel payload, protocol shape, or log event changes. No test
  file is renamed.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None. This is a behavior-preserving refactor; `.openspec.yaml` declares `skip_specs: true`.
The touched behaviors (party/dialogue/lore-codex/art panel push, creation draft validation,
local-map/exploration protocol validation) are already written in the shipped specs
`webclient-party-panel`, `webclient-dialogue-session`, `webclient-lore-codex-panel`,
`webclient-art-panel`, `webclient-character-creation-ui`, `webclient-local-map`, and
`webclient-exploration-menu`; their requirements stay exactly as shipped, and the existing
traceability annotations stay attached to the existing passing tests.

## Impact

`web/webclient/presentation/{party,dialogue,lore_codex,art}_push.py` (bodies → factory
shells), new `web/webclient/presentation/push.py` and
`web/webclient/presentation/protocol_validation.py`,
`web/webclient/presentation/{creation,local_map,exploration}.py` and
`web/webclient/actions/creation_actions.py` (validators delegate). Tests are untouched
except where a patch target names a moved private function (see tasks). Shard manifest
`.github/evennia-shards.json` unchanged (no module added/renamed under a shard label —
`web.webclient.tests` and the `web.webclient.presentation.tests.*` labels cover the new
helper modules' directories, and helpers are non-test modules like the existing
`presentation/watchers.py`).

## Batch

- depends-on: (none)
- Independent of `rules-wallet-rollback-helpers`, `art-path-confinement-and-ai-guardrails`,
  `rules-handler-dedup`, and `webclient-frontend-utils` (disjoint files; A/B/C waves run in
  parallel).
- Code-conflict notes: none with the three in-flight changes (`martial-arts-catalog`,
  `elementless-damage-effect`, `divine-mystery-catalog` touch skills/rulebook/rules-test
  files only — verified their proposals/tasks never name `web/webclient/**`).
  `webclient-frontend-utils` touches only `web/webclient-app/**` — disjoint from this
  change's `web/webclient/**` Python surface.

## Non-goals

- The `_in_exploration_mode` pair (`presentation/character.py:658` vs
  `presentation/affordances.py:188`) stays file-local: the audit flagged it as
  evaluate-only, and the two copies are not byte-identical semantics.
- `_db_safe` (`world/lore/sync.py:49` vs `world/quests/compile.py:863`) stays as-is: the
  `compile.py` comment records that the tuple-vs-list difference is deliberate.
