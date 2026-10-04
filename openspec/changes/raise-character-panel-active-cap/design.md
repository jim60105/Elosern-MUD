# Design — raise-character-panel-active-cap

## Context

The version-7 character-panel wire contract fixes two independent flattened skill-row bounds in
the `webclient-exploration-menu` spec's skill-grouping requirement (the requirement carrying the
panel's numeric row bounds; the top-level v7 requirement text's 32s belong to `traits`,
`equipment`, and `disguise` and are untouched here): 32 rows for `passives`, 32 rows for
`actives`. The server presenter (`web/webclient/presentation/character.py`,
`MAX_ACTIVE_ROWS`) and the JS wire validator (`web/static/webclient/js/elosern/protocol/panels/character.js`,
`CHARACTER_MAX_ACTIVE_ROWS`) enforce both, with `tests/test_exploration_parity_contract.py`
asserting the two literals stay equal.

The character read model (`_split_active_passive_keys` in
`world/rules/status_query/readers.py`) builds the active bucket from three sources: stored
`db.skills` keys, innate grants, and every act-catalogue skill unlocked via
`unlocked_act_keys_for` (`world/skills/sexual_acts`). The 66-entry `SEXUAL_ACT_REGISTRY` is
entirely ACTIVE-kind in `SKILL_REGISTRY` (verified live: 66/66), so the authorizable active-row
count grows with the act catalogue and already exceeds 32 for any progressed character. The live
failure (character 悠奈, pk 229: 61 active rows → `CharacterPanelError` →
`panel_presenter_failed` → internal-unavailable payload) is the designed fail-closed behavior
firing on well-formed data — the bound, not the data, is wrong.

## Goals / Non-Goals

**Goals:**
- A legitimately progressed character renders the available character panel.
- The actives bound stays a fail-closed wire guard with symmetric server/JS enforcement.
- Spec, presenter, JS mirror, parity contract, and traceability tests all agree on one number.

**Non-Goals:**
- No truncation, pagination, or overflow collapsing of skill rows (explicitly rejected).
- No `schema_version` bump (see D2).
- No change to `MAX_PASSIVE_ROWS`, traits/equipment/disguise bounds, category-group bound, or the
  byte envelope.
- No player-command surface change; `docs/game/commands.md` and `command-reference.md` untouched.

## Decisions

### D1: Raise `MAX_ACTIVE_ROWS` to 96 (headroom math)

The actives bound must sit strictly above the maximum active-row set the read model can
legitimately assemble, so the check keeps meaning "malformed payload" rather than "character got
strong." Upper-bound inventory at proposal time:

| source | rows |
|---|---|
| ACTIVE-kind act-catalogue skills in `SKILL_REGISTRY` (`SEXUAL_ACT_REGISTRY` fully ACTIVE) | 66 |
| innate grants (`flee`, `basic_attack`, enhancement innates) + stored/legacy + unregistered-key rows | small, double-digit ceiling |
| other registry ACTIVE skills the character can own (martial arts, elemental magic, enhancement, holy rite) | already inside the 66+innate character for progressed actors |

66 registry act skills alone already break 32. 96 = 66 + 30 headroom: covers the innate grants,
stored keys, unknown-key fallback rows, and future ACTIVE act skills without another amendment
cycle, while staying a tight, reviewable multiple of the old bound. The alternative "remove the
bound" was rejected: the check is the panel's only defense against a corrupted skill map
fabricating an unbounded payload, and fail-closed discipline is a contract property. Round 96
(also a clean power-of-two multiple, mirroring the 32 family) over e.g. 72 or 128 keeps the
rejection boundary far from today's legitimate maximum (61 observed) yet far below envelope
saturation.

### D2: `schema_version` stays 7 — no bump

