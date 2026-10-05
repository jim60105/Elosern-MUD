## Context

See proposal.md for motivation. The chain/payload vocabulary (`official-art-resolution` capability), the official catalog + fingerprinted serving (`official-artwork-catalog`), and the reference resolver (`official-content-provenance`) land first; this change adds the preference fields, selection-aware step 1, gallery projections, and adapters. Source design §7–§8. Existing precedents: `GalleryRecord` lock discipline (`art-gallery-model`), the seven ui_action adapters (`webclient-gallery-management-actions`), and personal-preference-not-card from the stage-transform design.

## Goals / Non-Goals

**Goals:**
- Preferences entity-local; official bytes never mutable; exactly one personal default governs.
- Update tolerance: identities outlive bytes; overrides degrade without deleting.

**Non-Goals:**
- No changes to card contract, monster cap, bindings, generation pipeline, or mounted directory semantics. No cross-character sharing of overrides. No new storage backend — preferences live on the existing `GalleryRecord`.

## Decisions

- **Preferences live on `GalleryRecord`, not a new model**: one lock, one sole writer, one record per subject already matches the subject-ownership boundary; a separate `OfficialPreferenceRecord` would double the writer surface for no isolation gain. Alternative rejected accordingly, extending the sole-writer requirement rather than bypassing it.
- **Selection participates in chain step 1 as "an explicit personal official selection replaces the gallery-default candidate"**, keeping equipment-bound cards ahead (design §7 step 1 wording). Implementing it inside `gallery_match` step 4's slot (default-card position) keeps steps 2–3 untouched and gives the mutual-clearing rule a natural home: each writer clears the counterpart field. This change's `art-gallery-resolution` delta MODIFIEDs the exact chain (step 4 selection-else-default; step 5 classic only when no selection resolved); the purity-exemption wording lives in the dependency change's `official-art-resolution` requirement, which already anticipates it.
- **Geometry overrides keyed by root-relative identity, not image_id or fingerprint**: the design's stable-identity rule — bytes update under the same identity, so overrides survive updates and only *invalidate* (retain + degrade) when dimensions make them illegal. Keying by fingerprint would silently orphan overrides on every content change.
- **Rejection code `official_read_only` at the adapter layer** with backend re-validation of every identity against the catalog + reference scope (the existing adapters' re-resolve-through-public-API pattern), rather than trusting the frontend's row kind.
- **Panel exposes official rows in a separate `official_entries` list** instead of synthesizing fake card rows: the card contract (twelve keys, source vocabulary `generated|seed`) stays byte-for-byte intact — design amendment 3 and the "not appended to cards" rule — and validators mirror one exact new list.

## Risks / Trade-offs

- [Preference fields grow the record's stored shape] → tolerant reads treat malformed preference state as absent; pre-release policy means no migration of old records (absent = unset).
- [Mutual clearing could surprise a player who wanted both defaults set] → intentional and spec'd: "changes the selected default unambiguous" is the design's requirement; UI copy states it.
- [Selection of an image outside the content reference] → adapter scope-checks identity prefix against the subject's reference before the writer is called.

## Migration Plan

None (pre-release): existing records simply lack the new fields, which read as unset. Rollback drops the fields; nothing else touched them.

## Open Questions

None.
