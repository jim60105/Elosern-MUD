# Design: subrace-specialty-localization

## Context

Design document `docs/superpowers/specs/2026-09-12-human-subrace-lineage-rework-design.md` §4
(plus §1 defect 4 and §8) is the source of truth; every content decision below was settled with
the project owner and is transcribed, not re-decided. See `proposal.md` for motivation.

Current state: both creation surfaces are dumb printers of `Subrace.specialty` —
`commands/character_creation.py:191-192` interpolates it into the CLI prompt, and
`web/static/webclient/js/elosern/creation_menu.js:247` copies it into the menu item's
`description` (validated as a bounded string in `web/webclient/presentation/creation.py` and the
mirrored `protocol.js`, bound 256 code points). After Change 1 the five human values are zh-TW
verbatim from Change 1's delta; the three elf and seven beastfolk values are still English
sentences (`"Excels at archery and light magic."`, `"Agile assassins and scouts."`, …).

Constraints: no save-data compatibility layer (design §7); every `### Requirement:` heading name
stays stable so `@covers_requirement` slugs remain valid; the ten elf/beastfolk keys, names,
anchors, modifiers, and `vital_overrides` are untouched — only the `specialty` string values
change.

## Goals / Non-Goals

**Goals:**
- Replace the ten elf/beastfolk `Subrace.specialty` values with concise zh-TW prose faithful to
  each entry's `world_info.md` lore block and its `static_modifiers` tradeoff.
- Lock all 15 values with a registry-language contract in `lore-registries`, enforced by a
  behavior test in `world/lore`.

**Non-Goals:**
- Rewriting the five human specialty strings (owned by Change 1's delta; this change's
  requirement merely *covers* Change 1's output — that coverage is why Change 2 lands second).
- Any renderer, protocol, or shard-manifest change; renaming keys/fields/headings; translating
  `RaceProfile.description` or other prose fields.

## Decisions

**D1 — Server-owned prose, not renderer-side i18n.** The fix lives in the registry values, not
in the views. `creation_menu.js` is deliberately a dumb view layer under the project's
Python-vs-pnpm split (it already duplicates no label literals — see the sex-label scenario in
`webclient-character-creation-ui`, which mandates "no label literal duplicated in browser
code"); adding an English-key → zh-TW map in JS would recreate exactly the client-owned-label
problem that spec forbids, and the CLI surface would need a second copy. Alternative rejected:
rendering `common_name_zh` only — it drops the trait information both surfaces are built to show.

**D2 — Language rule enforced by a behavior test, not a load-time validator or a lint.** The
project already proves registry data invariants by test: the zero-sum stat-modifier contract is
asserted in `world/lore/tests/test_races.py` (`test_beastfolk_modifiers_sum_to_zero`,
`test_human_modifiers_sum_to_zero`, both `@covers_requirement`-annotated against the Subrace
requirement), not by `races.py` import-time code — the only load-time validator in `races.py` is
`_validate_static_tier_magic_bands`, which guards a cross-registry referential rule a player
could otherwise hit at runtime. A prose-language violation is an authoring bug with identical
blast radius to a non-zero-sum modifier, so it belongs beside those tests. Alternative rejected:
a registry-load assertion — it would run on every server boot to protect data that only ships
through a code review, and `tools.test_data_lint` is for test fixtures, not lore registries.

**D3 — The assertion rule is precise and exception-free: every specialty value MUST contain at
least one CJK ideograph and zero ASCII letters (`A-Z`, `a-z`).** All fifteen approved strings
(five human from Change 1 + ten new) satisfy it — none contains a single ASCII character; every
punctuation mark used (`。、（）`) is fullwidth. An "allow parenthetical lore terms" escape hatch
was rejected because zero values need it, and an exception list is a regression door: the bug
this locks out is precisely someone re-adding `(Fionnen)`-style Latin glosses into a player-facing
line. Item keys never appear in `specialty` (they live in `key`/`home_anchor_key`/kit fields), so
excluding "keys" from the sweep is unnecessary — the sweep is a plain regex over the fifteen
field values.

**D4 — Translation principles (what the ten strings encode).** Style mirrors Change 1's §3.3
pattern — identity + habit/aptitude + tradeoff — and quotes lore terms verbatim:
- Beastfolk name a **physique**, its habit, and the exact tradeoff their `static_modifiers`
  encode, matching `world_info.md`'s 「亞種數值傾向」 rationales (狼人 均衡/團隊, 貓人 敏捷/暗殺偵查 aptitude
  vs 纖薄, 熊人 力量/重型武器 vs 遲鈍, 兔人 最快/弓箭 vs 脆, 牛人 防禦/陣地戰 vs 緩慢, 虎人 高攻高速 vs
  紙糊防禦, 狐人 以體術換魔力 + 最接近施法者 + MP 50–70 底蘊). This follows §1 finding 2's praise of the
  beastfolk naming axis: a wolfkin may be a warrior or a merchant, so 貓人 prose says
  「擅長潛行偵查資質」-style aptitude, never 「是刺客」 occupational determinism.
- Elves name the clan's own village, affinity elements, and signature art per `world_info.md`'s
  三分支 block (翠綠森林村/光/弓術; 暗影谷村/火暗/刀術; 幽月谷村/全屬性/神之秘法), since elves have no
  documented stat skew — prose carries identity only, no mechanic claims.
- Canonical zh-TW terms stay canonical (黑暗精靈, 幻童精靈, 神之秘法, 陣地戰); vocabulary is Taiwan
  Traditional Chinese throughout (凌厲, 底蘊 — never simplified forms).
- Every string stays well under the 256-code-point protocol bound (longest ≈ 45 code points).

**D5 — Change 1 boundary is hard.** The five human strings arrive from Change 1's delta verbatim;
the pinned-verbatim scenarios in this delta split accordingly (Change 1's scenario pins the human
five, this change's two new scenarios pin the elven three and beastfolk seven), and the ADDED
language requirement covers all fifteen. The MODIFIED Subrace-registry requirement is authored
against Change 1's **post-archive** main-spec text, carrying over its body and every scenario it
has after Change 1 syncs — otherwise archive would resurrect pre-Change-1 requirements.

## Risks / Trade-offs

- [Delta authored before Change 1 archives → MODIFIED text drifts from Change 1's output] → The
  carry-over in `specs/lore-registries/spec.md` copies Change 1's delta verbatim; at apply time,
  diff the MODIFIED requirement against the post-archive main spec and reconcile before editing
  `races.py`. Archive order is declared in proposal.md `## Batch:`.
- [A future entry legitimately wants a Latin gloss, e.g. `(Fionnen)`] → The gloss belongs in a
  lore codex field, not the creation-menu one-liner; until one exists, adding an exception is
  cheaper than letting English back into the prompt. Accepted trade-off.
- [Verbatim-pinned prose makes cosmetic edits fail tests] → Intended: these fifteen strings are
  player-facing contract text, mirroring how Change 1 pinned the human five.
- [Translation reviewed against lore but by a single pass] → The strings are quoted verbatim in
  the delta spec so the owner's review happens on the spec text before any code edit.
