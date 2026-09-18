## Context

`world/art/paths.py::resolved_under_root(root, identity)` is already the authoritative
confinement discipline (absolute/`..`/NUL refusal, strict-under-root after `resolve()`,
walk-and-refuse of any symlinked component). The private copies in `web/art_media.py:72-80`
and `world/art/worker.py:115-124` implement a weaker variant: they accept a pre-joined
`Path`, catch only `OSError` (an embedded NUL makes `resolve()` raise `ValueError`), and
permit an in-root symlink whose target is another in-root file. `gallery.py` already routes
through the strict shared function — the three-way split is drift, not design.

The five `world/ai/` layers register guardrail hooks with the same dance, pinned by tests
that patch the dicts directly (`guardrail._degrade_fallbacks`,
`guardrail._semantic_validators`) and assert identity-keyed rollback (`test_narrator.py:393-411`,
`test_npc_dialogue_registration.py:214-237`).

## Decisions

### D1 — Convergence onto the STRICT helper; one bounded failure-shape change, stated

`worker._write_temp`/delete and the `art_media` gallery branch pass their identity string to
`resolved_under_store_root(identity)` and delete the private helpers (module-local
`_store_root()` stays where the code still needs the raw root to join write targets).
Because the shared function is stricter, two pathological inputs change shape, both on
rejection paths only:

1. an identity with an embedded NUL previously raised an uncaught `ValueError` out of
   `resolve()`; now the call returns `None`, i.e. the worker's bounded `WorkerStoreError` /
   the media route's 404 — the same bounded-failure contract every other refusal uses;
2. an identity with an in-root symlink component was previously accepted by the weak copy;
   now refused — this is the security invariant the duplication endangered (a planted link
   inside the store can never masquerade as a confined file, exactly the case
   `test_gallery.py:149-165` pins for `gallery.py`).

No legitimate identity (queue-produced `gallery/<kind>/<key>/<id>.<ext>` or DB-record
stored identity) is affected: they are clean relative paths. The task list verifies no
existing test pins the old crash/accept shape before flipping.

`art_media.py:174`'s manual `target.is_symlink()` 404 check is deleted with the private
helper — the strict function refuses the same input (returns `None` → same 404).

### D2 — `GuardrailHooks.install()/uninstall_own()` keeps every patch seam in `guardrail.py`

```python
# world/ai/guardrail.py
@dataclass(frozen=True)
class GuardrailHooks:
    layer: LayerName            # existing _require_layer validation applies
    fallback: DegradeFallback
    validators: Mapping[str, SemanticValidator]

    def install(self) -> None: ...      # skip-if-identity, else register_*; on
                                       # GuardrailRegistrationError -> uninstall_own(); raise
    def uninstall_own(self) -> None: ...# delete only entries whose object IS this module's
```

`install()` encodes today's shared body verbatim: the fallback is installed only when
`_degrade_fallbacks.get(layer) is not self.fallback`; each validator only when the dict's
entry `is not` the module's own; any `GuardrailRegistrationError` triggers `uninstall_own()`
before re-raising (foreign hooks stay untouched — the identity comparisons are the
mechanism that keeps `test_startup_seam_survives_a_foreign_*_registration` green). Each
layer keeps its public `register_*` signature and its layer-specific preamble/postamble
(narrator's `callable(template_renderer)` check, `_is_registered()` no-op, and
`_template_renderer` assignment; schema-registration interleaving in
`npc_dialogue`/`scenario_director` stays in the layer function around the `install()`
call). `_uninstall_fallback`/`_uninstall_validator`/`_uninstall_all_own_hooks` are deleted
from all five modules.

### D3 — `world/ai/immutable.py::reject_mutable_containers` with import aliases

The two copies are semantically identical (`isinstance(value, (dict, list))` vs the
two-`or` spelling is textual only). One copy moves to `world/ai/immutable.py`; both modules
do `from world.ai.immutable import reject_mutable_containers as _reject_mutable_containers`
so any test that patches or imports the old private name through its module keeps
resolving. Same `TypeError` message bytes.

## Risks / Trade-offs

- The symlink-refusal widening could in principle break a deployment that hand-planted
  symlinks inside `ART_STORE_ROOT`; that usage violates the gallery sole-writer contract,
  and `test_gallery.py` already enforces the strict rule on the delete path today.
- `GuardrailHooks` hides the dict mutations from layer files; the literal event/rollback
  semantics are covered by the existing per-layer registration suites plus
  `world.ai.tests.test_guardrail`, run per task.
