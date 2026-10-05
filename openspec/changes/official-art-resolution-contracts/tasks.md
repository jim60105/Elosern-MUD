## 1. Chain extension

- [ ] 1.1 Add the official-default step (after the classic asset, before the terminal seam) to `world/art/gallery_match.py` for both the character chain and the declaration-driven monster variant, and verify chain tests: runtime card/classic outrank official, nothing-runtime resolves the official default, an absent/unregistered reference falls through to the seam without a new diagnostic storm, and a populated snapshot changes nothing for monsters (no producer)
- [ ] 1.2 Keep chain purity — snapshot reads only — and verify a tripwire test proves official resolution performs no network call, filesystem write, enqueue, or record mutation across a hundred synthetic resolutions

## 2. Payload origin discriminator

- [ ] 2.1 Extend the origin vocabulary shipped by `builtin-silhouette-stage-fallback` with the `official` value on the official payload branch (and keep the decorative `fallback` field carried beside real images), and verify payload tests pin each branch's value and that a URL's presence never determines the discriminator
- [ ] 2.2 Build the official payload (fingerprinted URL, validated metadata-or-fitted rect, validated manifest stage when declared-and-valid else identity placement, name/identity fields, no paths/license/prompt text) and verify field-shape tests — including a non-identity manifest stage surviving to the payload — plus a not-generated status assertion against an untouched subject's gallery/asset state
- [ ] 2.3 Mirror the discriminator through both wire validator sides and the frontend portrait consumers for the art panel catalog and roster rows, and verify the dual-direction parity tests reject any payload accepted by one side only (contract gate run for the changed vocabularies)

## 3. Eligibility ordering

- [ ] 3.1 Prove eligibility runs ahead of official presentation in `resolve_character`/catalog dispatch, and verify a canonical-age-failing character with fully valid official content presents the truthful placeholder with no URL, rect, or subject key

## 4. Auto-generation suppression

- [ ] 4.1 Extend the `world/art/service.py` automatic-path guard with the official-satisfied condition (eligible reference + resolvable default) and verify: preset-born activation with official art enqueues nothing but keeps its named policy; unsatisfied/ineligible entities behave exactly as today; manual generation still works and the settled card then outranks the official default; a later directory update retroactively enqueues nothing

## 5. Verification

- [ ] 5.1 Run the package-adjacent chain/presenter/autogen tests, wire-parity tests, and contract gate once, confirming acceptance criteria 4 (shared bytes, independent choices — resolution half), 6 (update/restart preserves generated cards), and 7's fall-through half observable together
