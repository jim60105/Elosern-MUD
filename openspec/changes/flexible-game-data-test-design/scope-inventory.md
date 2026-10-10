# Implemented scope inventory

## Baseline and method

Baseline master: `234dc1c4e57ab40a9e56703698df91327c10c49e`. Live CLI root: `/var/home/jim60105/repos/MUD`; schema: `spec-driven`. The inventory reads all 311 current `openspec/specs/*/spec.md` files (2,074 requirement headings), all 94 classified content-test sources and the 14 existing debt paths, and statically screens all 1,244 versioned Python/JS/TS test sources. All 311 capabilities have existing literal requirement-ID associations in those sources. This is a static inventory, not a claim that tests ran or every assertion was independently reviewed.

Historical archive files are evidence, not edit destinations. Every existing active change is excluded. Baseline file hashes are captured in `baseline-scope.json` to distinguish this proposal's edits from concurrent work without rewriting either.

## Disposition keys

- **DELTA**: explicit current requirement revisions; other requirements in the capability stay intact.
- **TEST-ONLY**: current contract already permits independent fixtures/authored data; migrate relevant assertions without revising it.
- **RETAIN**: existing mechanism, identity, schema, security, protocol, presentation, vocabulary, topology or intentional quality contract, not an identified mutable-value approval mirror. Exact synthetic outcomes and stable safety limits stay valid. Linked tests remain unless their mutable assertions fall in a concrete family below.

This is not a ban on numbers. Intentional invariants include integer copper conversion, age 0..10000, canonical affinity floors/natural cap, pleasure 0..100, vocabulary ordinal relationships, hit-index/count shapes, irreversible flags, counter increments, no baked multipliers, independent racial power gaps, existing monster authoring bounds and comparative sexual quality. Named roster size is not a balance magnitude.

## All current capabilities

