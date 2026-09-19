"""Deterministic defeat aftermath (defeat-aftermath-core).

Runs inside ``settle_session``'s ``transaction.atomic()`` for every
hostile-mode ``outcome == "defeat"`` settlement, on the deterministic-core
side of the single-writer boundary (parent design §4.1). The writer floors
the defeated player at the nonlethal HP floor, marks the knockout, departs
the living violators (population despawn; quest-bound monsters retained with
precedence), mounts the weak debuff, and records the defeat EventLog kinds.
The violation-sequence hook point is guarded by ``DEFEAT_ADULT_SCENES`` and
its body is the defeat-aftermath-violation-sequence engine registered at the
package bottom (DA4 D-V6); with the flag off the hook is never called and the
core-only behavior is the entire settlement.

Rollback contract (design D-C5): the database rows restore through the
transaction, but Evennia's idmapper cache is not transaction-aware, so every
in-process surface the writer touches (actor trait/buff attributes, the
transient battlefield knockout set, the departed monsters' marker and
bookkeeping) is snapshotted at entry and restored by the idempotent
``undo`` closure on every exception boundary — the writer's own, the
settlement's commit/exit failure, and a later outer round-transaction
rollback (armed via :func:`register_pending_undo` because Django has no
rollback hook).

Departure contract (design D-C3, two-phase): the logical departure (marker
clear + bookkeeping drop) commits inside the settlement transaction; the
physical deletion is scheduled through ``transaction.on_commit`` so it runs
only after the outermost durable commit — a rolled-back round discards it.
A post-commit delete failure reverts the logical departure deterministically;
only a process crash in the post-commit window leaves a marker-less live
monster (the parent design's accepted restart-refresh risk).

The split:

- :mod:`world.rules.defeat_aftermath.contracts` — result/outcome records,
  rulebook section value types, hook-context shapes.
- :mod:`world.rules.defeat_aftermath.rulebook` — the section-validator
  registry, the loader, the import-time ``DEFEAT_AFTERMATH_RULEBOOK``.
- :mod:`world.rules.defeat_aftermath.validation_core` /
  ``validation_violation`` / ``validation_digest`` — the per-section
  validators.
- :mod:`world.rules.defeat_aftermath.violation` — the hook registry, the
  attempt mechanics, and ``run_violation_sequence``.
- :mod:`world.rules.defeat_aftermath.digest` — the digest phase.
- :mod:`world.rules.defeat_aftermath.aftermath` — the writer, departure,
  undo, recovery helpers.

Everything the historical ``world.rules.defeat_aftermath`` module exposed
is re-exported here.
"""

from world.rules.defeat_aftermath.aftermath import (
    _depart_violators,
    _living_foes,
    _recovery_scope,
    _restore_aftermath_surfaces,
    _schedule_boundary_event,
    drain_pending_undos,
    finalize_departure,
    register_pending_undo,
    run_defeat_aftermath,
    solve_recovery_seconds,
)
from world.rules.defeat_aftermath.contracts import (
    DefeatAftermathResult,
    DefeatAftermathRulebook,
    DigestConfig,
    DigestOutcome,
    DigestRow,
    RecoveryConfig,
    ViolationConfig,
    ViolationDeltas,
    ViolationHookContext,
    ViolationOutcome,
    ArchetypeViolationRow,
    WakeObservation,
)
from world.rules.defeat_aftermath.digest import (
    _digest_bystanders,
    _digest_row_matches,
    _digest_snapshot,
    _match_digest_row,
    _max_sensitivity_label,
    _rewrite_companion_wake,
    _run_digest_phase,
    _schedule_digest_boundary,
)
from world.rules.defeat_aftermath.rulebook import (
    DEFEAT_AFTERMATH_RULEBOOK,
    _DEFEAT_AFTERMATH_PATH,
    _OWNED_SECTIONS,
    _SECTION_VALIDATORS,
    _register_section_validator,
    load_defeat_aftermath_sections,
)
from world.rules.defeat_aftermath.validation_core import (
    _validate_pg_lines,
    _validate_recovery,
    _validate_weak_debuff,
)
from world.rules.defeat_aftermath.validation_digest import (
    _DIGEST_CLIMAX_CEILING,
    _DIGEST_CONDITION_KEYS,
    _DIGEST_OUTCOMES,
    _DIGEST_ROW_KEYS,
    _validate_digest,
    _validate_digest_labels,
    _validate_digest_range,
)
from world.rules.defeat_aftermath.validation_violation import (
    _DIRECTION_BOUND_COUNTERS,
    _VIOLATION_DELTA_KEYS,
    _VIOLATION_ROW_KEYS,
    _require_non_negative_int,
    _validate_violation,
    _validate_violation_deltas,
)
from world.rules.defeat_aftermath.violation import (
    _advance_attempt_clock,
    _apply_violation_deltas,
    _call_violation_hook,
    _companion_wake_entry,
    _credit_violation_counters,
    _derived_resist_roll,
    _schedule_violation_boundary,
    _select_violation_victim,
    _snapshot_sexual_surfaces,
    _victim_climax_onset,
    _violation_act_entry,
    _violation_attempt_entry,
    _violation_pool,
    _violation_resisted_entry,
    _violation_scope,
    register_violation_hook,
    run_violation_sequence,
)

# The DA4 violation sequence is the shipped body of the core's guarded hook:
# registration happens at import, so the wiring needs no startup step and is
# exercised by every defeat settlement, while the single-registration guard
# still fails loudly on any second adult body. ``DEFEAT_ADULT_SCENES`` stays
# the only switch — with it off the hook is never called and this
# registration is structurally invisible (DA4 D-V6).
register_violation_hook(run_violation_sequence)


def __getattr__(name: str):
    """Delegate the mutable hook-registry read to its owning module.

    ``_VIOLATION_HOOK`` lives in :mod:`world.rules.defeat_aftermath.violation`
    and is rebound by ``register_violation_hook``; a plain re-export would
    freeze the pre-registration ``None``, so the historical
    ``world.rules.defeat_aftermath._VIOLATION_HOOK`` read resolves live here.
    """
    if name == "_VIOLATION_HOOK":
        from world.rules.defeat_aftermath import violation as _violation_module

        return _violation_module._VIOLATION_HOOK
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
