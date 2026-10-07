## Context

See `proposal.md` for motivation and the Yuna boundary. The approved engine architecture assigns mutation to deterministic owners and keeps WebClient presentation read-only. This design changes attention metadata without changing a gameplay writer.

Current implementation evidence:

- `world/rules/status_query/status.py` builds buff-instance rows plus the exact `assembly.matches` used by breakdown. `ConditionValue` currently has no source field.
- `_assemble` and `_sexual_condition_context` use no-create stored readers. Exposure uses the shared pure `effective_exposure` overlay. The latter context currently projects buff cache instance keys, whereas canonical `active_buff_keys_from_storage` and combat's buff predicates use logical definition keys. Attached instances require correcting that projection inside the affected status-query context to maintain combat parity.
- `toggle_equipment` derives attached instances with `attached_buff_instances(normalized_mapping)`, keys them as `definition:item`, persists `definition_key` and `source_key=item`, and removes only the detached item's instances atomically. A bare `source_key`, a colon in a key, or a matching definition alone is insufficient proof of equipment ownership.
- `status_presenter` serializes the frozen model and publishes implemented `STATUS_SCHEMA_VERSION = 2`; browser `protocol/panels/status.js` validates exact available v2 condition objects. The main compact-status requirement still names v1. This delta updates that touched requirement to v3 and preserves the existing optional composed full title.
- `isVitalsVisible` currently accepts every adverse severity; `buildView` supplies only committed data and makes unavailable status invisible. `StatusPanel` remains mounted with `v-show` to retain trailing-bar memory.
- The current HUD visibility matrix hides the dock in dialogue and creation. An older paragraph in the vitals data rule still claims dialogue behaves as exploration. The replacement requirement removes that contradiction without changing the matrix or actual gates.
- Under possession, the presenter already reads owner resources/conditions while exposing the controlled actor identity. Provenance must use the same `status_source`, without joining equipment from the controlled host or another panel.

## Goals / Non-Goals

**Goals:** A small authoritative source contract at the deterministic read boundary, with one frontend attention predicate and truthful equipment labels in existing condition details. Tests establish effects parity and independent warning attention with synthetic state.

**Non-Goals:** No severity downgrade, condition filtering, balance edits, persistent source history, new equipment-settlement behavior, polling, attention timers, dismiss controls, special content exceptions, compatibility path, or migration. Canonical persisted consequences keep their current attention even if earlier gameplay involving equipment helped cause them.

## Decisions

### D1. Carry one provenance object and derive attention from it

Every v3 condition requires `provenance` with exactly `kind` and `equipment_sources`:

- `kind` is `equipment`, `non_equipment`, `mixed`, or `unknown`.
- `equipment_sources` is a stable item-key-sorted, duplicate-free array of at most eight objects, each exactly `{item_key, label}`. Item keys use the existing stable identifier contract (1..64 characters); labels come from the item registry and contain 1..128 Unicode code points. Eight covers the canonical three singleton slots plus five accessories.
- `equipment` and `mixed` require a nonempty array; `non_equipment` and `unknown` require an empty array. Unknown sources never invent a label or falsely assert equipment-only causation.

`equipment` means the active condition has no independently matching non-equipment source in this read. `mixed` means equipment contributes to a relevant current input while the same condition remains independently active without equipment. `non_equipment` means no equipment contribution to that condition's current matching inputs. `unknown` means attribution cannot be proven from otherwise readable state.

The client counts a condition only when severity is warning/harmful/critical and provenance kind is non_equipment/mixed/unknown. No additional `visible` or attention boolean duplicates these facts. Global severity continues to determine icon shape, colour, and full-status wording.

Reject missing/malformed provenance at protocol adoption rather than supporting legacy severity-only payloads. Conservative attention for the valid `unknown` kind is a domain classification, not a compatibility fallback.

### D2. Verify attached instances from existing ownership facts

Build the required attached-instance map once from the same normalized worn mapping used by equipment settlement. An active cache entry is equipment-owned only if its exact instance key, logical definition, and cached `source_key` agree with that map. Ordinary instances are non-equipment even if they share the definition or carry an item-looking source key. An attached-looking orphan or inconsistent ownership record is unknown, so it cannot hide an independent warning. Existing malformed required status data still raises `StatusQueryError` and becomes unavailable; no new repair or handler mounting is introduced.

Keep buff rows per instance, including independent and attached instances of the same definition, with their existing durations. Do not collapse by code, change stacking, or expose the private cache key on the wire. The frontend must preserve duplicate-code rows using local row identity for Vue keys, tooltip targets, and overflow selection, since a code denotes a definition rather than a unique instance.

### D3. Compare current matches with an equipment-free read context

Keep the actual effective-context matches as the sole source of condition membership and adjustment values. In the same read assembly, build one in-memory comparison context over the same captured state, using stored exposure without the worn bias, no worn-item facts, `dual_wielding=false`, and active **logical definition keys** reconstructed after removing only proven attached instances. Preserve independent instances, skills, grants, unrelated sexual state, and all canonical values. Unknown instances remain in the comparison so uncertainty cannot suppress attention.

Run the existing `matched_combat_modifiers` evaluator once for that comparison. It supplies comparison rule IDs solely for provenance; its adjustments never replace actual values and comparison-only matches never become visible conditions. This is bounded reuse of the rule evaluator, with at most two evaluations per assembly and no per-item trial removals or parallel gameplay formula.