| Capability (path below `openspec/specs/`) | Requirements | Disposition | Associated test-source count |
| --- | ---: | --- | ---: |
| `action-options-layer` | 7 | RETAIN | 2 |
| `action-options-trigger-hooks` | 5 | RETAIN | 5 |
| `action-options-trigger-service` | 12 | RETAIN | 9 |
| `action-resolution-pipeline` | 18 | TEST-ONLY | 22 |
| `affinity-cap-break` | 2 | DELTA | 3 |
| `affinity-friendly-fire` | 5 | TEST-ONLY | 2 |
| `affinity-system` | 6 | DELTA | 9 |
| `ai-action-options-prompts` | 4 | RETAIN | 3 |
| `ai-action-options-schema` | 7 | RETAIN | 1 |
| `altoria-crown-and-watch` | 3 | RETAIN | 2 |
| `altoria-hospitality` | 3 | RETAIN | 2 |
| `altoria-learning-and-exchange` | 3 | RETAIN | 2 |
| `altoria-sanctum` | 4 | RETAIN | 1 |
| `anchor-placement` | 4 | RETAIN | 2 |
| `art-asset-lifecycle` | 11 | RETAIN | 11 |
| `art-gallery-autogen` | 3 | RETAIN | 7 |
| `art-gallery-fallback` | 4 | RETAIN | 3 |
| `art-gallery-generation` | 4 | RETAIN | 6 |
| `art-gallery-kind-capabilities` | 4 | RETAIN | 4 |
| `art-gallery-model` | 16 | RETAIN | 6 |
| `art-gallery-prompt-fields` | 4 | RETAIN | 5 |
| `art-gallery-resolution` | 6 | RETAIN | 2 |
| `art-gallery-seed-sync` | 4 | RETAIN | 3 |
| `art-output-format-pipeline` | 3 | RETAIN | 1 |
| `art-portrait-cutout` | 6 | RETAIN | 5 |
| `art-prompt-translation` | 11 | RETAIN | 5 |
| `art-queue-worker` | 9 | RETAIN | 13 |
| `art-sd-server-integration` | 3 | RETAIN | 2 |
| `art-service-connectivity-surface` | 2 | RETAIN | 1 |
| `art-stable-key-contract` | 2 | RETAIN | 7 |
| `art-staff-commands` | 7 | RETAIN | 1 |
| `art-subject-model` | 5 | RETAIN | 9 |
| `authored-registry-references` | 3 | RETAIN | 2 |
| `battlefield-action-context` | 5 | RETAIN | 1 |
| `battlefield-commit-surface` | 4 | RETAIN | 4 |
| `blueprint-portrait-policy` | 5 | RETAIN | 8 |
| `buff-handler-integration` | 14 | DELTA | 9 |
| `canonical-wilderness-destination` | 1 | RETAIN | 1 |
| `cast-settlement-atomicity` | 2 | TEST-ONLY | 3 |
| `character-breakdown-view` | 3 | RETAIN | 3 |
| `character-creation-ux` | 5 | RETAIN | 3 |
| `church-ordination` | 24 | DELTA | 16 |
| `ciaran-village-commerce` | 4 | RETAIN | 1 |
| `ciaran-village-commons` | 2 | RETAIN | 2 |
| `ciaran-village-crafts` | 2 | RETAIN | 1 |
| `cleanse-effect-handler` | 3 | RETAIN | 2 |
| `climax-settlement` | 6 | TEST-ONLY | 2 |
| `combat-modifier-table` | 17 | DELTA | 13 |
| `combat-resolution` | 12 | TEST-ONLY | 12 |
| `combat-target-traits` | 1 | RETAIN | 1 |
| `combat-upkeep-settlement` | 4 | RETAIN | 1 |
| `commerce-assortments` | 5 | RETAIN | 3 |
| `companion-possession-core` | 5 | RETAIN | 4 |
| `companion-possession-transition` | 5 | RETAIN | 1 |
| `concept-transient-fill` | 4 | RETAIN | 6 |
| `connection-screen` | 2 | RETAIN | 2 |
| `container-image` | 6 | RETAIN | 2 |
| `contrib-matrix-verification` | 2 | RETAIN | 1 |
| `correspondence-delivery` | 2 | RETAIN | 4 |
| `correspondence-memory` | 2 | RETAIN | 3 |
| `correspondence-npc-replies` | 2 | RETAIN | 3 |
| `correspondence-player-surface` | 6 | RETAIN | 2 |
| `creation-activation-gating` | 2 | RETAIN | 3 |
| `creation-persona-persistence` | 4 | RETAIN | 5 |
| `cross-lineage-unlock` | 7 | TEST-ONLY | 3 |
| `damage-effect-handlers` | 5 | RETAIN | 3 |
| `damage-state-feedback` | 7 | RETAIN | 9 |
| `defeat-aftermath-core` | 7 | RETAIN | 6 |
| `defeat-aftermath-digest` | 4 | RETAIN | 2 |
| `defeat-aftermath-recovery` | 6 | DELTA | 4 |
| `defeat-aftermath-violation-sequence` | 10 | RETAIN | 5 |
| `dialogue-epochs` | 4 | RETAIN | 1 |
| `dialogue-offer-quest` | 4 | RETAIN | 1 |
| `dice-roller` | 2 | RETAIN | 1 |
| `disengage-action` | 5 | RETAIN | 3 |
| `disguised-stats-boundary` | 6 | RETAIN | 7 |
| `dismiss-options-action` | 4 | RETAIN | 2 |
| `displayed-stats-view` | 5 | RETAIN | 4 |
| `divine-mystery` | 4 | RETAIN | 4 |
| `dream-authoring` | 2 | RETAIN | 3 |
| `dream-explicit-presentation` | 4 | RETAIN | 4 |
| `dream-session-lifecycle` | 3 | RETAIN | 2 |
| `dream-sleep-surface` | 3 | RETAIN | 1 |
| `effect-context-validation` | 1 | RETAIN | 5 |
| `element-affinity` | 2 | TEST-ONLY | 4 |
| `element-mastery` | 1 | TEST-ONLY | 1 |
| `entity-sex-vocabulary` | 2 | RETAIN | 1 |
| `entity-trait-scales` | 9 | DELTA | 5 |
| `equipment-effects` | 13 | DELTA | 7 |
| `equipment-inventory` | 13 | TEST-ONLY | 10 |
| `erosion-leech` | 2 | RETAIN | 1 |
| `evennia-project-skeleton` | 3 | RETAIN | 2 |
| `evennia-test-guard` | 8 | RETAIN | 1 |
| `evennia-test-optimization` | 14 | RETAIN | 9 |
| `event-log` | 4 | RETAIN | 1 |
| `event-log-compression` | 5 | RETAIN | 1 |
| `exploration-affordances` | 6 | RETAIN | 8 |
| `fake-llm-client` | 3 | RETAIN | 3 |
| `field-combat-initiation` | 9 | RETAIN | 1 |
| `freeform-casting` | 7 | TEST-ONLY | 5 |
| `game-command-docs` | 12 | RETAIN | 2 |
| `gauge-transfer-effects` | 5 | TEST-ONLY | 4 |
| `generative-character-concept` | 4 | RETAIN | 3 |
| `gm-developer-console` | 14 | RETAIN | 13 |
| `gm-operations-dashboard` | 5 | RETAIN | 5 |
| `gm-portal-access-api` | 5 | RETAIN | 7 |
| `gm-portal-spa` | 6 | RETAIN | 3 |
| `gm-runtime-state` | 9 | RETAIN | 16 |
| `gm-save-management` | 8 | RETAIN | 9 |
| `gm-world-data` | 6 | RETAIN | 3 |
| `grid-room-sync` | 6 | RETAIN | 4 |
| `grid-room-typeclasses` | 4 | RETAIN | 3 |
| `guardrail` | 4 | RETAIN | 5 |
| `guild-exam-requests` | 2 | RETAIN | 4 |
| `guild-exam-restrictions` | 3 | DELTA | 2 |
| `guild-exam-schedule-hold` | 2 | RETAIN | 1 |
| `guild-quest-board` | 6 | RETAIN | 8 |
| `guild-rank-exams` | 9 | RETAIN | 2 |
| `guild-registration` | 7 | RETAIN | 9 |
| `heal-effect-handler` | 4 | RETAIN | 2 |
| `human-combat-calibration` | 2 | TEST-ONLY | 1 |
| `human-guild-hosts` | 3 | DELTA | 1 |
| `import-loader` | 7 | TEST-ONLY | 4 |
| `import-reference-example` | 4 | RETAIN | 2 |
| `import-schema` | 13 | RETAIN | 4 |
| `import-validation` | 17 | TEST-ONLY | 7 |
| `instance-reclamation` | 8 | RETAIN | 3 |
| `instance-room-typeclass` | 4 | RETAIN | 1 |
| `instance-spawn` | 4 | RETAIN | 1 |
| `internal-art-worker` | 7 | RETAIN | 4 |
| `inventory-item-actions` | 5 | RETAIN | 3 |
| `item-effect-rulebook` | 6 | RETAIN | 2 |
| `item-presentation-metadata` | 3 | RETAIN | 3 |
| `item-use-resolution` | 10 | RETAIN | 10 |
| `limbo-one-way-gates` | 7 | RETAIN | 2 |
| `limbo-room` | 3 | RETAIN | 1 |
| `living-entity-hierarchy` | 6 | RETAIN | 2 |
| `llm-client` | 7 | RETAIN | 3 |
| `llm-profiles` | 7 | RETAIN | 5 |
| `llm-transcript` | 3 | RETAIN | 2 |
| `localized-appearance` | 2 | RETAIN | 3 |
| `lore-item-catalog` | 7 | RETAIN | 12 |
| `lore-knowledge` | 10 | RETAIN | 3 |
| `lore-registries` | 14 | DELTA | 13 |
| `lore-startup-sync` | 4 | RETAIN | 3 |
| `map-knowledge` | 5 | RETAIN | 3 |
| `masterwork-price-band` | 3 | DELTA | 3 |
| `merchant-dialogue` | 2 | RETAIN | 2 |
| `military-equipment` | 2 | DELTA | 1 |
| `monster-action-policy` | 13 | DELTA | 12 |
| `monster-behaviour-profile` | 3 | RETAIN | 1 |
| `monster-flee-policy` | 7 | TEST-ONLY | 4 |
| `monster-individual-construction` | 8 | DELTA | 7 |
| `monster-resource-abilities` | 13 | DELTA | 6 |
| `monster-site-placement` | 6 | RETAIN | 3 |
| `monster-species-registry` | 10 | DELTA | 8 |
| `movement-cost-charging` | 6 | RETAIN | 4 |
| `movement-settlement-atomicity` | 3 | RETAIN | 4 |
| `mp-state-feedback` | 5 | RETAIN | 1 |
| `namegen-corpus-registry` | 6 | RETAIN | 2 |
| `narrative-attention` | 2 | RETAIN | 2 |
| `narrative-context` | 3 | RETAIN | 5 |
| `narrative-events` | 2 | RETAIN | 2 |
| `narrative-fast-recall` | 3 | RETAIN | 3 |
| `narrative-memory` | 3 | RETAIN | 6 |
| `narrative-quest-compilation` | 2 | RETAIN | 1 |
| `narrative-story-threads` | 2 | RETAIN | 3 |
| `narrator` | 5 | RETAIN | 3 |
| `npc-canonical-age` | 1 | RETAIN | 1 |
| `npc-dialogue` | 10 | RETAIN | 21 |
| `npc-identity-titles` | 23 | RETAIN | 26 |
| `npc-name-generation` | 4 | RETAIN | 1 |
| `npc-persona-card` | 10 | RETAIN | 2 |
| `npc-persona-cutover` | 3 | RETAIN | 1 |
| `npc-persona-editor` | 7 | RETAIN | 7 |
| `npc-profile-registry` | 11 | RETAIN | 4 |
| `npc-schedule-model` | 4 | RETAIN | 2 |
| `npc-schedule-runtime` | 12 | RETAIN | 7 |
| `npc-service-availability` | 2 | RETAIN | 1 |
| `observability-lint-gate` | 5 | RETAIN | 1 |
| `observability-logging` | 7 | RETAIN | 11 |
| `official-art-personalization` | 4 | RETAIN | 4 |
| `official-art-resolution` | 4 | RETAIN | 3 |
| `official-artwork-catalog` | 7 | RETAIN | 4 |
| `official-content-provenance` | 6 | RETAIN | 5 |
| `openspec-cli-version-pinning` | 1 | RETAIN | 1 |
| `ordered-level-trait` | 4 | RETAIN | 1 |
| `outbound-http-identity` | 2 | RETAIN | 3 |
| `overwhelm-threshold` | 7 | RETAIN | 3 |
| `party-system` | 12 | DELTA | 10 |
| `persona-dialogue-injection` | 4 | RETAIN | 7 |
| `persona-editing` | 4 | RETAIN | 4 |
| `persona-store` | 5 | RETAIN | 5 |
| `phase-scoped-spell-empowerment` | 3 | RETAIN | 1 |
| `place-attendant-hosts` | 3 | RETAIN | 2 |
| `place-driven-service-sync` | 5 | RETAIN | 4 |
| `place-price-scaling` | 4 | TEST-ONLY | 1 |
| `player-character-creation` | 15 | TEST-ONLY | 18 |
| `player-combat-session` | 18 | RETAIN | 17 |
| `player-control-predicate` | 1 | RETAIN | 1 |
| `player-stat-allocation` | 2 | TEST-ONLY | 3 |
| `positional-marker` | 6 | RETAIN | 2 |
| `preset-authoring-docs` | 2 | RETAIN | 1 |
| `profession-registries` | 4 | RETAIN | 1 |
| `prompt-library` | 6 | RETAIN | 7 |
| `quest-auto-settlement` | 4 | RETAIN | 1 |
| `quest-blueprint` | 12 | TEST-ONLY | 11 |
| `quest-delivery` | 9 | RETAIN | 4 |
| `quest-detail-view` | 2 | RETAIN | 2 |
| `quest-failure-conditions` | 4 | RETAIN | 2 |
| `quest-issuance` | 7 | RETAIN | 1 |
| `quest-issuer-authorization` | 5 | RETAIN | 6 |
| `quest-lifecycle` | 10 | RETAIN | 8 |
| `quest-progress-tracking` | 7 | RETAIN | 6 |
| `quest-reward-settlement` | 5 | DELTA | 7 |
| `recent-action-evidence` | 1 | RETAIN | 1 |
| `rulebook-schema` | 5 | RETAIN | 3 |
| `saintess-vessel` | 5 | DELTA | 6 |
| `sample-city-altoria` | 7 | RETAIN | 11 |
| `scenario-director` | 16 | RETAIN | 19 |
| `scene-archetype-mixin` | 3 | RETAIN | 2 |
| `scene-builder` | 13 | RETAIN | 12 |
| `scene-flavor` | 6 | RETAIN | 4 |
| `scripted-dialogue` | 3 | RETAIN | 3 |
| `service-anchoring` | 2 | RETAIN | 4 |
| `settings-environment-overrides` | 9 | RETAIN | 7 |
| `settlement-place-registry` | 5 | RETAIN | 2 |
| `settlement-stage-order` | 8 | RETAIN | 6 |
| `sexual-act-effects` | 16 | DELTA | 7 |
| `sexual-act-registry` | 16 | TEST-ONLY | 5 |
| `sexual-act-seeds` | 7 | RETAIN | 3 |
| `sexual-catalog-combat` | 5 | DELTA | 1 |
| `sexual-catalog-divine-core` | 5 | TEST-ONLY | 1 |
| `sexual-catalog-divine-mutators` | 6 | TEST-ONLY | 1 |
| `sexual-catalog-interspecies` | 5 | DELTA | 1 |
| `sexual-catalog-partner` | 8 | DELTA | 1 |
| `sexual-catalog-shame` | 7 | DELTA | 1 |
| `sexual-catalog-solo` | 3 | DELTA | 1 |
| `sexual-resist-cast-wiring` | 5 | RETAIN | 2 |
| `sexual-resist-contest` | 8 | RETAIN | 1 |
| `sexual-resist-out-of-combat` | 5 | RETAIN | 2 |
| `sexual-resist-turn-cost` | 4 | RETAIN | 1 |
| `sexual-state-handler` | 19 | DELTA | 9 |
| `sexual-transition-rulebook` | 14 | DELTA | 4 |
| `sexual-vocabulary` | 2 | RETAIN | 1 |
| `shop-economy` | 7 | TEST-ONLY | 4 |
| `single-shot-resolution` | 9 | RETAIN | 3 |
| `skill-category-registry` | 5 | RETAIN | 1 |
| `skill-effect-model` | 17 | RETAIN | 27 |
| `skill-handler` | 9 | RETAIN | 14 |
| `skill-identity-eligibility` | 5 | RETAIN | 13 |
| `skill-lineage` | 12 | DELTA | 16 |
| `skill-lineage-panel` | 6 | RETAIN | 7 |
| `skill-registry` | 25 | DELTA | 21 |
| `skip-safety-gate` | 6 | RETAIN | 3 |
| `spawn-named-portraits` | 2 | RETAIN | 3 |
| `spec-test-traceability` | 8 | DELTA | 2 |
| `species-portrait-identity` | 2 | RETAIN | 1 |
| `starting-companions` | 3 | DELTA | 2 |
| `stateful-spell-casting` | 3 | RETAIN | 1 |
| `story-director-beats` | 3 | RETAIN | 2 |
| `targeting-validation` | 7 | RETAIN | 3 |
| `terrain-marker` | 2 | RETAIN | 3 |
| `test-data-independence` | 25 | DELTA | 4 |
| `time-skip-commands` | 4 | RETAIN | 3 |
| `title-system` | 18 | DELTA | 23 |
| `universal-action-ownership` | 4 | RETAIN | 3 |
| `village-ciaran-map` | 3 | RETAIN | 3 |
| `webclient-action-dispatch` | 13 | RETAIN | 15 |
| `webclient-action-feedback` | 2 | RETAIN | 1 |
| `webclient-art-panel` | 12 | RETAIN | 6 |
| `webclient-browser-verification` | 8 | RETAIN | 9 |
| `webclient-character-creation-ui` | 14 | RETAIN | 14 |
| `webclient-character-roster` | 19 | RETAIN | 10 |
| `webclient-combat-beats` | 6 | RETAIN | 8 |
| `webclient-combat-menu` | 16 | RETAIN | 18 |
| `webclient-component-showcase` | 9 | RETAIN | 11 |
| `webclient-context-actions` | 2 | RETAIN | 3 |
| `webclient-context-actions-suggestions` | 5 | RETAIN | 4 |
| `webclient-contextual-hud` | 67 | RETAIN | 33 |
| `webclient-desktop-shell` | 15 | RETAIN | 17 |
| `webclient-dialogue-session` | 4 | RETAIN | 4 |
| `webclient-dream-stage` | 9 | RETAIN | 1 |
| `webclient-exploration-menu` | 22 | RETAIN | 23 |
| `webclient-frame-resolution` | 11 | RETAIN | 5 |
| `webclient-gallery-management-actions` | 9 | RETAIN | 1 |
| `webclient-gallery-panel` | 9 | RETAIN | 2 |
| `webclient-gallery-ui` | 13 | RETAIN | 1 |
| `webclient-input-narrative` | 11 | RETAIN | 5 |
| `webclient-local-map` | 14 | RETAIN | 16 |
| `webclient-login-gate` | 2 | RETAIN | 2 |
| `webclient-lore-codex-panel` | 11 | RETAIN | 3 |
| `webclient-narrative-markup` | 6 | RETAIN | 5 |
| `webclient-npc-persona-editor` | 6 | RETAIN | 3 |
| `webclient-objectives-panel` | 2 | RETAIN | 2 |
| `webclient-oob-protocol` | 11 | RETAIN | 17 |
| `webclient-options-surface` | 4 | RETAIN | 2 |
| `webclient-party-panel` | 4 | RETAIN | 3 |
| `webclient-pointer-activation` | 5 | RETAIN | 6 |
| `webclient-possession-presentation` | 5 | RETAIN | 1 |
| `webclient-quest-drawer` | 10 | RETAIN | 6 |
| `webclient-quest-log-panel` | 8 | RETAIN | 3 |
| `webclient-service-menus` | 10 | RETAIN | 14 |
| `webclient-skillbook-casting` | 9 | RETAIN | 3 |
| `webclient-status-presentation` | 7 | RETAIN | 8 |
| `webclient-vue-application` | 10 | RETAIN | 9 |
| `wilderness-gateway` | 8 | DELTA | 7 |
| `wilderness-map-provider` | 3 | RETAIN | 2 |
| `wilderness-monster-population` | 5 | DELTA | 2 |
| `wilderness-terrain` | 4 | RETAIN | 3 |
| `world-clock` | 15 | DELTA | 13 |

