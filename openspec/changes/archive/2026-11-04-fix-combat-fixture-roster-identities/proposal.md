# Proposal

## Why

The identity cutover left seven `Battlefield(...)` construction sites in two test modules using `fixture:` roster keys for actors with positive primary keys. The reported baseline at `11de2a59` has 12 conditional-damage errors and three skip-safety errors, preventing those tests from reaching their intended assertions.

## What Changes

- Migrate three conditional-damage construction sites to keys derived from `stable_actor_id` for their real `PlayerCharacter` objects.
- Migrate four skip-safety construction sites to distinct dbref identities for their explicit-pk doubles, and migrate the fled-state write to the same identity domain.
- Add focused controls in both existing modules for identity-safe construction, repeated display labels, and rejection of mismatched roster keys. Preserve damage, nonlethal, rollback, skip rejection, and registry-isolation assertions.
- Clarify the existing battlefield protocol requirement with executable construction scenarios. This records the current mechanism without adding executable production behavior or another requirement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `battlefield-action-context`: spell out canonical roster/team identity and mismatch rejection under the existing protocol requirement.

## Impact

Implementation is limited to `world/rules/tests/test_conditional_damage.py` and `world/rules/tests/test_skip_safety.py`. No production constructor is responsible for the reported errors: both modules construct the failing battlefields directly; `reconstruct_battlefield` already derives keys with `stable_actor_id`. The skip registry deliberately uses decimal pk strings, a separate domain that remains unchanged.

This is a single engineer-day fixture repair. No runtime feature, compatibility layer, migration, name fallback, `key:` path, shared fixture redesign, or second battlefield path is authorized. All nine archived regional-population changes remain untouched. Existing shard ownership remains exact because no module is added, moved, or renamed. Traceability uses the existing canonical battlefield requirement and preserves existing decorators.

## Evidence Boundary

The 15 baseline errors are supplied, already reproduced observations; this planning change does not rerun them merely to confirm the report. Inspection identifies their construction sites and a fled-key defect hidden behind the skip-safety constructor error. Implementation acceptance requires both focused module labels green, exact shard ownership, the contract gate green, and negative mismatch controls proving rejection is retained. Commands and expected observations are specified in `design.md` and `tasks.md`; no implementation success is claimed here.

## Dependencies and Conflicts

No active-change dependency exists (`openspec list --json` was empty). The archived `combat-individual-identity` cutover is an already-landed prerequisite. Potential code conflicts are confined to concurrent edits of the two named test modules; spec-sync conflicts are confined to the first requirement of `battlefield-action-context`. Regional-population scope is excluded.
