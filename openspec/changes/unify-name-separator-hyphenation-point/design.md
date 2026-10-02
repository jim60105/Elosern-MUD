## Context

Two separator conventions coexist in authored sources (verified census, node_modules/dist/.static/
vendored bundles/`__pycache__` excluded): U+00B7 `·` (237 py, 229 webapp, 249 docs, 43 openspec/specs)
is the registry/content convention — NPC names (瑪爾特·金秤), item names (暗影鋼刀·影), dialogue
prose, webclient UI strings (同伴 · 隊伍) — while U+30FB `・` (89 py, 20 webapp, 47 docs, 6
openspec/specs) is the namegen-pipeline convention, pinned in the `namegen-corpus-registry` and
`npc-name-generation` main specs and in codepoint-pinning tests. U+2027 `‧` currently has zero
authored uses. See proposal.md for motivation; the delta specs under this change pin the target
literals.

The composition path is narrow: one constant `world/lore/names.py:29 NAME_SEPARATOR` feeds
`compose_display_name` (:246), which is the sole composer used by `world/rules/namegen.py::roll_name`
and transitively the scenario-director `name_inspiration` bank; the fantasy-name-generator skill
asset duplicates the constant in `scripts/namegen.py:34`.

## Goals / Non-Goals

**Goals:**
- Exactly one middle-dot codepoint — U+2027 `‧` — in every authored string, comment, fixture,
  prompt-bank sample, and current (non-archived, non-design-doc) documentation.
- Requirement titles byte-identical across the eight touched capabilities so `covers_requirement`
  annotation IDs (`<capability>::<slugified-title>`) stay stable; only bodies, codepoints, and
  scenario literals change.
- Post-migration invariant: `·`, `・` (and `･` U+FF65) appear nowhere in authored tracked sources
  beyond the narrow D8 evidence allowances (historical records, this change's own artifacts, and
  escape-written negative assertions); prompt output contains no dot other than ‧.

**Non-Goals:**
- No validator, schema, or wire-format changes (‧ verified compatible; see Decisions D3).
- No rewrite of historical evidence: `openspec/changes/archive/**` and `docs/superpowers/specs/**`
  stay byte-identical, including the 2026-09-20 settlement-shops design doc:457 "Registry names use
  U+00B7" note, which this change supersedes (recorded here, per D5).
- No regeneration of the vendored upstream namegen corpus; only the `label` display field of the
  five `third_party/fantasy-namegen/data/packs/*.json` files (and the skill-asset copies) changes,
  since `NAME_SEPARATOR` is composed in code, never read from the corpus, and the `zh`/text
  fields contain no dots.
- Command surface untouched: `docs/game/commands.md` and `docs/game/command-reference.md` contain
  zero middle dots (verified); implementation re-confirms rather than edits.
- Gitignored artifacts (`.storybook-out/`, `web/static/webclient/app/dist/`, `tmp/story_settings/`,
  `.superpowers/`) are build outputs or scratch; they regenerate and are not hand-edited.

## Decisions

**D1 — ‧ (U+2027) wins over · (U+00B7) and ・ (U+30FB).** Owner decision, final. U+2027 HYPHENATION
POINT is the MOE-standard 間隔號 for 正體中文 names (教育部《重編國語辭典修訂本》〈標點符号用法·間隔號〉,
https://language.moe.gov.tw/001/Upload/FILES/SITE_CONTENT/M0001/HAU/h14.htm; https://zh.wikipedia.org/zh-tw/間隔號
lists U+2027 as the 中文分隔號/間隔號 recommendation). U+00B7 is the Western middle dot and U+30FB is
the Japanese nakaguro — both font-dependent renders in mixed CJK/Latin UI. Alternatives considered:
keep · (rejected: ad-hoc typographic convention, no normative basis) and keep ・ (rejected:
Japanese punctuation standard, wrong for 正體中文).

**D2 — Mechanic replace, single sweep.** The migration is a pure codepoint substitution over
authored text: `·`→`‧`, `・`→`‧`, across `world/**/*.py|yaml`, `web/webclient-app/**` sources,
tests, stories, Node gate tests, `web/static/webclient/js/**` (excluding `app/dist/`),
`.agents/skills/fantasy-name-generator/**`, `third_party/fantasy-namegen/data/packs/*.json`
`label` fields, and `docs/lore/**`, `docs/design/**`. No semantic edits beyond the pins enumerated
in tasks.md. Rationale: any hand-curated per-site review of 1,700+ sites is slower and noisier than
a scripted sweep with a fail-closed residue scan.

**D3 — No validator changes.** Verified with `unicodedata`: ‧ is category Po, `isprintable()`,
non-whitespace, and not among the reserved separators `|{}/:` — it passes `validate_npc_name` /
`validate_npc_title` (`world/rules/npc_identity.py`), `character_creation._validate_name`
(`world/rules/character_creation.py:252-266`), and the art subject-key reserved-separator rules
(`world/art/subjects.py`). The U+3000 full-width-space ban (display-composer reserved) is
unaffected. Implementers MUST NOT touch these validators.