## Exact modified requirement inventory

### `affinity-cap-break`

- MODIFIED: The cap_breaks rulebook table drives milestone cap raises at quest turn-in
### `affinity-system`

- MODIFIED: The stage ladder maps hidden values to seven Traditional Chinese stage names
- MODIFIED: apply_affinity_change is the sole affinity writer with a source-capped daily budget
### `buff-handler-integration`

- MODIFIED: Buff tick is exposed as a plain callable, with no settlement order invented
### `church-ordination`

- MODIFIED: Series A/B/D rows ship as registry skills earned only through the church pipeline
- MODIFIED: Series C discipline passives ship pure-positive with no baseline downside
- MODIFIED: Series E utility rows feed the core loop
- MODIFIED: Series C/E rule rows load under the correspondence and polarity gates
### `combat-modifier-table`

- MODIFIED: Sexual-field rules degrade to inert until entity.sexual is real, then self-arm
- MODIFIED: Flat defense and atk_phys bundle values adjust deterministic damage magnitude
- MODIFIED: Percentage mp_cost and sp_cost bundle values adjust resource checks and deductions
- MODIFIED: Damage-estimation surfaces mirror the live adjusted damage math
- MODIFIED: Preview, preflight, and resolve agree on adjusted resource costs
- MODIFIED: Worn equipment merges into the merged bundle of both evaluation paths
- MODIFIED: Condition contexts match on effective exposure
- MODIFIED: Equipment-worn conditions match a shared worn-item fact
- MODIFIED: high_exposure_defense_penalty prices raised exposure as a combat cost
### `defeat-aftermath-recovery`