The payload *shape* is byte-identical: same keys, same grouping rules, same ordering rules, same
row bounds. Only one numeric bound in the validation domain widens: every payload valid under
v7-with-32 remains valid under v7-with-96, and the JS mirror ships in the same deploy, so no
client can legitimately hold a snapshot the server would newly reject in a shape it cannot
parse. Bumping the version would force resync/rejection traffic for a change no conforming
client can observe as a structural break — the version gate exists for shape changes. The spec
delta therefore MODIFIES the requirement text (bounds are normative spec content) without
touching the "version-7" registration.

### D3: `MAX_PASSIVE_ROWS` stays 32 — explicit, not accidental

Passives cannot reach the cap: the PASSIVE side of `SKILL_REGISTRY` has 37 members total (37
verified live) and none arrive through the act-unlock flood path; the observed live passive count
for the worst character is 8. Widening a bound that is never approached would only enlarge the
attack/fabrication surface of a guard that works, so 32 stays — don't widen what isn't broken.
The delta spec states both numbers side by side so the asymmetry is deliberate and visible.

### D4: Envelope safety at the new bound (envelope math)

`MAX_CANONICAL_JSON_BYTES = 65,536` is unchanged and remains comfortably satisfied at the new
worst case. Reproducing the exact worst-case legal payload of
`test_worst_case_legal_payload_fits_the_envelope` (32 traits with maximal labels, 32 passives,
32 equipment rows, 32 displayed rows, maximal disguise description) with the actives section
maximal:

| actives rows | full payload canonical bytes |
|---|---|
| 32 (current test) | 24,407 |
| 96 (new bound) | 31,575 |

31,575 / 65,536 ≈ 48 % — the envelope check keeps real headroom, and the live 悠奈 panel is
10,332 bytes. The enriched-detail variant
(`test_worst_case_active_rows_with_detail_fields_fit_the_envelope` in `test_schema_detail_fields.py`:
96 rows each carrying `cost`, `target_spec`,
`usable_out_of_combat` and the five-rung `freeform_scales` ladder, over the minimal `_valid_panel`
sections) was measured the same way at 11,072 bytes at 32 rows and 31,552 at 96 — shorter fixture
labels keep it just under the label-maximal worst case, so 31,575 remains the binding worst case.
The envelope, not the row bound, remains the true payload ceiling; no envelope constant changes.

### D5: Why not truncation/pagination

Truncating actives would render an incomplete skill list that looks canonical — a silent lie on
a read-only display panel, violating its exact-read-only contract, and any pagination scheme
would be a shape change (schema bump, client work, request surface) for a display list that
fits in ~32 KB worst case. The user decision of record is: raise the flattened bound to 96, keep
fail-closed, no truncation/pagination.

### D6: Boundary tests pin both sides of the new bound

Constant-driven tests (they iterate `range(bound)` / `bound + 1`) move automatically, but the
change additionally pins the boundary explicitly: 96 accepted / 97 rejected for actives, 33
still rejected for passives, plus a presenter-level regression that a progressed actor whose
read model assembles a >32 active roster (e.g. 61 rows) renders `available: true` with every
row present — the scenario class that was broken. New/reworked boundary tests carry
`covers_requirement("webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel")`
(the amended requirement's literal ID) so `tools.spec_traceability` binds them to the amendment.

## Risks / Trade-offs

- **Bigger fabrication surface**: a corrupted skill map can now legitimately grow to 96 active
  rows before the guard fires. Mitigated by the byte envelope (D4) and the category-group bound
  (8 groups) staying at their values; the guard still rejects 97+.
- **Amendment pressure if the act catalogue grows past ~90 ACTIVE skills**: acceptable; a second
  amendment would then be a deliberate contract event, not a silent drift. 96 was chosen to make
  that unlikely, not impossible.
- **Client skew during rollout**: an old cached JS validator would reject a 33–96-row actives
  panel. Mitigated by deploy atomicity (static JS and Python ship together) and the protocol
  resync path; the parity contract test exists precisely to keep the pair from diverging in-repo.
