# Design

## Context

See `proposal.md` for motivation. The baseline is `afa974d4`. Frozen lore registries already own keyed species/variants, place staffing, NPC profiles, `STARTER_EPITHET`, items, assortments and persistent qualified adventurers. Shared construction, action, service synchronization, first-claim and trade boundaries already exist. This change replaces content approval contracts; it does not deliver new game content.

Read precedents: `AGENTS.md`, `docs/development/spec-test-traceability.md`, the archived `2026-10-10-flexible-game-data-test-design` design/test-migration/review-disposition, and both monster-resource design documents dated 2026-10-09/10. Their test-role distinction remains binding: synthetic mechanism tests have independent expected outcomes, registry contracts validate current reference relationships, and proportional production smokes observe real consumers. Documentation is English with canonical Traditional Chinese content identifiers.

## Goals / Non-Goals

A valid content identity/prose/membership edit, with its required authored references, must not require changing a general requirement. Invariants must reject broken records and relationships rather than freezing a approved roster under another filename.

No compatibility aliases, save migration, new balance values, content addition, pending monster ability delivery or shared engine redesign. Place keys/order, settlement descriptions/culture, topology and institutional prohibitions stay fixed by their current contracts. The clergy ladder, fixed guild titles, six tabs, skill catalogs and sexual catalogs remain unchanged. Historical headings retained by MODIFIED deltas are parser/traceability identities, not statements that their old rosters remain authoritative.

## Decisions

### Family 1: Monster identity is registry membership

Keep immutable key identity, species/default-variant ownership, public projection, habitat-not-spawn authority, independent tier/grade bounds, deterministic construction and atomic committed reload. Remove species-specific ability/policy/construction requirements and old first-batch tables. Kit presence, skill/effect/behavior references, active/passive order and authored eligibility determine executable configuration. Missing special kits continue to use innate actions and tier defaults, without text-derived powers or synthetic placeholders.

Add an immutable per-variant `profile_required` declaration so completeness does not silently become optional when the old twelve-row guarantee disappears. Populate it true for all current shipped variants that currently require complete profiles/grades; preserve their exact existing values and delivered/undelivered kits. Optional absent profiles retain existing fallback, observability and bounds. Validate the declaration's type and required presence at load. The declaration expresses an obligation, not another list of approved variant keys. No separate delivery-status table is needed: delivery follows validated authored kits.

The generic resource contracts retain physical contact, eligibility and battlefield gates, invocation-local hit evidence, capped actual-removal transfer, effects-before-cost ordering, either-axis affordability, miss/absorbed/critical/defeat boundaries, audience-specific riders, self guard, refresh/expiry and rollback. Exact coefficients/costs/magnitudes remain current rulebook data. Synthetic tests keep independent arithmetic. Production representatives cover the three delivered composition shapes, selected from kit composition rather than a new species allowlist; reference/real-construction checks cover every current variant. Do not clone the entire mechanism battery per species.

Rejected: relocating closed six/twelve-row approval tables into a fixture; dropping completeness; pretending a narrated deferred ability is delivered; species branches in action resolution.

### Family 2: Personnel is authored identity; completeness is universal

Use current place declarations for host identity, profession, sex, race/subrace and presence/absence, with existing all-or-none host fields, key validation, ages, components, source provenance and no-reset reuse. Keep every capital/village place and exterior assertion. A personnel edit may change who staffs an existing location or declare it hostless; it may not change that location's purpose or grant prohibited institutions/work. Each declared host must support the existing location's permitted dialogue/service purpose. Persistent examiner qualification selects people from current branch/target bindings; normal bases, gear references and lineage prerequisites validate without personal-name tables. Their routes must use connected residences and actual Exits, not teleportation. Examiner military/rank restrictions remain untouched.

**D2, user approval required:** remove all six inventory-slice requirements and replace them with the generic live-source completeness requirements. First derive actual sources independently using `derive_shipped_sources` from places, dialogue tables, persistent people/qualifications, companions, offline templates and shipped imports. Compare actual versus inventory in both directions; do not iterate only inventory or hard-coded owner labels. Then check every actual host's individual bounded card, age, profile/service identity, voice, sole dialogue greeting, misunderstanding reply and table ownership, and every actual persistent person's profile/offline voice/provenance. A new host under a previously unseen owner must enter coverage automatically. Missing/stale owner, host, table or profile must fail with a source-specific diagnostic.

All six source slices remain content modules; no module renaming or registry-assembly redesign is needed. Replace fixed `OWNER_LABELS`, 25-host/3-person/28-profile counts and slice-only wrappers with registry-derived coverage. Keep unique keyword labels within a table, but allow different hosts to legitimately share the same service keyword vocabulary. Voice distinctness and card/dialogue agreement require an editorial review ledger indexed by actual source identity, including all affected greetings and keyword responses. That ledger records what reviewers inspected and why it fits the individual; it is not a expected-prose fixture and must be updated for new/changed content. Automated nonempty/shape checks do not prove a historic rewrite or literary individuality.