- MODIFIED: Defeat recovery advances the clock to the 5% wake target
- MODIFIED: The recovery rulebook section is validated by its own loader
- MODIFIED: A retained quest-bound winner forces the move-and-rest route
### `entity-trait-scales`

- MODIFIED: Static combat trait bases are read directly from RaceProfile.static_baseline, never derived from vital_baseline
- MODIFIED: Subrace static_modifiers and vital_overrides apply in a fixed order: race baseline, then static_modifiers, then vital_overrides
- MODIFIED: A caller may name a STATIC_TIER_REGISTRY tier to land inside a specific power band instead of the species floor
### `equipment-effects`

- MODIFIED: Equipment adjustments render as deterministic prose
- MODIFIED: Effective exposure is a pure clamped read-time overlay
### `guild-exam-restrictions`

- MODIFIED: Reduced neutral baselines precede penalties and preserve both agility consumers
- MODIFIED: A and S examination kits retain real lineage effects
### `human-guild-hosts`

- MODIFIED: Normal hosts own literal bases gear and usable complete human skill lineages
### `lore-registries`

- MODIFIED: RaceProfile encodes the three-race power gap
- MODIFIED: StaticTier registry records named power bands within each race's static_baseline
- MODIFIED: Subrace registry covers elf branches, beastfolk subspecies, and human bloodline subraces with stat modifiers
- MODIFIED: MagicTier bands are contiguous and non-overlapping
- MODIFIED: MonsterTier registry has physical stat and HP bands derived from guild rank
- MODIFIED: Currency is an integer count of 銅 with no floats in the money path
### `masterwork-price-band`

