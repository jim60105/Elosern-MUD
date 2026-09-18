## Context

Three presentation-layer duplications need extraction shapes that preserve today's
observable behavior and today's test-patch seams. Existing tests patch the *pusher
module's* collaborators (`test_party_panel.py` patches
`web.webclient.presentation.party_push.watchers_for`,
`.build_production_registry`, `.log_warn`; `test_art_push.py` patches
`web.webclient.presentation.art_push.log_warn`), and AGENTS.md forbids patching
`world.observability.*` — assertions patch the caller module's binding.

## Decisions

### D1 — Pusher factory resolves collaborators through the shell module's globals

`push.py::make_panel_pusher(panel_key, event_prefix, deps)` returns a closure; `deps` is a
zero-arg callable supplied by each `*_push.py` shell that reads the *shell module's* global
names at call time:

```python
# party_push.py
from world.observability import log_warn
from web.webclient.presentation.coordinator import publish_panel_update
from web.webclient.presentation.ingress import build_presentation_context
from web.webclient.presentation.registry import build_production_registry
from web.webclient.presentation.watchers import watchers_for
from web.webclient.presentation.push import make_panel_pusher

def _deps():
    return PanelPushDeps(
        watchers_for=watchers_for,
        build_registry=build_production_registry,
        build_context=build_presentation_context,
        publish=publish_panel_update,
        log_warn=log_warn,
    )

push_party_update = make_panel_pusher("party", "party", _deps)
```

Because `_deps` dereferences module globals per call, `patch.object(party_push,
"watchers_for", ...)` and `patch.object(party_push, "log_warn")` keep working unchanged —
the identity-based patch seam survives the move. Event ids are built as
`f"{event_prefix}_push_watchers_failed"` / `f"{event_prefix}_push_failed"` — the prefixes
were chosen so the produced strings are byte-identical to the catalog strings
(`party_push_watchers_failed`, `dialogue_push_failed`, ...). A unit test in
`web/webclient/tests/test_panel_push_factory.py` (new file; covered by the
`web.webclient.tests` shard label) pins the six concrete strings the three trio prefixes
produce (party/dialogue/lore_codex × `{prefix}_push_watchers_failed` / `{prefix}_push_failed`)
literally, so a prefix typo can never silently mint a new event id.

`art_push.py` stays as-is: its fan-out iterates `SESSION_HANDLER.get_sessions()` with a
coordinator gate and subject-key filtering — structurally different, not a quadruplet member.

### D2 — Creation validators: injected error class + per-site normalization, no tightening

`protocol_validation.py` hosts the mechanism; each site's deviation stays a parameter:

- `validate_background(value, error_cls, max_length=MAX_PERSONA_FIELD_LENGTH)` — identical
  at both sites today; becomes the single copy.
- `validate_affinity_elements(value, race_key, error_cls, *, empty_as_none, global_bound=None)`
  — the presentation copy normalizes `None`→`[]`, returns a list, and enforces the
  `MAX_AFFINITY_ELEMENTS` global bound; the actions copy normalizes `None`→`None`, returns a
  tuple, and enforces **no** global bound. Parameterizing the bound (rather than always
  applying it) is deliberate: silently applying the presentation-side global bound to the
  submit surface would *tighten* accepted payloads — a behavior change. Message texts are
  already identical between the copies and stay byte-identical.

### D3 — `_require_node_id` is NOT unified

Only the shape check (`isinstance str`, `len <= MAX_NODE_ID_CHARS`) moves to
`protocol_validation.py::require_node_id_shape`. The `decode_node` hop stays per-site
because the observable failure differs: exploration converts `KnowledgeError` into
`ProtocolValidationError(... ) from error`; local_map lets `KnowledgeError` escape. That
difference is pinned by existing panel tests. `require_exit_ref(value, field, error_cls)`
moves wholesale — the two copies are byte-identical.

## Risks / Trade-offs

- A factory indirection can obscure grep-discoverability of the event strings; the literal
  id-pinning test in D1 closes that.
- Deps-provider closures add ~8 lines per shell; still a ~120-line net reduction with one
  fan-out copy.
