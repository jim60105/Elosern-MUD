# Proposal

## Why

The balance-data cutover in `afa974d4` left shipped content identities and prose embedded in current requirements and approval-style tests. Valid roster, personnel, epithet or shelf edits therefore still require contract edits even when no mechanic changes.

## What Changes

- **BREAKING** Replace delivered per-species requirements with registry-derived monster integrity and composition contracts. Species, variants, kits and delivery status become authored data; no new species or ability is delivered.
- **BREAKING** Consolidate the six NPC inventory-slice requirements into a complete live-source-derived profile/dialogue guarantee. Generalize capital/village personnel declarations and personal-name examples while preserving place/settlement contracts.
- Read the starter epithet's display and origin from the existing `STARTER_EPITHET` declaration. Retain first-ever reward-claim timing, atomic banking, auto-equip and notification behavior; leave guild titles, clergy ladder and category tabs unchanged.
- Generalize equipment/item roster membership and shop assortment rules. Preserve reference closure, equipment quality, unstocked-item validity and non-sellable precedence. **Explicit exception:** the six E-S military sword/armor pairs stay named because guild examiner content depends on them; examiner-facing statements stay named.
- Replace bestiary verbatim prose assertions with a machine-checked keyed documentation relationship, complete species/variant coverage and public/private separation.
- Retarget every annotation whose requirement is removed or renamed in the same implementation, backed by assertions establishing the replacement contract.

## Capabilities

### New Capabilities

None. Existing owners retain their contracts.

### Modified Capabilities

`monster-species-registry`, `monster-resource-abilities`, `monster-action-policy`, `monster-individual-construction`, `npc-profile-registry`, `npc-identity-titles`, `sample-city-altoria`, `altoria-hospitality`, `altoria-learning-and-exchange`, `altoria-crown-and-watch`, `altoria-sanctum`, `ciaran-village-commons`, `ciaran-village-crafts`, `ciaran-village-commerce`, `guild-registration`, `title-system`, `quest-reward-settlement`, `equipment-effects`, `commerce-assortments`, `shop-economy`, `lore-registries`, `place-attendant-hosts`, `lore-item-catalog`, `human-guild-hosts` and `webclient-contextual-hud`. The exhaustive requirement-level disposition is in `scope-inventory.md`.

`military-equipment`, `guild-exam-restrictions` and `guild-rank-exams` are retained dependencies, not modified capabilities. The named military exception creates no delta for them.

## Impact

One planning-only change on `master`; implementation needs the serial packages in `design.md`. No code, existing proposal, main spec, archive or compatibility/save migration is changed by this proposal. Every other non-archived `openspec/changes/*` directory is read-only both now and for this proposal's implementation tasks. Places/settlements, clergy titles, skill names, sexual-act catalogs and balance values are excluded.

## Approval decisions

Approval must explicitly cover D1 (deferred monster owners must later rebase their incompatible deltas), D2 (live-registry-derived NPC coverage replaces all six slices, including editorial rewrite evidence), and D3 (removed traceability IDs are retired and meaningfully retargeted in the same implementation). Full consequences and exact pending blocks appear in `design.md` and `pending-couplings.md`. Approval of this proposal grants no approval to implement or edit a deferred monster proposal.
