## 1. Committed image set

- [ ] 1.1 Author or license six images — `man`, `woman`, `boy`, `girl`, `elder`, `monster_anon` — matching the project's approved visual style, with no sexualized content in any of them
- [ ] 1.2 Encode each to a bounded-size WebP (declare the bound as a constant used by the contract test) and commit them to `web/static/art/defaults/`
- [ ] 1.3 Confirm `.gitignore` still excludes `server/.art/` and that no other art file becomes tracked by this change

## 2. Fallback module

- [ ] 2.1 Create `world/art/gallery_fallback.py` with the closed key vocabulary, the defaults directory constant, the per-key face-rect map, and the declared size bound
- [ ] 2.2 Add the band table: monster subjects to `monster_anon`; elder, child, and adult apparent-age bands, each mapping female/male to one key and every other sex to that band's ordered pool
- [ ] 2.3 Add `fallback_key_for(subject, entity)`: declared registry key first, then the band table, then a stable hash of the subject's full key into the band pool; fail closed to the adult band on missing or malformed sex or apparent age
- [ ] 2.4 Add `fallback_url_and_rect(key)` returning the `/art/defaults/<key>.<ext>` URL and the key's rectangle (shared default when the key has no entry)
- [ ] 2.5 Keep the module free of `world.ai`, `ollama`, `llm_client`, and `world.art.connectivity` imports and free of every write

## 3. Registry declarations

- [ ] 3.1 Add an OPTIONAL fallback-key field to `PlayerPreset` in `world/lore/player_presets.py`, defaulting to unset so every existing preset stays valid
- [ ] 3.2 Add the same optional field to the NPC tier and monster tier registries
- [ ] 3.3 Validate a declared key against the closed vocabulary at registry construction time so a typo fails loudly at import

## 4. Seam implementation

- [ ] 4.1 Implement `world/art/gallery_match.py::fallback_for(subject)` against the module, returning the URL and rectangle pair
- [ ] 4.2 Emit one `gallery_fallback_used` info event per use with `subject`, `kind`, and `key` in `context`, through the `world.observability` facade
- [ ] 4.3 Write nothing: no record, no card, no store copy

## 5. Tests

- [ ] 5.1 `world/art/tests/test_gallery_fallback.py`: a declared key wins over the band rule; an invalid declared key fails at import
- [ ] 5.2 Band coverage: adult, child, and elder ages against female and male sexes each resolve their band's key; monsters resolve `monster_anon`
- [ ] 5.3 A sex outside the pair hashes into its band pool, and repeated resolution is identical
- [ ] 5.4 Determinism: the same subject resolves the same key across fresh module state (simulated restart)
- [ ] 5.5 Fail-closed: missing and malformed sex and apparent-age values resolve the adult band without raising
- [ ] 5.6 Contract test: every vocabulary key has exactly one committed file within the size bound, and every file in the defaults directory is a vocabulary key
- [ ] 5.7 Integration: a subject with no card and no `done` classic asset resolves the fallback URL and rectangle, logs one `gallery_fallback_used`, and creates no record or card
- [ ] 5.8 Integration: the `/art/defaults/<key>.<ext>` route serves each committed image with its media type
- [ ] 5.9 Annotate new tests with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`

## 6. Verification

- [ ] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art world.lore web.tests`
- [ ] 6.2 `uv run --locked python -m tools.observability_lint check`
- [ ] 6.3 `uv run --locked python -m tools.spec_traceability check`
- [ ] 6.4 `openspec validate gallery-builtin-fallbacks --strict`
