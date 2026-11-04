# Proposal

## Why

`docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §3 and §7.3 add two one-shot manual boss sites: `reservoir_crocodile_boss_site` with one `reservoir_warden` (locally called 「閉灣者」) in a remote southeast tidal backwater, and `ember_bristle_boss_site` with one `warm_den_boar` (「赤背」) in remote western rocky woodland. Each boss has bounded territorial activity with immediate contact inside a defended area, either side may flee through a legal route and fight again, and defeat leaves the site cleared permanently. After the variant and species changes, neither boss is placed.

## What Changes

- Two `boss_site` declarations (one-shot, capacity 1, no site activity override, designated labels 閉灣者 and 赤背 through `individual_label_zh`) at planning-probe cells (design.md): `(2076, 381)` in `southeast_coast` beside inland water, and `(710, 530)` in `western_hills_valleys`.
- Two solitary compositions bound to territorial `solitary_roaming` activities over a territory rectangle with a `defended_area` aggression sub-area (bay; den/path).
- The existing `tide_mouth_boss_site` and every other declaration stay unchanged; no high-tier variant enters an ecology pool.
- Extend the content-expansion sites smoke with both bosses: labelled construction, one-shot clearing that survives reload, revisit, map read and quest acceptance, and a living escape that keeps identity and actual remaining resources before re-engagement.
- Review entry.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. `.openspec.yaml` declares `skip_specs: true`. One-shot sites, labels, territorial activity, hostile contact admission, mapped escape journeys and re-engagement are existing requirements (`monster-site-placement` including `site-member-activity-bindings`, `monster-field-activity`, `hostile-field-contact`, `monster-journeys`, `player-combat-session`).

## Impact

Files: `world/lore/monster_placement.py`, `world/lore/monster_activity.py`, `world/maps/tests/test_content_expansion_sites.py`, `docs/development/regional-monster-population.md`, regenerated `content/map-reference-context.json`.

No player-progress scaling, minimum-health lock, phase resurrection, exit-time reset, legendary equipment, rare-material harvest, currency or boss-reward system; no quest commission is authored (design §7.3). Human-reviewed document: the boss subsection of `docs/development/regional-monster-population.md` (remoteness and geography fidelity, territory and defended-area extents).

## Batch:

depends-on: reservoir-warden-variant
depends-on: ember-bristle-boar-species
depends-on: abandoned-transfer-station-encounter
depends-on: site-member-activity-bindings

Batch 7 (alone).

Code conflicts: appends to the same declaration tuples, review subsection and smoke module as `abandoned-transfer-station-encounter` (land after it). `content/map-reference-context.json` regenerated after rebase.
