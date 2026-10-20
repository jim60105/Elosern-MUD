# Design: Fractional GM breakdown formatting

## Context

Handoff secondary observation records a `ValueError` in `breakdown_section()` at `web/gm/readers/characters.py:230`. The `pct` branch uses `f"{amount:+d}%"`. `StatLayer.amount` in `world/rules/status_query/models.py` accepts `int | float`; other branches already accept general numeric formatting. The failure is separable from the GM lineage section and ordinary member status commands.

## Goals / Non-Goals

Render valid authoritative numeric contributions without changing their meaning. This change does not round or truncate stored traits, recalculate effective totals, suppress section exceptions or alter lineage.

## Decisions

Use the existing presentation numeric convention if available; otherwise apply a local numeric formatter accepting finite integer/fractional inputs, preserving sign, fraction and the percent suffix. Integral values must retain their familiar signed integer representation. Do not multiply percentage values by 100, since the model already carries percentage points. Test +12.5 and -2.5 as independent known values, +10 and -10 controls, fractional flat and multiplier layers, and the model's unchanged base/effective values.

Test the real reader with authoritative read-model fixtures, then request the protected character-detail endpoint with a valid fractional percentage source. The breakdown section must be available with the expected layer source/name/kind and values, not an empty or unavailable substitute. Compare persisted state before/after the GET. Retain existing failure isolation for a genuinely invalid source and protection for unauthorized requests.

## Risks / Trade-offs

A broad shared formatting abstraction would expand scope. Reuse an existing helper if it already has the required semantics; otherwise keep the change at the reader. Do not impose an unapproved display precision that discards fractions.

## Verification and documentation

Extend existing GM reader/API tests, annotate the curated summary requirement, and register a new module only if required by existing test organization. Update the GM inspection guide to state percentage-point and fractional display semantics. Run focused tests and exact ownership contracts through the apply owner. No assembled acceptance task is marked complete by this secondary reader fix.
