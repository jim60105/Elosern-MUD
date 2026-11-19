# Design

## Context

`resolve_starting_profile` currently exposes raw bounds and one exact budget to activation, preset resolution and creation clients. Raw increments are also persisted in pending drafts.

## Goals / Non-Goals

Allow distinct custom elf builds with deterministic previews and identical validation across entry points. Leave authored stats and combat mechanics untouched. The previous single-strike estimate supports 200 as a starting cap, not a guarantee of equal encounter outcomes.

## Decisions

- In `world/rules/character_creation.py`, resolve policy explicitly with a required `mode` keyword (`custom` or `preset`). Update every caller according to its purpose. Keep lore bounds and modifiers intact. In the same module define `ELF_CUSTOM_MAGIC_CREATION_CAP = 200`; derive the budget from the three resolved physical spans. Represent conversion by a point cap and value at cap for each axis. Share exact allocation validation and pre-modifier conversion across the rules consumers.
- Given a point cap `p`, minimum `lo`, value at cap `hi`, and valid points `n`, return `lo` for `p == 0`; otherwise compute `lo + (2 * (hi - lo) * n + p) // (2 * p)`. Apply existing subrace modifiers once after conversion in `_resolve_values`. For non-elf custom and preset axes, `p` is the lore span and `hi` the lore maximum. For custom elf magic, `p` is the budget and `hi` the configured cap; fixed gauges have `p == 0` and `hi == lo`. Physical axes use the raw-increment conversion.
- Publish `point_cap` and `value_at_cap` on every axis in creation panel schema 9. Keep `minimum` and `maximum` as lore bounds. Both exact validators require `0 <= point_cap`, `minimum <= value_at_cap <= maximum`, and `value_at_cap == minimum` if the cap is zero. Use exact integer arithmetic in the browser (BigInt intermediates, safe-integer results). Browser previews are pre-modifier values. Point fields and the allocation briefing use point caps, and text creation explains the same conversion.
- Keep `DRAFT_VERSION` unchanged. `save_custom_draft` stamps `allocation_policy_version: 1` only on accepted elf writes. `_normalize_draft` exposes otherwise valid stale elf drafts as `custom_needs_allocation` with `allocations: null`. Keep non-allocation fields and the separate portrait state; do not mutate storage on reads or invoke `reset_creation_draft`. Keep the marker off the wire. `_request_from_draft` rejects the incomplete stage before it can build a request, including direct activation without a panel read or with a matching fingerprint. A fresh valid save replaces the stale points and enables explicit confirmation.
- In `world/ai/character_creation.py`, replace `_race_bands` and `_allocation_budget` with the shared custom policy. Preserve the existing guardrail and transient proposal shape. Include resolver-derived caps and budgets for valid race/subrace pairs in `build_race_catalog()` within its bounded output, and use the selected profile in retry feedback. Keep WebClient transient fill and Telnet continuation draft-free until the existing deliberate save or activation.

## Risks / Trade-offs

The shipped lore ceiling remains 900, so authored characters may exceed the custom cap. The previous combat estimate is rationale only. Do not add a combat gate or change combat rules.

## Human review: allocation briefing

Review the Traditional Chinese briefings in WebClient and Telnet with an elf and a non-elf profile. Check that point units are distinguishable from stat values and that the magic cap is described as a creation limit. Automated checks cover the underlying data and behavior without matching localized wording.
