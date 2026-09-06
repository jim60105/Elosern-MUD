# Tasks: webclient-lore-codex-panel

## 1. Presenter

- [x] 1.1 New `web/webclient/presentation/lore_codex.py` building the version-1 available form from
  `list_discovered(actor)`, grouping into all eight `CODE_CATEGORIES` in mapping order — always all
  eight, never a subset and never reordered.
- [x] 1.2 Category labels: reuse the existing `CATEGORY_LABELS` mapping from `commands/lore.py` by
  promoting it to a shared location so the command surface and the panel cannot disagree.
- [x] 1.3 Entries: `key`, `title` (the card's display name, falling back to the key exactly as the
  `lore` command does), and `card` as an ordered `{name, value}` list straight from `lore_card`.
- [x] 1.4 An entry whose registry key no longer resolves (`LoreKeyError` / `LoreCategoryError`) is
  omitted; the rest of the codex ships; the stored record is not rewritten.
- [x] 1.5 `count` per category and `discovered_total` derived from shipped entries only — never from
  registry sizes.
- [x] 1.6 Host independence and read-only isolation asserted by construction: no host, registration,
  schedule, or room is consulted, and no reveal or record write occurs.

## 2. Validator

- [x] 2.1 Exact-shape validator: panel key set; exactly eight categories in mapping order; per-group
  key set; per-entry key set; per-card-field key set; code-point bounds on every string; `count`
  equals the entry list length; `discovered_total` equals the sum of counts.
- [x] 2.2 Declare and enforce a maximum entries-per-category, a maximum total entries, and a maximum
  card fields per entry.
- [x] 2.3 Close with the shared `MAX_CANONICAL_JSON_BYTES` envelope guard, failing closed — never
  truncating and never paginating.
- [x] 2.4 Reject lone surrogates in every string field.

## 3. Degradation

- [x] 3.1 A `LoreRecordError` raises `PanelUnavailableError` so the registry emits the common
  unavailable form; no partial entry list, no reset, no rewrite of the stored record.

## 4. Registration and push

- [x] 4.1 Register the panel in `web/webclient/presentation/registry.py` with its own unavailable
  reason pair.
- [x] 4.2 Mark dirty and push when `record_lore_reveal` records a NEW entry; a repeat reveal, which
  the writer treats as a no-op, pushes nothing.

## 5. Client mirror

- [x] 5.1 Add the `lore_codex` validator to `web/static/webclient/js/elosern/protocol.js` mirroring
  the exact Python bounds.
- [x] 5.2 Add the panel entry to the `webclient-vue-application` protocol mirror table.
- [x] 5.3 Extend the dual-direction parity test to cover the new panel.

## 6. Tests

- [x] 6.1 Shape tests: two-discovery serialization with all eight groups present in mapping order;
  empty codex available with every group empty; exact key sets at every level; `count` and
  `discovered_total` consistency.
- [x] 6.2 Non-disclosure tests: an undiscovered sibling entry is absent entirely; the payload carries
  no registry total, denominator, ratio, or placeholder.
- [x] 6.3 Card-fidelity test: a serialized card equals `lore_card` output field-for-field in declared
  order.
- [x] 6.4 Vanished-key test: a recorded entry absent from its registry is omitted, the rest ships,
  and the stored record is unchanged.
- [x] 6.5 Read-only test: building twice leaves `db.lore_discovered` unchanged with identical
  serializations.
- [x] 6.6 Host-independence test: a room with no NPC still yields the full codex.
- [x] 6.7 Degradation tests: a malformed record hides the whole panel; the stored record is unchanged
  afterwards.
- [x] 6.8 Bound tests: exceeding a declared bound or the envelope raises rather than truncating.
- [x] 6.9 Push tests: a new reveal pushes; a repeat reveal does not.
- [x] 6.10 Client-mirror rejection tests: ninth category, reordered categories, extra entry field,
  extra card-field key.
- [x] 6.11 Annotate with `covers_requirement` against the new requirement IDs; update
  `.github/evennia-shards.json` in the same change.
- [x] 6.12 Run the observability lint plus the focused presentation, protocol-parity, and lore test
  modules in the same batch.