Replace personal-name examples in identity/import/scene/HUD contracts with explicitly synthetic identities. Those paths preserve formatting, collision, rollback and truthful portrait behavior. No historical personnel identity comparison remains as a generic consumer oracle.

### Family 3: Starter epithet values are one frozen declaration

Retain `STARTER_EPITHET` as the existing single starter declaration, not a new registry/framework. Display and origin basis remain authored frozen data. The first-ever successful guild reward claim, not registration or a particular quest key, banks that data through the regular writer in the claim transaction. Preserve dedupe, empty-slot-only auto-equip, title snapshot/rollback and CLI/dialogue/web notification echo. 「獲得異名：」 is presentation grammar; the following display is data. Guild title 「F級冒險者」 remains the named guild contract.

Behavior tests patch an explicit synthetic starter declaration at the actual import seam and independently assert its display/origin and state/notification. Current-data checks validate immutable nonempty bounded display/origin metadata without expecting 「南門新客」. Browser seeds and protocol/UI fixtures use explicitly synthetic epithet text, and test/freeze documentation must describe their roles accurately. No existing character's banked epithet is renamed or re-granted by a content edit.

### Family 4: Item membership and shelves are relationships

Use current immutable items, effect bijection, declared slots/kinds, price bands, assortment membership and existing place additions/removals/scales/overrides. Preserve stock, wallets, acquisition progress, affinity, local-service gates, persistence and atomicity. Complete equipment may remain unoffered; a shop listing is not an entitlement inferred from registration. A shop's union plus additions minus removals is authoritative. Within-shop duplicate offers reject absent precedence; sharing an item between shops is valid. Remove historical item/shop counts and capital/village approved union snapshots, not the underlying place inventory or balance bounds.

Preserve shop-purpose restrictions through small immutable eligibility declarations on assortment lore (`allowed_item_kinds`, and where relevant `allowed_equipment_slots`), validated against each resolved item. They express shelf classification rather than another list of expected item keys. No fixed two-accessory-bundle count, fixed capital union or cross-capital uniqueness rule remains. Existing location/shop purpose descriptions remain unchanged; every offer must satisfy its authored eligibility policy.

Move Church equipment subset membership from named spec/test lists into immutable item-lore `liturgical_role` with closed values for vestment/emblem and sanctuary device (or no Church role). Mutable effect rules cannot assert/reassign roles to borrow exemptions. Keep the doctrine's nonnegative exposure/pleasure and healing constraints, positive device pleasure, vestment healing-or-immunity and allowed ordinary combat trade-offs. This is only equipment classification; clergy title/skill catalogs and sexual act data do not change. Invalid role metadata or unsupported role/equipment relationships fail load. Content reviewers own legitimate classification changes; an effect mutation cannot opt out.

Starting-kit item selections are also equipment membership data. Keep existing human subrace keys, commoner rarity-profile equality and noble inherited-arm quality. Retain general kit existence, equipment-only closure and wearable-set validation under their existing owner. Express lineage/quality eligibility as frozen kit/item metadata where it cannot already be derived from existing kind/rarity/slot data, without a named rejected-item blacklist. Preserve current starting selections; this change permits later valid edits, not new kit content.

**Named exception:** retain the six E-S military sword/armor pairs, their `military-equipment` requirements and examiner-facing `guild-exam-restrictions`/`guild-rank-exams` statements. Current persistent examiner equipment explicitly references the B/A/S pairs and E-S exam kits depend on the full family. The exception's reason is this examiner dependency, not that military items are inherently unsuitable for registry data. Keep their narrow tagged membership tests separate from generic item/effect/shop coverage.

Non-sellable item metadata outranks all offers, additions, overrides and price bands on both buy and sell. Keepsake-band offerings reject at load through every shelf route, without making held/inspectable keepsakes invalid. Independent synthetic cases establish refusal before any wallet, inventory, stock, progress or affinity writes.

### Family 5: Bestiary relationship checking without narrative pins

Keep authored public prose in the species/variant registries and editable reader-facing bestiary prose. Add stable machine-readable boundaries to the current publication sections of `docs/lore/bestiary.md`, not to historical approval appendices: species key, variant key and parent species key, plus links naming the public registry fields each current section documents. The index is derived by parsing those bounded sections, never from a parallel manually maintained expected-key table.

A pure checker takes registry projections and parsed documentation structure. It compares key sets both ways, validates uniqueness, parent ownership, public-field references, required field coverage and nonempty bodies, and checks kit-backed executable status as structured metadata. It rejects private-field references and private sections inside published boundaries. Display names and Chinese headings are not lookup keys. Default variants must appear as ordinary owned variants, not as invented documentation-only variants. Historical notes do not satisfy current coverage.

