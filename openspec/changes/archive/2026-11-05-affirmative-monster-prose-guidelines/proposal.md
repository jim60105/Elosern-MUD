# Proposal

## Why

The content-expansion design (`docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §2, §8) requires every newly written or rewritten public monster passage to be affirmative, and requires `docs/lore/monster-creation-guidelines.md` to carry that rule and the separate high-tier approval scope of this batch. The guide still states that high-tier species are outside approved content, and its kit section enumerates which species own kits and claims six variants have none, which no longer matches the registry.

## What Changes

- Add an affirmative-public-prose rule to the guide: public description, appearance, ecology, variant direction and commission text state observable body, behaviour, ability scope, material needs and costs directly; technical exclusions stay in author-facing fields and design documents.
- Record the 2026-11-03 content-expansion approval scope beside the preserved 2026-10-05 first-batch approval: three low-tier species, one stronger high-tier crocodile variant and one high-tier species, each placed only by explicit declarations; calamity tier and new civilized peoples stay outside it.
- Replace the roster-enumerating kit paragraphs ("吞潮鱷、穗鳴雀、潮燈蟹各有…", "其餘六變體未宣告套組") with roster-free statements that each variant's kit is whatever its own registry row declares, so later content changes do not edit this guide to stay truthful.
- Note in "Documenting a species" that a public section may not cite command keys, buff identifiers or resource-field names.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`: this is documentation only. Affirmative phrasing is a human editorial judgement and is not a test-establishable mechanism; no test may police prose (design §2, §10).

## Impact

Only `docs/lore/monster-creation-guidelines.md`. Human-reviewed document: that guide itself, read by the user during review of this change. No code, registry, test, shard or generated artifact changes.

## Batch:

depends-on: none

Batch 1, parallel with `activity-group-formation` and `owned-kit-decision-coverage` (no shared file).

Code conflicts: none. The later content changes (`mudfilm-slime-species`, `wax-pouch-rat-species`, `sticky-palm-goblin-species`, `reservoir-warden-variant`, `ember-bristle-boar-species`) cite this rule and declare `depends-on: affirmative-monster-prose-guidelines` so their prose is written under it; none of them edits this guide.