- MODIFIED: A masterwork price band spans everyday and scarce prices for the same object
### `military-equipment`

- MODIFIED: Six military pairs use shared registered effects and approved integer prices
- MODIFIED: Military pairs participate in ordinary finite commerce
### `monster-action-policy`

- MODIFIED: Authored crocodile behavior uses the existing first-owned strategy
- MODIFIED: 穗鳴雀 contact kit uses existing first-owned policy and fallback
- MODIFIED: 潮燈蟹 contact kit uses existing first-owned policy and fallback
### `monster-individual-construction`

- MODIFIED: 穗鳴雀 construction persists both approved contact kits
- MODIFIED: 潮燈蟹 construction persists both approved contact kits
### `monster-resource-abilities`

- MODIFIED: Crocodile bite is one authored shared-engine physical resource skill
- MODIFIED: Successful bite drains MP and recovers only actual removal
- MODIFIED: Affordability precedes effects and recovery precedes costs
- MODIFIED: Production crocodile delivery includes real combat and persistence evidence
- MODIFIED: 穗鳴雀 owns its approved contact resource ability
- MODIFIED: 穗鳴雀 timed modifier follows its authored recipient and lifetime
- MODIFIED: 穗鳴雀 payment and atomicity retain the shared transaction
- MODIFIED: 潮燈蟹 owns its approved contact resource ability
- MODIFIED: 潮燈蟹 timed modifier follows its authored recipient and lifetime
- MODIFIED: 潮燈蟹 payment and atomicity retain the shared transaction
### `monster-species-registry`

- MODIFIED: The approved first-batch profiles and grades are user-approved literals
- MODIFIED: Numeric combat profiles and danger grades are balance-gated slots, never invented values
### `party-system`

- MODIFIED: Completing a quest rewards each then-in-party companion with affinity
### `quest-reward-settlement`

- MODIFIED: Reward payout is one atomic copper, item, merit, acquisition, claim, and affinity transaction
### `saintess-vessel`

- MODIFIED: Each named public blessing ceremony reads the holder's excitement tier exactly once
- MODIFIED: Saintess trickle pins the holder's idle arousal inside the idle band
### `sexual-act-effects`

- MODIFIED: compute_pleasure_gain scales base_pleasure by ratio, sensitivity, shame, and participant count
### `sexual-catalog-combat`

- MODIFIED: Eight Tier 1/2/3/5 combat acts are registered, gated by hostile_act_count and/or climax_count and/or climax_extension_count thresholds
- MODIFIED: combat_forced_climax, combat_relentless_torment, and combat_climax_domination reliably clear the climax extension threshold
- MODIFIED: combat_forced_climax and combat_relentless_torment differ by actor_pleasure_ratio, not by dominance-freedom tuning
### `sexual-catalog-interspecies`

- MODIFIED: Seven Tier 1-4 interspecies acts are registered, gated by hostile_act_count and/or climax_count and/or interspecies_act_count thresholds
- MODIFIED: interspecies_receive declares the highest actor_pleasure_ratio among this change's seven acts
- MODIFIED: interspecies_mating grants the actor strictly more pleasure than interspecies_receive despite the lower ratio
### `sexual-catalog-partner`

- MODIFIED: Sixteen Tier 1-4 partner acts are registered, gated by duo_act_count and/or group_act_count and/or climax_count thresholds
- MODIFIED: The four Tier 3 acts trade off at baseline sensitivity
### `sexual-catalog-shame`

- MODIFIED: Nine Tier 1-4 shame acts are registered, gated by exposure_act_count and/or watched_count thresholds
### `sexual-catalog-solo`

- MODIFIED: Eleven Tier 1-3 solo acts are registered, gated by masturbation_count and/or toy_use_count thresholds
### `sexual-state-handler`

- MODIFIED: pleasure is constructed from an imported baseline's arousal level at that level's band floor
- MODIFIED: arousal is a derived, read-only view over pleasure, comparable exactly as before
- MODIFIED: decay_tick decays pleasure by crossing exactly one band per configured interval
- MODIFIED: Equipment exposure bias never touches stored state
### `sexual-transition-rulebook`

- MODIFIED: The one rule targeting a vital gauge outside SexualState writes through change 3's entity.traits surface, never through SexualState
- MODIFIED: pleasure-targeting rules write through the bounded_counter kind, and report their arousal-level crossing under the field name arousal
### `skill-lineage`

- MODIFIED: The fire lineage ships as the authored branching tree with a two-parent canopy
- MODIFIED: The wind lineage ships as the authored two-root branching tree with a two-parent canopy
- MODIFIED: The ice lineage ships as the authored two-root branching tree with a two-parent canopy
- MODIFIED: The lightning lineage ships as the authored two-root branching tree with a two-parent canopy
### `skill-registry`