Positive and synthetic missing/duplicate/orphan/wrong-parent/missing-field/private-reference/status-mismatch cases test the checker. Rewording prose under valid boundaries must pass without changing a spec/test expected sentence. No normalized sentence, substring, approved prose fixture, source hash or disguised prose equality check survives. Programmatic structural checks do **not** claim to detect semantic contradictions between two freeform passages; indexed editorial review assesses ecological accuracy, ability limits and current versus historical narrative. This limit is explicit, not a fake text-understanding assertion.

### Traceability is part of the cutover

**D3, user approval required:** REMOVED headings retire their canonical IDs, and all 164 currently discovered annotation sites for the 61 affected requirements are inventoried in `scope-inventory.md`. During apply regenerate canonical IDs from the effective specs using `tools.spec_traceability list`; do not invent normalized IDs. Retarget each removed-ID annotation to the specific generic requirement it actually asserts, splitting tests when roles differ. MODIFIED headings retain IDs but need assertion review. Registry tests do not claim engine behavior just by loading data. Add direct positive/negative tests for every new contract; do not use a broad decorator as a coverage substitute. Python and JS annotations, freeze metadata, seed reasons and docs stay aligned. Acceptance includes a zero-stale-ID scan and a clean traceability check with no allowlist.

### Deferred proposal collision

**D1, user approval required:** this change removes four requirement names modified by each of the three deferred monster proposals. Their later application after this cutover cannot succeed without owner-authored delta refresh. `pending-couplings.md` gives all twelve broken blocks, eighteen old-shaped ADDED blocks, exact target mappings and the dependency/conflict matrix. Recommend the generalization cutover before their eventual refresh; there is no automatic queue dependency or permission to change them now. If a deferred proposal lands first, the applying owner must re-inventory the changed current requirements and update this change through the normal approval workflow before applying. Never preserve obsolete aliases solely to make stale deltas apply.

## Serial work packages

The locked one-proposal shape exceeds one engineer-day. Use seven approximately one-day serial packages within this change, each with a bounded reviewable deliverable. They are not separate proposals or independently syncable spec changes.

| Package | Deliverable | Depends on | Shared/conflicting surfaces |
|---|---|---|---|
| WP1 | Effective requirement/annotation inventory and test-role migration preparation, no discarded invariant | approval D1-D3 | all selected test decorators; test-data metadata |
| WP2 | Generic species/profile/kit contracts and all-variant integrity/construction checks | WP1 | monster registries, skill contract tests; all deferred proposals |
| WP3 | Shared composition suites and representative real consumer evidence; keyed bestiary checker/document boundaries | WP2 | monster action/effects tests, lore bestiary and author guidance |
| WP4 | Live-source NPC completeness, editorial ledger, generic personnel fixtures retaining topology | WP3 | profile/inventory tests, service roster/settlement tests, human hosts/HUD identity |
| WP5 | Starter epithet declaration-driven first-claim and surface fixtures | WP4 | reward/title, commands/web/browser seeds, annotation metadata |
| WP6 | Item/assortment/kit membership, shelf/doctrine data classification, non-sellable precedence; military exception | WP5 | item/equipment/shop/settlement tests, item metadata; examiner suite deliberately retained |
| WP7 | Whole cutover acceptance, traceability/metadata/docs completion and final CI evidence | WP6 | all selected contracts and test metadata |

No package may weaken tests temporarily and call the change complete. Main-spec synchronization and the implementation commit sequence belong to os-apply, not this planning session. Verify once after integrated work according to project gates; split suites by responsibility without concurrent verification storms.

## Migration plan and acceptance

`test-migration.md` gives concrete file/assertion/role changes. Keep shipped content values and runtime state unchanged. Add only the minimal frozen classification/obligation metadata required to replace named obligations. No live save migration or compatibility layer. Deployment rollback reverts implementation/spec changes together; no destructive entity rewrite is needed.

Acceptance: a valid content add/rename/retirement under each selected family, with references updated, passes generic checks without editing a spec; corresponding malformed relationships fail. Every registry-derived host/card/dialogue is covered, even outside old slices. Bestiary structure faults fail and wording-only edits pass. First-claim state and notification use a synthetic configured epithet across all surfaces with rollback. All listing routes respect non-sellable/keepsake precedence. Exact military pairs and examiner statements remain named. Every removed ID is retired with substantive replacements; unchanged location/clergy/skill/sexual/balance contracts retain coverage. Validate this delta, all main specs and all changes strictly; this proposal adds no failure beyond the three explicitly deferred monster proposals.

## Risks / Trade-offs

- Lost slice completeness → derive actual sources independently, prove both-way inventory equality, inject a new-owner host and omission faults.
- Self-fulfilling data oracles → separate registry relationship checks from synthetic mechanism arithmetic and committed real consumer evidence.
- Metadata opt-out → preserve all current required-profile/role assignments; freeze role ownership outside effect rules, and require content review for classification edits.
- Editorial quality mistaken for automated correctness → indexed review ledger plus explicit checker limits, no text pins.
- Stale delta/traceability breakage → D1 and D3 require approval and same-cutover acceptance; no edits to deferred changes here.
