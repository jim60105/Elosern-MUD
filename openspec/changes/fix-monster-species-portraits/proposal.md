# Proposal

## Why

A wilderness goblin can first display a retired humanoid silhouette and later inherit a low-tier gallery portrait. Monster art currently shares threat-tier subjects ahead of species artwork, so fixing the renderer alone would preserve cross-species image leakage.

## What Changes

- **BREAKING** Replace every threat-tier monster art subject with a registered species visual identity. Retire low, mid, high and calamity art production, gallery rows, selection, prompts and media application. Keep threat tiers and combat balance unchanged.
- Preserve monster runtime generation, seeded cards, selection, placement and mounted official artwork, scoped to the monster's declared visual species. No image means `monster_anon`.
- Give baseline wilderness population declarations explicit visual keys, including `goblin`, without requiring new combat species profiles or inferring identity from translated names.
- Separate reusable species cards from entity-local personal image selections and geometry. No same-tier or cross-species preference may resolve.
- Amend the approved engine design D15 and conflicting main requirements. Replace obsolete tier tests, with the required cutover and traceability registration.

## Capabilities

### New Capabilities

- `monster-visual-identity`: authored art-only identity for baseline wilderness populations, kept separate from complete combat-species construction.

### Modified Capabilities

- `art-subject-model`: species visual membership and physical descriptions replace tier art membership and descriptions.
- `species-portrait-identity`: all monster image sources use the same declared visual species, with silhouette on unresolved identity or absent images.
- `official-content-provenance`: accepts validated baseline visual provenance alongside combat-species provenance.
- `art-asset-lifecycle`: startup monster art synchronization covers visual species and respects real official defaults.
- `art-gallery-autogen`: species-aware automatic monster generation and suppression.
- `art-gallery-resolution`: species-only cards, classic identities and official defaults; no tier precedence.
- `art-gallery-fallback`: every unresolved or imageless monster uses `monster_anon` without tier overrides.
- `official-art-personalization`: individual monster selections and geometry remain entity-local.
- `art-gallery-seed-sync`: monster seed membership is registry-validated visual species.
- `art-staff-commands`: species-scoped requeue and retry, no retired tier revival.
- `wilderness-monster-population`: baseline population carries explicit visual provenance while its mechanics remain unchanged.
- `webclient-gallery-panel`: species rail, bounded ordering and explicit personal-preference capabilities.
- `webclient-gallery-management-actions`: species admission and refusal of personal writes without an entity context.
- `webclient-gallery-ui`: preserves generation and shared-card selection while hiding unsupported personal writes.
- `art-gallery-model`: separates species cards from entity-local monster preferences.
- `art-queue-worker`: rejects unregistered monster output identities at queue and media boundaries.
- `art-portrait-cutout`: species portrait examples replace retired tier examples without changing image processing.
- `art-gallery-generation`: monster generation requires a registered visual species.
- `art-gallery-prompt-fields`: provenance follows the selected visual species.
- `webclient-art-panel`: monster catalog entries resolve visual species with authoritative monster fallback.

## Impact

Affected owners include `world/art/{subjects,service,gallery,gallery_match,gallery_fallback,official_refs,gallery_seed,presenter,queue,worker}.py`, monster visual lore declarations, baseline wilderness producers, monster identity attributes, gallery presenters/actions/selection and art media admission. Character and scene workflows retain their contracts. Implementation updates the approved engine design, deployment/seed documentation and relevant tests; this proposal edits planning artifacts only.

## Non-goals

No new combat species, skill kit, population density, numerical balance, RNG, GPU integration, compatibility aliases or data migrations. Existing unreleased tier artifacts are never interpreted as species artwork. No destructive cleanup of unrelated local images or game saves.

## Batch:

```text
depends-on: none
code-conflicts: fix-combat-portrait-publication (webclient-art-panel integration tests only; apply identity cutover first)
```

`fix-combat-portrait-publication` completes the first-combat delivery and retired SVG removal. Both changes are required for the reported acceptance; neither is advertised as the complete fix alone. Each is limited to one engineer-day. The three active resource-skill changes edit combat species data but require no dependency on art; avoid rewriting their authored profiles. Exploration UI changes share browser journey helpers and potentially AppClient integration with the publication change; serialize those files if touched.