- MODIFIED: dual_wield_style is a PASSIVE stance, not a castable ACTIVE skill
- MODIFIED: Reincarnation boon labels match the preset character names
- MODIFIED: Lightning spell progression composes executable turn-order behavior
### `spec-test-traceability`

- ADDED: Test migrations preserve meaningful current requirement coverage
### `starting-companions`

- MODIFIED: A preset declares its starting companions by partner preset key
### `test-data-independence`

- MODIFIED: Data-contract tests are explicitly classified
- ADDED: Production content checks validate references without numerical approval mirrors
- ADDED: Shared synthetic mechanism coverage owns independently known outcomes
- ADDED: Representative production smoke proves real consumer integration proportionally
### `title-system`

- MODIFIED: The clergy title ladder unlocks by redeemed count and never displays 聖女
### `wilderness-gateway`

- MODIFIED: wilderness_move is a new, distinct clock cost, not a reuse of the grid's move constant
### `wilderness-monster-population`

- MODIFIED: population_for_coordinates is a pure, deterministic function over the bounded map
### `world-clock`

- MODIFIED: move and converse command-default time costs are declared as rulebook data only

## All classified content-test files

| Existing path | Family | Concrete migration/retention rationale |
| --- | --- | --- |
| `tests/test_command_docs.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `tests/test_preset_authoring_docs_contract.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/ai/tests/test_director_template_cards.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/ai/tests/test_dream_frame_contract.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/imports/tests/test_yohanna_demo.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/lore/tests/test_anchor_placement.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_anchors.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_assortments.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/lore/tests/test_church.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_dialogue_assembly.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_economy.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/lore/tests/test_elements.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_guild.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_items.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/lore/tests/test_magic.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_monster_species_content.py` | MONSTER | Remove approved profile/cost/magnitude mirrors; retain taxonomy, tier bounds, reference/kit gates and representative composition smoke. Detect missing profile/skill, wrong receiver or refill after reload. |
| `world/lore/tests/test_monsters.py` | MONSTER | Remove approved profile/cost/magnitude mirrors; retain taxonomy, tier bounds, reference/kit gates and representative composition smoke. Detect missing profile/skill, wrong receiver or refill after reload. |
| `world/lore/tests/test_names.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_nations.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_npc_profile_inventory.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_npc_profile_slice_content.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_npc_tiers.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_player_presets.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_races.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_registry_index_contract.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_room_prose_language.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_saintess_vessel_grant.py` | CHURCH | Remove final prices/gains/durations/bonus pins; keep ordination, endpoints, polarity, daily flags, idle named bands and defense/snapshot observations. Detect gate bypass, duplicate accrual/snapshot, wrong holder or transaction leak. |
| `world/lore/tests/test_scene_archetypes.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_settlements.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_sex.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_sexual_vocab.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/lore/tests/test_shops.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/lore/tests/test_starting_kits.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/lore/tests/test_sync.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/lore/tests/test_titles_registry.py` | LORE | Remove copied mutable bands/modifiers/starting values/thresholds; keep identity, power-gap, zero-sum/directional intent, age safety and taxonomy. Detect crossed bounds, invalid rank/profile references, wrong source/order or unauthorized identity changes. |
| `world/lore/tests/test_wilderness_entry.py` | CLOCK | Replace production duration/density pins with configured-cost integration and synthetic boundaries; retain topology, calendar and causality. Detect uncharged/double-charged movement, wrong cost key or nondeterminism. |
| `world/lore/tests/test_wilderness_regions.py` | CLOCK | Replace production duration/density pins with configured-cost integration and synthetic boundaries; retain topology, calendar and causality. Detect uncharged/double-charged movement, wrong cost key or nondeterminism. |
| `world/maps/tests/test_altoria_capital.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/maps/tests/test_bootstrap.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/maps/tests/test_city_movement_cost.py` | CLOCK | Replace production duration/density pins with configured-cost integration and synthetic boundaries; retain topology, calendar and causality. Detect uncharged/double-charged movement, wrong cost key or nondeterminism. |
| `world/maps/tests/test_city_walkthrough.py` | CLOCK | Replace production duration/density pins with configured-cost integration and synthetic boundaries; retain topology, calendar and causality. Detect uncharged/double-charged movement, wrong cost key or nondeterminism. |
| `world/maps/tests/test_village_ciaran.py` | RETAIN | Retain identity/topology/prose/language/roster and security checks: these do not approve balance magnitudes. Do not weaken canonical prose correspondence or content-quality checks. |
| `world/quests/tests/test_compile_blueprint.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/quests/tests/test_compile_offline.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/quests/tests/test_compile_registration.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/quests/tests/test_definitions.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/quests/tests/test_hunt_catalog_content.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/quests/tests/test_scenario_mapping.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/rules/tests/test_affinity_config.py` | AFFINITY | Keep canonical vocabulary/natural cap; replace budget/quest gain pins with authored validation and synthetic ordering. Detect invalid stage topology or cap-before-gain regression. |
| `world/rules/tests/test_buffs.py` | BUFF | Replace shipped duration/rate/charge pins with definition integrity and synthetic tick/expiry/refresh/reload tests. Detect replayed tick, lost source, invalid shape or wrong expiry partition. |
| `world/rules/tests/test_church_accrual.py` | CHURCH | Remove final prices/gains/durations/bonus pins; keep ordination, endpoints, polarity, daily flags, idle named bands and defense/snapshot observations. Detect gate bypass, duplicate accrual/snapshot, wrong holder or transaction leak. |
| `world/rules/tests/test_church_enrollment.py` | CHURCH | Remove final prices/gains/durations/bonus pins; keep ordination, endpoints, polarity, daily flags, idle named bands and defense/snapshot observations. Detect gate bypass, duplicate accrual/snapshot, wrong holder or transaction leak. |
| `world/rules/tests/test_church_hosts.py` | CHURCH | Remove final prices/gains/durations/bonus pins; keep ordination, endpoints, polarity, daily flags, idle named bands and defense/snapshot observations. Detect gate bypass, duplicate accrual/snapshot, wrong holder or transaction leak. |
| `world/rules/tests/test_church_rulebook.py` | CHURCH | Remove final prices/gains/durations/bonus pins; keep ordination, endpoints, polarity, daily flags, idle named bands and defense/snapshot observations. Detect gate bypass, duplicate accrual/snapshot, wrong holder or transaction leak. |
| `world/rules/tests/test_clock.py` | CLOCK | Replace production duration/density pins with configured-cost integration and synthetic boundaries; retain topology, calendar and causality. Detect uncharged/double-charged movement, wrong cost key or nondeterminism. |
| `world/rules/tests/test_crocodile_resource_skill.py` | MONSTER | Remove approved profile/cost/magnitude mirrors; retain taxonomy, tier bounds, reference/kit gates and representative composition smoke. Detect missing profile/skill, wrong receiver or refill after reload. |
| `world/rules/tests/test_equipment_effect_rulebook.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_guild_config/_support.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_guild_config/test_assortment_shop_rules.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_guild_config/test_catalog_loading.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_guild_config/test_commerce_rulebook_slices.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_guild_config/test_item_offer_definitions.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_guild_config/test_merit_exam_rulebook.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_guild_config/test_price_scaling.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_guild_config/test_service_host_roster.py` | ECONOMY | Remove literal production prices, stock, adjustments and host/exam tuning; keep item/slot/band/reference/roster invariants and distinct materialization boundaries. Detect missing references, illegal shape, wrong placement or double application. |
| `world/rules/tests/test_human_combat_calibration.py` | CALIBRATION | Remove normal-production stat and fixed seeded outcome approvals; retain bounded real gear/restriction/action-validity evidence, outcome taxonomy and no awards. Zero rejected actions is not balance evidence. Detect illegal selections, simulation leakage or missing records. |
| `world/rules/tests/test_monster_behaviour_profile.py` | MONSTER | Remove approved profile/cost/magnitude mirrors; retain taxonomy, tier bounds, reference/kit gates and representative composition smoke. Detect missing profile/skill, wrong receiver or refill after reload. |
| `world/rules/tests/test_npc_roster_validation.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/rules/tests/test_npc_schedules.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/rules/tests/test_profession_config.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/rules/tests/test_rulebook_schema.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/rules/tests/test_saintess_vessel_trickle.py` | CHURCH | Remove final prices/gains/durations/bonus pins; keep ordination, endpoints, polarity, daily flags, idle named bands and defense/snapshot observations. Detect gate bypass, duplicate accrual/snapshot, wrong holder or transaction leak. |
| `world/rules/tests/test_shipped_item_use_regression.py` | CONSUMER | Retain schema/card/identity and real integration; replace mutable payout/resource/threshold literal expectations with synthetic fixtures or distinct declaration-to-persistence properties. Detect broken materialization, missing references, double scaling or silent reset. |
| `world/rules/tests/test_sway_whistle_sparrow_resource_skill.py` | MONSTER | Remove approved profile/cost/magnitude mirrors; retain taxonomy, tier bounds, reference/kit gates and representative composition smoke. Detect missing profile/skill, wrong receiver or refill after reload. |
| `world/rules/tests/test_tide_lamp_crab_resource_skill.py` | MONSTER | Remove approved profile/cost/magnitude mirrors; retain taxonomy, tier bounds, reference/kit gates and representative composition smoke. Detect missing profile/skill, wrong receiver or refill after reload. |
| `world/skills/sexual_acts/tests/test_acceptance.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_combat_catalog.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_divine_core_catalog.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_divine_mutators_catalog.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_interspecies_catalog.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_partner_catalog.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_registry_structure/_support.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_registry_structure/test_divine_structure.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_registry_structure/test_registry_assembly.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_seed_acts.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_shame_catalog.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/sexual_acts/tests/test_solo_catalog.py` | SEXUAL | Replace mutable gain/ratio/unlock tables with authored shape, gate-key topology and comparative intent; shared fixtures own arithmetic. Detect compound-gate omission, swapped roles, wrong parts/counters/events or broken comparative quality. |
| `world/skills/tests/test_cost_tiers.py` | SKILL | Remove production magnitude/cost/duration pins; validate effects, vocabulary, audience and policy. Keep damage out-of-combat eligibility and established cost-tier bounds. Detect unresolvable effects, wrong hit index, category/policy drift or lost ownership. |
| `world/skills/tests/test_skill_registry/_support.py` | SKILL | Remove production magnitude/cost/duration pins; validate effects, vocabulary, audience and policy. Keep damage out-of-combat eligibility and established cost-tier bounds. Detect unresolvable effects, wrong hit index, category/policy drift or lost ownership. |
| `world/skills/tests/test_skill_registry/test_category_classification.py` | SKILL | Remove production magnitude/cost/duration pins; validate effects, vocabulary, audience and policy. Keep damage out-of-combat eligibility and established cost-tier bounds. Detect unresolvable effects, wrong hit index, category/policy drift or lost ownership. |
| `world/skills/tests/test_skill_registry/test_content_completion.py` | SKILL | Remove production magnitude/cost/duration pins; validate effects, vocabulary, audience and policy. Keep damage out-of-combat eligibility and established cost-tier bounds. Detect unresolvable effects, wrong hit index, category/policy drift or lost ownership. |
| `world/skills/tests/test_skill_registry/test_out_of_combat_policy.py` | SKILL | Remove production magnitude/cost/duration pins; validate effects, vocabulary, audience and policy. Keep damage out-of-combat eligibility and established cost-tier bounds. Detect unresolvable effects, wrong hit index, category/policy drift or lost ownership. |
| `world/skills/tests/test_skill_registry/test_registry_contract.py` | SKILL | Remove production magnitude/cost/duration pins; validate effects, vocabulary, audience and policy. Keep damage out-of-combat eligibility and established cost-tier bounds. Detect unresolvable effects, wrong hit index, category/policy drift or lost ownership. |
| `world/skills/tests/test_spell_catalogs.py` | SKILL | Remove production magnitude/cost/duration pins; validate effects, vocabulary, audience and policy. Keep damage out-of-combat eligibility and established cost-tier bounds. Detect unresolvable effects, wrong hit index, category/policy drift or lost ownership. |

## Existing debt paths

Debt is not a new exemption. No debt is added or re-seeded. Unrelated UI/AI/name-fit debt remains outside numerical migration unless a specific mutable assertion is identified. `test_item_effects_rulebook.py` already has fixed synthetic parse fixtures (local amount -12); `test_traits.py` retains mechanism setup. Skill-registry self-arming remains live schema/ownership integration. Keep useful mechanism assertions while removing production pins.

- `web/webclient-app/tests/action/dock_items.test.js`
- `web/webclient-app/tests/action/dock_menu.test.js`
- `web/webclient-app/tests/action/dock_menu_panes.test.js`
- `web/webclient-app/tests/components/dock_panes.test.js`
- `web/webclient-app/tests/data/party_drawer.test.js`
- `web/webclient-app/tests/store/protocol_fixtures.js`
- `web/webclient-app/tests/store/store_slices.test.js`
- `web/webclient-app/tests/world/map_lattice_edge_names.test.js`
- `web/webclient-app/tests/world/map_lattice_name_fit.test.js`
- `web/webclient-app/tests/world/map_lattice_support.js`
- `world/ai/tests/test_npc_dialogue_prompts.py`
- `world/imports/tests/test_skill_registry_self_arming.py`
- `world/rules/tests/test_item_effects_rulebook.py`
- `world/rules/tests/test_traits.py`

## Additional concrete shared/behavior suites

These are not new content registrations. Fixed synthetic fixtures remain appropriate; use the migration plan for their production references and self-oracles.

- `world/maps/tests/test_wilderness_population.py`
- `world/maps/tests/test_wilderness_population_species.py`
- `world/rules/tests/test_combat_modifiers.py`
- `world/rules/tests/test_combat_modifiers_matched.py`
- `world/rules/tests/test_combat_modifiers_self_arming.py`
- `world/rules/tests/test_damage_state_feedback/test_pleasure_gain_rule_shapes.py`
- `world/rules/tests/test_defeat_aftermath_core/__init__.py`
- `world/rules/tests/test_defeat_aftermath_core/_support.py`
- `world/rules/tests/test_defeat_aftermath_core/test_debuff_and_violation_hook.py`
- `world/rules/tests/test_defeat_aftermath_core/test_departure_rules.py`
- `world/rules/tests/test_defeat_aftermath_core/test_recovery_solve_and_advance.py`
- `world/rules/tests/test_defeat_aftermath_core/test_rendering_and_rulebook_loader.py`
- `world/rules/tests/test_defeat_aftermath_core/test_retained_winner_and_causality.py`
- `world/rules/tests/test_defeat_aftermath_core/test_zero_uncaused_write_and_rollback.py`
- `world/rules/tests/test_defeat_aftermath_digest.py`
- `world/rules/tests/test_defeat_aftermath_violation/__init__.py`
- `world/rules/tests/test_defeat_aftermath_violation/_support.py`
- `world/rules/tests/test_defeat_aftermath_violation/test_attempt_loop_and_pool_digest.py`
- `world/rules/tests/test_defeat_aftermath_violation/test_companion_pool.py`
- `world/rules/tests/test_defeat_aftermath_violation/test_martyr_vow.py`
- `world/rules/tests/test_defeat_aftermath_violation/test_rollback_replay.py`
- `world/rules/tests/test_defeat_aftermath_violation/test_state_derived_rolls_and_threshold_gate.py`
- `world/rules/tests/test_defeat_aftermath_violation/test_violation_rulebook.py`
- `world/rules/tests/test_effect_audiences/__init__.py`
- `world/rules/tests/test_effect_audiences/_support.py`
- `world/rules/tests/test_effect_audiences/test_authoring_and_pure_planner.py`
- `world/rules/tests/test_effect_audiences/test_effect_routing_pipeline.py`
- `world/rules/tests/test_effect_audiences/test_effect_routing_pipeline_rollback_and_composite_effects.py`
- `world/rules/tests/test_effect_potency.py`
- `world/rules/tests/test_gauge_transfer/__init__.py`
- `world/rules/tests/test_gauge_transfer/_support.py`
- `world/rules/tests/test_gauge_transfer/test_drain_and_share.py`
- `world/rules/tests/test_gauge_transfer/test_parse_and_validation.py`
- `world/rules/tests/test_gauge_transfer/test_regen_lock_and_clock.py`
- `world/rules/tests/test_gauge_transfer/test_restore_and_audience_conditions.py`
- `world/rules/tests/test_item_use/__init__.py`
- `world/rules/tests/test_item_use/_support.py`
- `world/rules/tests/test_item_use/test_item_use_preflight.py`
- `world/rules/tests/test_item_use/test_item_use_settlement.py`
- `world/rules/tests/test_item_use/test_multi_effect_settlement.py`
- `world/rules/tests/test_item_use/test_multi_effect_surfaces.py`
- `world/rules/tests/test_item_use/test_registry_profile_gauge.py`
- `world/rules/tests/test_item_use/test_sexual_surface_rollback.py`
- `world/rules/tests/test_item_use/test_target_resolution_and_rollback.py`
- `world/rules/tests/test_progression/__init__.py`
- `world/rules/tests/test_progression/_support.py`
- `world/rules/tests/test_progression/test_derived_and_cross_lineage_unlocks.py`
- `world/rules/tests/test_progression/test_element_affinity_and_practice_pipeline.py`
- `world/rules/tests/test_progression/test_preset_lineage_and_npc_policy.py`
- `world/rules/tests/test_progression/test_progression_ladder.py`
- `world/rules/tests/test_sexual_act_effects/__init__.py`
- `world/rules/tests/test_sexual_act_effects/_support.py`
- `world/rules/tests/test_sexual_act_effects/test_act_cast_handler_integration.py`
- `world/rules/tests/test_sexual_act_effects/test_config_and_pure_helpers.py`
- `world/rules/tests/test_sexual_act_effects/test_pair_events_and_solo_cast.py`
- `world/rules/tests/test_sexual_act_effects/test_pleasure_gain_and_counter_tables.py`
- `world/rules/tests/test_sexual_act_effects/test_sexual_event_channel_boundaries.py`
- `world/rules/tests/test_sexual_state.py`
- `world/rules/tests/test_skill_hit_dependencies.py`
- `world/rules/tests/test_skill_lineage.py`
