# Proposal

## Why

`art.monster_description` declares the dead placeholder `examples` — never supplied by any caller and forbidden by the monster-description contract — while `display_name` is declared but also never supplied, so a shipped template that actually used it would crash with an uncapturable `KeyError` instead of degrading. At the same time the prompt suite is pin-churn hostage: two baseline tests fail even at the pre-retune HEAD (one pins the literal `art.character_description` sentence, one builds a monster subject from a threat-tier key retired by `fix-monster-species-portraits` and asserts against the wrong registry), and the routine wording retune of commit `858e52dc` ("append `, standing, rim light on clothes,`" plus LoRA tags) additionally breaks a dozen more shipped-text pins across `test_verbatim_shipment.py`, `test_loader.py`, and the `world/art/` description-composition tests — proving every shipped-wording pin, in any prompt file's tests, is churn the moment the deployment owner edits the text.

## What Changes

- Wire the monster subject seam to the visual registry: `monster_description` always supplies both public identity values — `description` (the row's `published_appearance_zh`) and `display_name` (the row's `display_label`) — so the template owns which tokens it uses while no declared token can be missing at render time. The `PromptUnavailableError` degrade path keeps returning `published_appearance_zh` alone.
- **BREAKING** (unreleased, internal contract) Reduce the `art.monster_description` allowlist in `world/prompts/registry.py` from `("description", "display_name", "examples")` to exactly `("description", "display_name")`. `examples` was never supplied, the visual registry row carries no examples field, and the specs forbid mixed-species examples in a monster description; a template using `{examples}` now fails as an unknown-placeholder load error and `render_prompt(..., examples=...)` raises `UnexpectedPromptValueError`.
- Rebind the monster prompt-field contracts from "appearance only" to the closed two-token vocabulary (public physical appearance + public species display label): tier rank and multi-species examples stay forbidden.
- Restate the prompt-library test contract as code-level, suite-wide across every prompt file (`narrator.yaml`, `npc_dialogue.yaml`, `art.yaml`, `action_options.yaml`, …): prompt tests assert key registration, allowlist/template token parity, value substitution, render determinism, and degrade behavior — and MUST NOT pin literal shipped-template wording from any `prompts/*.yaml`, which the deployment owner edits freely. The byte-for-byte verbatim-shipment pins in `test_verbatim_shipment.py` and the whole shipped-sentence `assertIn` pins across the prompt suite are retired; short semantic probes naming the role/language/fidelity vocabulary an owning main-spec scenario itself names stay wherever their owning requirement's coverage places them. What the text must *mean* (language, fidelity, output-contract, hidden-value rules) stays owned by each consumer capability's own content-contract tests, unchanged here.
- Rework the affected test sites: drop the literal wording pins in `test_loader.py` (byte-identity test, whole shipped framing-sentence spots — keep two-render determinism + supplied-value substitution logic), extend the placeholder-set parity pattern to `art.monster_description`, rebuild `test_degrade.py`'s broken-art degrade test on a registered visual species key asserting the fallback equals the registry's own `published_appearance_zh` projection, rewrite `test_verbatim_shipment.py`'s shipped-text pins as logic/parity/substitution checks and align its monster render with the two-parameter contract, sweep the remaining whole-sentence shipped-wording pins across `world/prompts/tests/`, and audit the incidental `{examples}` inline fixtures in `world/prompts/tests/` and `world/art/tests/` (keep only intentional unknown-placeholder traps).

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `prompt-library`: `art.monster_description` is registered with exactly `description` and `display_name`; prompt-library tests are required to verify program logic (registration, parity, substitution, determinism, degrade) and forbidden from pinning shipped-template wording.
- `art-subject-model`: the monster description seam always supplies both public identity values from the selected visual-species row; the degraded fallback stays `published_appearance_zh` alone; "registry text" wording updated to the two-token data vocabulary with tier descriptions and multi-species examples still forbidden.
- `art-gallery-prompt-fields`: the monster card provenance scenario follows the same two-token data vocabulary — species public appearance plus species public label, never a threat-tier rank or mixed-species examples.

## Impact

- Code (prototype already in the working tree, finalize as part of this change): `world/art/subjects.py::monster_description`, `world/prompts/registry.py` `art.monster_description` spec.
- Tests: the whole prompt test suite — `world/prompts/tests/` (`test_loader.py`, `test_degrade.py`, `test_verbatim_shipment.py`; `test_validate_cli.py` audited) plus `world/art/tests/test_subjects.py` and `world/art/tests/test_gallery_prompt.py`; the `world/ai/` prompt-construction tests are audited, not rewritten — their short role/language/fidelity probes name vocabulary their own main-spec scenarios state and stay. The byte-for-byte verbatim-shipment pins (narrator, scenario-director, npc-dialogue, `npc.thinking`, art templates, scene-builder, action-options) are retired as prompt-library obligations; what shipped text must *mean* (language, fidelity, output-contract, hidden-value rules) stays owned by each consumer capability's own content-contract tests, which this change leaves unchanged. Because `PromptFixture` seeds its fixture root by copying the repo's own `prompts/`, the description-composition suites (`AppearanceDescriptionTests`, `CompositionTests`) inherit the shipped framing and are already broken by commit `858e52dc`'s template retune — they move to test-owned inline fixtures so composition claims no longer depend on deployment wording. No test files move, so `.github/evennia-shards.json` registration is unchanged.
- No player-facing command, documentation, gallery-pipeline, or data changes; every `prompts/*.yaml` wording itself is deployment-authored and stays out of the pinned contract (the shipped `art.yaml` `{description}`-only monster text remains valid under the two-token allowlist).
- Follows archived `2026-10-11-fix-monster-species-portraits` D2: this change completes its prompt-wiring intent — appearance *plus* the species' own public display label as an allowlisted token, with the example-placeholder deletion it ordered.

## Non-goals

No template wording edits or pins in `prompts/art.yaml`, no new prompt keys, no changes to character description composition, no backward-compat shim for `examples` (unreleased project), no changes to `SYNTH_MONSTER_TIERS` itself or other tier consumers, no test-file moves.
