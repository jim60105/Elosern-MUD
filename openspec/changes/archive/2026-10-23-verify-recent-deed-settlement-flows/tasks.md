# Tasks

## 1. Replace seed-only fixtures with real settlement

- [x] 1.1 Replace the directly inserted narrative rows in `server/conf/tests/test_title_nomination_service.py` with synthetic objects and registries driven through a real purchase/delivery completion and a real adult resolver settlement, verifying the fixture creates no narrative event directly.
- [x] 1.2 Drive a real multi-round combat with repeated same-skill actions and its terminal outcome through the same composition, verifying the request retains the correct encounter group without hand-built evidence.
- [x] 1.3 Add the committed-state probe using the existing `TransactionTestCase` precedent, force-evicting `ObjectDB` and `Attribute` caches and reading a fresh production instance, verifying the ballot and title-grant results survive reload.
- [x] 1.4 Verify the fixture cleans synthetic data, registries and clock scope and uses fixed seeds with no live model or network service.

## 2. Prove the real composition boundaries

- [x] 2.1 Replace only the external transport with a fake that returns exactly five bounded candidates citing IDs captured from the rendered request, verifying selection, form filters, citation validation and ballot persistence run unchanged.
- [x] 2.2 Inject failure after real gameplay, title award and evidence writes but before each owning outer commit, including the nested quest writer, verifying gameplay state, title collection and equipped state, awards, events and projection work restore durably and in warmed caches.
- [x] 2.3 Use a valid five-candidate late result while another nomination is in flight or a ballot exists, verifying suppression comes from the ballot/admission guard rather than invalid output shape and the in-flight slot is released.
- [x] 2.4 Verify empty material, disabled profile, transport failure and malformed output each leave no ballot and no decline cooldown while leaving gameplay playable.
- [x] 2.5 Verify privacy controls in the real flow, including an untouched adult recipient and an unrelated character's private fields, and confirm transcript provenance retains cited source IDs without credentials.
- [x] 2.6 Replay committed settlement notifications instead of re-invoking gameplay owners, verifying replay creates no additional occurrence and preserves original award results.

## 3. Repository bookkeeping

- [x] 3.1 Update `.github/evennia-shards.json` for any added or moved test module and verify `tests.test_evennia_test_optimization_contract` passes locally with the test settings file.
- [x] 3.2 Update documented testing/traceability guidance and add substantive `covers_requirement` annotations for the requirements this change establishes, verifying `uv run --locked python -m tools.spec_traceability check` passes.
- [x] 3.3 Remove obsolete seed-only assertions whose claimed boundary moved to the new flow rather than leaving duplicate claims.
- [x] 3.4 Run the smallest focused labels for the replaced tests plus `uv run --locked python -m tools.contract_gate`, verifying no local command exceeds the ten-minute budget.
