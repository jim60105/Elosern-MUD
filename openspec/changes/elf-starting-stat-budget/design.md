# Design

## Context

`resolve_starting_profile` currently exposes raw bounds and one exact budget to activation, preset resolution and creation clients. Raw increments are also persisted in pending drafts.

## Goals / Non-Goals

Allow distinct custom elf builds with deterministic previews and identical validation across entry points. Leave authored stats and combat mechanics untouched. The previous single-strike estimate supports 200 as a starting cap, not a guarantee of equal encounter outcomes.

## Decisions

- Model per-axis point caps separately from stat bounds in the resolved allocation policy. Select the custom policy explicitly; the preset resolver keeps raw increments. Share the bounds-to-values calculation rather than copying it between modes.
- Author the custom elf cap in one configuration source. Derive the 75-point budget from the physical spans; each physical point remains one stat point. Magic consumes up to the full budget and interpolates from the lore floor to the creation cap. Round to nearest integer, ties upward, using integer arithmetic. Fixed gauges consume zero points.
- Publish the server's point caps and conversion inputs in the creation descriptor. Update its exact validators, preview, and confirmation checks together. Text creation reports the same contract. Keep the seven-key input shape.
- Distinguish pending drafts written under the two policies by version. Clear only superseded custom-elf allocations and return the draft to allocation, preserving identity, prose and portrait. Preserve unaffected drafts. Never activate stale values under the new policy.

## Risks / Trade-offs

The shipped lore ceiling remains 900, so authored characters may exceed the custom cap. Label the latter as a creation limit. A narrow comparison using existing combat rules can document the cap's expected impact without changing skills or claiming encounter parity.
