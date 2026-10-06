## Context

The external-art design gives every authored content kind a directory identity (`monster/<species-key>/`),
and `official-content-provenance` defined the typed official content reference with monsters as an
explicitly producer-less kind until this registry exists. `official-artwork-catalog` indexes the mounted
directory by `(kind, key)`; `official-art-resolution-contracts` inserted the official-default step into
the presentation chain, keyed by "the entity's content reference". What nobody owns yet is the monster
*producer* of that reference. `world/art/presenter.py`'s monster arm and `world/rules/art_view.py` still
classify monsters purely by `threat_tier` for the generic silhouette layer.

## Goals / Non-Goals

**Goals:** species key → `(monster, species_key)` official reference from provenance; the design's
"official images read-only, individual choice/geometry independent" invariant asserted; tier
substitution unrepresentable. **Non-Goals:** no image bytes or manifests (content of the official
package, out of repo), no new `ArtSubjectKind` (the reference layer is not the subject layer), no
personalization/gallery/presenter-chain edits, no portrait eligibility change, no generation behavior.

## Decisions

**D-A1 Producer lives beside the existing reference producers.** `official-content-provenance` already
centralizes reference derivation (preset provenance, `npc_profile_key`); the monster arm reads the
`Monster` typeclass's stored `species_key` there, so "references come only from provenance" stays one
auditable function, and the presenter/chain never special-case monsters again.

**D-A2 Species reference derives from species key only — never variant, never tier.** The external-art
layout is `monster/<species-key>/` (one shared identity per species, design §7), and variants are
behaviour/narrate differences, not image identities; per-variant directories would fork the approved
artwork budget and let tier or variant text leak into identity. An individual's visual distinctness
remains exactly what the design names: personal selection + geometry overrides (already owned by
`official-art-personalization`).

**D-A3 The tier subject layer stays untouched.** The built-in silhouette gallery (design §9 of the
external-art doc, shipped by `builtin-silhouette-stage-fallback`) is *generic-by-tier* on purpose.
Species identity joins only at the official-reference step, so silhouette fallback keeps working when
no official package exists, and the two layers cannot be confused — enforced by the `art-subject-model`
delta (species keys rejected from the subject vocabulary).

**D-A4 Absent-package behavior is pure fall-through.** The chain step already falls through on a
reference the snapshot lacks; this change adds no branch, only the producer, so honesty is structural:
there is no code left that could substitute another species' image. The design's "tier aliases cannot
satisfy the prerequisite" sentence becomes one rejection test.

## Risks / Trade-offs

- Depends on four landed artwork changes plus the registry; mitigated by the batch header — this is the
  wave's last landing, and the official-satisfied auto-gen suppression it inherits needs only a
  contract test, not an edit.
- If the official package ships tier-named directories, resolution simply never matches them (fall
  through) — a content-authoring error visible as "no official image", never as a wrong image.

## Open Issues

None; per-variant official art (if ever wanted) is a new external-art design decision, not a gap here.