**D4 — Delta specs keep titles verbatim.** The "middle-dot separator" requirement titles are the
anchors for `@covers_requirement` IDs; only body text, codepoint names, and scenario example
strings change. Census widened the delta set from the two pinned namegen requirements to eight
capabilities because literal `·`/`・` strings appear in six additional capabilities'
requirement/scenario text (webclient UI copy, skill boon labels, church/quest NPC literals).
Post-migration code would contradict those literals, so they are modified requirements, not
implementation details.

**D5 — Supersession recorded in this design doc.** `docs/superpowers/specs/2026-09-20-settlement-shops-design.md:457`
("Registry names use U+00B7 `·` (the authored convention), not the generator's U+30FB") is the
written statement of the losing convention. Design docs are historical decision records; the line
stays as authored, and this section is the forward-looking record: as of this change, registry names
use ‧ (U+2027), superseding both dots named there.

**D6 — Strengthen the negative assertion, on the right message.** `world/ai/tests/
test_scenario_director_prompts.py:179` currently asserts `assertNotIn("・", user["content"])`, but
the rolled name-inspiration bank lands in `system["content"]` (`prompt.py` renders it into the
system template; the rolled-name equality is asserted at :178) while user content is serialized
context. Post-migration the test asserts no non-‧ middle dot (`·`, `・`, `･`) in EITHER message,
with the three unwanted codepoints written as ASCII Unicode escapes so the residue scan (D8) never
sees literal old glyphs in the assertion itself.

**D7 — Rename the codepoint pin test.** `world/lore/tests/test_names.py:246
test_separator_is_the_katakana_middle_dot` becomes `test_separator_is_the_hyphenation_point` with
the pin flipped to `"‧"` / `0x2027`; the `@covers_requirement` decorator string is untouched
(title unchanged per D4). The skill-asset constant `.agents/skills/fantasy-name-generator/scripts/namegen.py:34`
flips too: it is the standalone authoring-tool duplicate of the separator, not the runtime
`name_inspiration` producer (the runtime bank rolls through `world.rules.namegen` →
`world.lore.names`), but a stale ・ there would keep the skill emitting mixed-dot names into
authored content, so it stays aligned with the registry constant.

**D8 — Residue policy separates display copy from codepoint evidence.** The fail-closed scan (tasks
§5) forbids `·`/`・`/`･` in authored display copy, with exactly three exclusions: historical
evidence (`openspec/changes/archive/**`, `docs/superpowers/specs/**`), this change's own artifact
directory (deliberate before/after quotes), and negative-assertion literals, which MUST be written
as ASCII Unicode escapes (`"\u00b7"` etc.) so they remain scan-clean and self-documenting.
Display strings are glyphs; assertions about codepoints are escapes.

## Risks / Trade-offs

- [Sweep misses a generated-at-runtime string (e.g. UI copy assembled from pieces)] → tasks.md
  includes a residue scan over tracked authored files plus a grep for the old codepoints in prompt
  output and rendered stories; tests that assert exact UI strings (`同伴 · 隊伍` etc.) fail loudly if
  code and spec diverge.
- [Sweep touches an out-of-scope file (archive, design docs, translit tables)] → the sweep list is
  allow-listed by directory; tasks.md ends with `git diff --stat` review confirming no
  `openspec/changes/archive/**` or `docs/superpowers/specs/**` paths changed.
- [Story/snapshot baselines drift] → stories are offline fixtures regenerated by the existing
  Storybook/Node gates; the sweep updates literal pins in the same pass, and the webapp test task
  runs the affected suites.
- [‧ renders narrower than · in some fonts] accepted trade-off: one canonical codepoint with MOE
  justification beats two drifting ones; font tuning, if ever, is a separate styling change.
- [Vendored corpus drifts from upstream] the `label` field is the only touched key and it is
  display copy, already Traditional-localized by this project's own edit; THIRD_PARTY_NOTICES
  semantics unchanged.

## Migration Plan

Pre-release project: no data migration, by the clean-cutover/reset assumption, not because strings
are never persisted. Runtime-composed names (`roll_name`, the inspiration bank) pick up ‧
immediately, and lore-registry DB mirrors are re-synced idempotently by `sync_all()`. But
authored identities do persist verbatim — quest occupants stamp `display_name` into `npc.db`
(`world/quests/scene_builder.py`), and the service-host contract is never-rename/never-retitle
(`docs/lore/settlement-locations.md:76`) — so existing persisted worlds are NOT upgraded by this
change and keep their pre-migration names until reset/reseed; the pre-release posture treats the
database as disposable. Rollback is `git revert` of the single migration commit.
