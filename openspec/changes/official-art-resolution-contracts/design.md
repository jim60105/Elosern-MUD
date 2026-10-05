## Context

See proposal.md for motivation. The catalog (`official-artwork-catalog`) supplies snapshot lookup + fingerprinted serving; the reference resolver (`official-content-provenance`) supplies entity→content-reference binding. This change weaves them into the deterministic chain and versioned payloads. Source design §6–§7 and §11's offline rules.

## Goals / Non-Goals

**Goals:**
- One chain, one vocabulary: official / runtime / silhouette remain distinguishable everywhere a portrait payload travels.
- Zero new mutation or I/O in presentation; eligibility ordering preserved.

**Non-Goals:**
- Personal official selections, geometry overrides, and gallery read-only rows (owned by `official-art-personalization`). Silhouette payload semantics and the stage mask (owned by `builtin-silhouette-stage-fallback`; its step-8 slot in the chain already exists as the fallback seam).

## Decisions

- **Official default slot after the classic asset, before the fallback seam** (step 6 of 8): keeps every existing runtime branch byte-for-byte ahead of official, satisfying "runtime images outrank official defaults" without touching steps 1–5, and the monster variant falls through the slot because it has no producer (structural, not conditional). The alternative — official ahead of cards — was rejected: it would let a server-side artwork swap silently replace a player's chosen default.
- **Origin discriminator as a new payload field with a closed vocabulary** (`official` | `runtime` | …silhouette value added by the silhouette change) rather than inferring from URL prefixes: the design forbids URL-shape inference and both wire validator sides mirror exact schemas anyway; adding one bounded enum field is the smallest versioned contract.
- **Auto-generation suppression lives in the autogen guard, not the chain**: the observable side ("official-satisfied subject presents official art without a card") is already forced by the chain; only the request-site guard is new, so one module (`service.py`'s guard) changes instead of every lifecycle path.
- **Stale official reference fall-through with no preference deletion** is chain behavior; the preference side (retaining the personal selection) belongs to personalization, so the chain simply treats "reference resolves to nothing" as a pass.
- **Presentation uses the startup snapshot exclusively** (catalog contract), so the chain's purity clause extends naturally: stored state + startup snapshot.

## Risks / Trade-offs

- [Versioned portrait vocabularies change in three surfaces at once (art catalog, roster rows, payload)] → they ship together in this one change with the dual-side validators updated atomically; the contract gate is the verification.
- [Suppressing auto-generation when official satisfies hides generated-art absence from operators expecting cards] → `official_art_*` catalog diagnostics and the autogen guard test make the suppression explicit; staff generation paths are untouched.

## Migration Plan

Payload fields are additive; deploy with the catalog empty and every new branch is inert. Rollback reverts the change; no stored state to unwind (nothing new is persisted).

## Open Questions

None.