For each actually matched rule, identify the equipment inputs its existing predicate consumes: a changed effective exposure field uses worn nonzero-bias contributors; `buff_active` uses verified attached sources for that definition; `equipment_worn` uses the named worn item; a true dual-wielding predicate uses the worn weapon pair. Only consumed equipment inputs count. Exposure sources are listed only when the clamped effective level differs from the stored level; saturation or net-zero bias does not create an equipment contribution. A rule matching without equipment keeps independent attention, yielding mixed when consumed equipment inputs also contribute and non_equipment otherwise. A rule absent from the comparison and supported by proven consumed equipment inputs is equipment. Incomplete proof yields unknown. A state prerequisite combined with required equipment remains equipment-dependent when that state alone does not match the same rule.

Resolve source labels through existing registry/accessor ownership. Any small pure contribution helper belongs beside the existing equipment accessors, so status does not introduce a second rulebook reader. Never remove/re-equip real gear or reevaluate via a facade that lets the matcher restore live worn facts through its defaults. Both contexts explicitly supply the stored-skills facade and their own worn/dual-wield facts.

At stored 中等 plus synthetic +1 exposure bias, the warning at 高 is equipment-dependent. At stored 高 plus +1, the same warning is mixed and still requests attention. At stored 極高 plus +1, clamping leaves the input unchanged; the warning is non_equipment and still requests attention. None changes stored exposure or the actual adjustment bundle.

### D4. Preserve committed visibility and detail surfaces

Change only the condition term in `isVitalsVisible`. Combat, depleted numeric resources, and derived low HP retain their existing terms. Existing availability and dialogue/creation gates stay outside that term and retain precedence. Full-health equipment-only adversity remains in `status.conditions`; `ConditionChips` receives the entire list whenever the dock is otherwise visible. The complete character-status drawer keeps all conditions even when the dock is hidden.

Extend the existing shared condition-detail text with registry-backed equipment labels for equipment/mixed kinds, an independent-source qualifier for mixed, and a neutral source-unavailable statement for unknown. Use the same source text for tooltip, overflow detail, accessible name, and full-status detail. Keep severity words, exact values, durations, and existing glyphs. Do not require the character/equipment panel to be available to disclose a source already supplied by status.

Equip/unequip, independent buff changes, and stored-state threshold changes publish through existing committed snapshot/update paths. There is no optimistic source edit based on an action result. A same-code condition whose kind changes must replace provenance atomically with the accepted status panel; stale revisions and retired epochs retain their current rejection behavior. Existing focus rescue handles the transition from independent attention to equipment-only attention before hiding the dock, and mounted vitals keep trailing memory.

### D5. One unreleased clean cutover

Advance status only to schema version 3; keep envelope protocol version 1, all other panel versions, and the common unavailable shape. Registration continues to consume the presenter-owned constant. Mirror v3 in the browser panel allowlist and exact validator, including unavailable-form version checks. Update all existing producers of test/story status and condition payloads, including browser support and possession coverage. Remove the obsolete severity-only visibility comment and legacy condition fixtures rather than adding defaults or aliases.

The presenter/frozen-model boundary must reject invalid provenance before emission using the repository's existing model/error patterns; there is no existing separately named `status_panel.py` server validator to duplicate. Browser validation enforces the wire shape and cross-field bounds. Parity tests establish the registered version and valid/invalid payload agreement.

## Risks / Trade-offs

- A second matcher call adds bounded work. Capture source inputs once per read and reuse one comparison for all rows; retain actual match/breakdown parity tests.
- Source-instance confusion can hide a genuine debuff. Verify the existing ownership triple, preserve independent logical definition keys, and test same-definition coexistence plus orphan metadata.
- Duplicate codes can select the wrong tooltip. Test both attached and independent instance rows through visible and overflow detail paths without changing gameplay condition codes.
- Specification drift exists for dialogue and status version. Replace the full touched requirements with the current mode matrix and v3 contract, leaving unrelated capability behavior intact.
- Historical causality is unavailable in stored snapshots. Document that boundary and retain independent attention for persisted consequences; do not expand into provenance event history.
- Yuna's baseline warning remains. Use a synthetic saturated-exposure fixture as acceptance evidence and never alter her preset to make a HUD test pass.

## Verification Plan

Extend existing backend status-query, status-boundary, equipment-attached-buff and presenter tests with synthetic registries. Assert canonical Attributes and handler absence before/after repeated reads, actual combat/breakdown adjustment parity, ownership labels, logical-definition projection, mixed and unknown behavior, and possession source consistency. Extend Node protocol/parity and Vitest visibility/detail/store tests for v3 exactness, duplicate codes, gates, equip/state revisions, stale messages, focus rescue, and retained trail memory. Add or extend one focused managed browser journey for hidden-dock/full-status disclosure and a revealing trigger, registering any new methods in the existing shard manifest. Implementation runs focused tests and the contract gate; complete browser/evidence suites remain CI-owned.

## Rollout

Ship the server presenter and browser bundle together. No stored records change and no migration runs. A code rollback restores the previous presenter and browser together. Normal protocol-version rejection handles mismatched bundles; no v2 reader is retained.
