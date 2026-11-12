# Proposal

## Why

The permanent decision modes need names that describe their behavior. The reflex skill heuristic also ignores authored damage coefficients and compares area skills through an early-return branch, preventing a common output comparison.

## What Changes

- **BREAKING**: replace mode values `legacy` with `reflex` and `utility` with `deliberation`, including enum members, fallback setting values, authored rulebook modes, consumers, documentation and evidence. No aliases or migrations.
- Compare affordable authored reflex damage skills using exact `E(s) = A(s) × c(s) × R(s)`. The attacking stat includes the actor's own adjustments; area coverage counts living hostile recipients. Defender terms and hit chance are excluded.
- Preserve `first_owned` as deterministic first affordable authored damage skill. For `highest_expected_damage`, sample exact estimates using existing independent seeded softmax and an archetype-authored `reflex_temperature`. The innate `basic_attack` is fallback only in both paths.
- Remove the area-preference flag from reflex selection. Keep its existing deliberation scoring role unchanged.
- Change tuning fingerprints and regenerate linked activation, selector, campaign and performance evidence under the new algorithm. Superseded evidence cannot establish acceptance of the new tuning.

This incorporates the supervisor's corrected uncertainty requirement. The earlier deterministic maximum/tie-rule request is superseded; equal reflex estimates receive equal sampling probabilities under the stochastic strategy.

## Capabilities

### New Capabilities

None. Existing capability requirements own the changed mechanisms.

### Modified Capabilities

- `monster-action-policy`: exact reflex estimate, common shape competition, authored-kit fallback and seeded sampling; rename mode prose.
- `combat-modifier-table`: preserve adjusted attacking-stat reads while removing the reflex defender term; leave overwhelm estimation unchanged.
- `monster-behaviour-profile`: clean mode vocabulary, temperature validation/ownership and fingerprint inputs.
- `monster-ai-rollout`: permanent reflex rollback and fresh evidence obligations.
- `monster-flee-policy`: rename mode references while preserving reflex flee priority, deliberation flee exclusion and typed-invalid-state reflex fallback.
- `monster-ai-utility-selection`: rename mode/fallback prose and scope intelligence-based temperature to deliberation.
- `monster-ai-decision-inputs`: rename the mode receiving existing shared legality.
- `monster-ai-legal-candidates`: rename mode/fallback references without changing candidates.
- `monster-ai-tactical-support`: rename references without changing support valuation.
- `monster-ai-observed-coordination`: rename references without changing coordination.
- `monster-ai-manual-validation`: rename report mode labels without changing campaign allocation or thresholds.

## Impact

Implementation is one engineer-day of focused policy/configuration work, mechanical consumer cutover and explicit evidence operations, in this repository only. Main-spec requirement headings and canonical IDs remain stable, including historical headings containing the former names. No capability directory or mathematical utility API is renamed. Tests establish mechanisms with synthetic inputs; no shipped copy, roster or balance-number approval assertions are added.

Current design authority is `docs/superpowers/specs/2026-10-11-monster-ai-design.md`; implementation amends its permanent-mode/unchanged-skill-dice clauses to this corrected contract, together with its attack and simulation companion documents. Documentation terminology and behavior interpretation are human-reviewed in this change's `design.md`, under “Human review record”; no prose-quality requirement or test is invented.

## Non-goals

No buckets/steps, defender defense or defense ratio, agility or hit-chance term; no deliberation scoring/temperature changes, new skills/stats, data migration, compatibility aliases, hot reload, combat formula changes, target tie-break changes or new player commands.

## Dependency/conflict matrix

| Change | Prerequisites | Conflicting surfaces | Integration order |
| --- | --- | --- | --- |
| `monster-decision-modes-rename-and-reflex-area-estimate` | Existing AI implementation on `master`; no active change dependency | Monster policy, mode consumers/settings, rulebook, AI tests/docs/specs and fingerprinted evidence | Single owner; rename/configuration, reflex selection, focused checks, then evidence regeneration |

The two decisions stay coupled because both invalidate the same evidence and rollback contract. No split or child repository is required.
