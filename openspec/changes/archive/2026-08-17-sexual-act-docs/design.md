## Context

`docs/game/command-reference.md` and `docs/game/commands.md` are the player-facing command contract,
protected by `tests/test_command_docs.py`. The test parses every `### <key>` heading in the reference
page as a *canonical entry* and requires its key to match a command mounted on `CharacterCmdSet`,
`AccountCmdSet`, `CharacterCreationCmdSet`, or the project XYZGrid set
(`mounted_command_classes()`); any heading that does not match fails `test_no_orphan_canonical_entries`.
Sexual acts are not commands — they are `SkillDef` rows in `SKILL_REGISTRY` with a parallel
`SexualActDef` in `world/skills/sexual_acts/` (per `sexual-act-registry` design D-1), reached only
through the already-documented `cast` and `combat actions` commands. This fixes the shape of the
change: new content can only land inside the existing `### cast` and `### combat actions` sections (or
as table-cell text in `docs/game/commands.md`), never as a new canonical heading of its own.

The subset of the system this change documents is fully shipped:
`world/rules/sexual_state.py::SexualState.unlocked_act_keys()` and
`world/skills/sexual_acts/__init__.py::unlocked_act_keys_for()` gate ownership,
`world/rules/combat_view.py::group_skill_views` groups owned skills into a `sexual_act` category (shown
by `combat actions`) sub-grouped by line, `world/rules/sexual_resist.py` runs the resist contest (wired
into `ActionResolver.resolve()` for every cast, in or out of combat, by the archived
`sexual-resist-cast-wiring`), and the affinity/auto-leave consequence of a forced act is applied by
`world/rules/combat_session.py::_scan_sexual_coercion` in combat and by its shipped out-of-combat
sibling `world/rules/cast_settlement.py::_scan_out_of_combat_sexual_coercion` outside combat
(`sexual-resist-out-of-combat` has archived). `world/rules/rulebook/status_display.yaml` carries the
three player-visible condition labels for arousal, climax, and exposure. None of the shipped subset
above is touched by this change; the design problem is purely where the explanatory prose goes, how it
stays test-enforceable, and — per the corrections below — keeping every claim scoped to what is
actually shipped.

**Corrections (state tracked across two reviews):** an early draft of this change's proposal.md and
this file incorrectly claimed that `sexual-resist-out-of-combat` and both `sexual-catalog-divine-*`
proposals were already archived, and cited a nonexistent `world/rules/sexual_unlock.py` module and a
nonexistent `cast_settlement.py::_scan_out_of_combat_sexual_coercion` function. A first rubber-duck
review caught that by checking the actual repository state (task-completion counts,
`openspec/specs/` entries, and the cited functions/modules directly), and every citation was corrected
to the real module paths — including, at that time, scoping the affinity/auto-leave sentence to
in-combat casts only, since that was the only half of the mechanism shipped then. Before
implementation, the state moved again in the other direction: `sexual-resist-out-of-combat`,
`sexual-catalog-divine-core`, and `sexual-catalog-divine-mutators` have all since archived. Verified
against the current repository: `world/rules/cast_settlement.py` now defines
`_scan_out_of_combat_sexual_coercion` and `settle_out_of_combat_cast` runs it inside the settlement's
outer transaction, `world/skills/sexual_acts/divine.py` now ships the seven 神之秘法 acts, and
`world/rules/sexual_unlock.py` still does not exist — the unlock query lives at
`world/rules/sexual_state.py::SexualState.unlocked_act_keys()` and
`world/skills/sexual_acts/__init__.py::unlocked_act_keys_for()`. The affinity/auto-leave sentence is
therefore documented without combat scoping, and the only retained bound is the Non-Goal of not
enumerating individual divine-arts acts.

The `element-mastery-freeform-casting` change (archived) already extended the `cast` requirement once,
adding an `ADDED Requirement` delta to `game-command-docs` with two scenarios: one asserting the
manifest/reference syntax match plus token presence in the 說明 field, one asserting the overview row's
wording. This proposal repeats that exact shape for a second, unrelated `cast`/`combat actions`
extension.

## Goals / Non-Goals

**Goals:**
- Every player who reaches an unlock threshold can learn, from the docs alone, how a 性愛 act is
  discovered (`combat actions` category grouping), how resisting works, what forcing an act costs, and
  that divine arts are race-gated — before it happens in play.
- The new content is protected by a contract test in the same style as every other documented command
  fact, so it cannot silently drift from the shipped resist/affinity behavior.
- Zero runtime code changes; zero new commands; zero new canonical headings.

**Non-Goals:**
- No enumeration of the 69 individual acts, their exact pleasure/counter numbers, or their unlock
  thresholds — the reference page does not enumerate the 80 elemental spells either (that is catalog
  data, not command documentation), and the sexual-act catalog is the same shape of data.
- No new docs page (e.g. a dedicated `docs/game/sexual-acts.md`). The design doc's own scope line names
  exactly two files; a third page would be a bigger surface than the gap being closed and would need its
  own sidebar/navigation requirements this proposal has no reason to open.
- No explicit or graphic content. Every existing design doc, spec, and proposal for this system (all
  archived and merged) describes it in mechanical, systems-register language — gauges, contests, event
  entries, condition labels — and this proposal keeps that register.
- No change to `EXPECTED_COMMANDS["cast"]` or `["combat actions"]` in `tests/test_command_docs.py`
  (syntax and context are unchanged); only the 說明 field content and a new prose block change.
- No claim about which of the seven 神之秘法 acts exist or what they do. Although
  `sexual-catalog-divine-core` and `sexual-catalog-divine-mutators` have archived and `divine.py`
  ships real content, the reference page does not enumerate the acts of any line — catalog data is
  not command documentation, and discovery-by-play is the intended experience. The only divine-arts
  fact this proposal documents (the race gate on the pre-existing `divine_sexual_arts` skill)
  predates both archived proposals.
- No claim that any part of the affinity/auto-leave consequence is combat-scoped. Both
  `_scan_sexual_coercion` (in-combat) and `_scan_out_of_combat_sexual_coercion` (out of combat) are
  shipped; the prose states the consequence as applying to forced acts generally.

## Decisions

- **New content is prose under the existing `### cast` heading, not a new canonical heading.**
  `parse_canonical_entries()` attributes every line after a `### <key>` heading to that key until the
  next `#`-prefixed line, and only lines matching `| field | value |` with `field` in
  `("指令","別名","語法","情境","說明")` become table facts — a plain paragraph is silently skipped by
  the parser. This means the detailed unlock/resist/status/divine-arts explanation can live as ordinary
  Markdown paragraphs immediately below the `cast` field table, still inside the `### cast` section, and
  the parser neither attributes it to a phantom key nor complains about it. *Alternative rejected:* a
  new `### 性愛系統` heading — clean information architecture, but `test_no_orphan_canonical_entries`
  would fail immediately because no command class has that key, and there is no mounted command to give
  it one without inventing a fake command.
- **The `cast` and `combat actions` 說明 fields each gain one additional clause, not a rewrite.** Both
  fields are single-line table cells today (`cast`'s already carries the freeform-scale explanation from
  the prior extension); appending a clause preserves every existing assertion in
  `test_cast_entry_documents_the_freeform_scale_token` (it only checks token presence with
  `assertIn`, not field equality) and keeps the diff reviewable against the shipped behavior each clause
  describes.
- **The new spec requirement pins keyword substrings, not full sentences, for every fact it states —
  not only some of them.** An earlier draft pinned substrings for 抵抗 (resist), 好感度 (affinity),
  and 神之秘法 (divine arts) but left "unlock is play-driven" and "the three status condition labels
  appear while active" untested, contradicting this same design's stated goal that the content "cannot
  silently drift." Corrected: the delta now also requires 解鎖 (unlock) in the section prose, all three
  status-label terms (興奮, 高潮, 露出), 戰鬥 (the resist contest applies in and out of combat), and a
  negative assertion that no individual divine-arts act name appears. Following the scale-token
  requirement's own pattern (`assertIn("1/4", entry["說明"])` etc.), substrings rather than exact prose
  still give the implementer wording latitude.
- **`docs/game/commands.md`'s cast row gets a short addition, not a new table row.** The overview groups
  commands by category (`test_overview_groups_commands_by_category`) and every row must correspond to a
  documented canonical key (`test_overview_links_only_documented_keys_and_all_keys` requires the link set
  to exactly equal the canonical-entry key set) — adding a new row would need a new key, which loops back
  into the orphan-heading problem above. Extending the existing `cast` row's description cell is the only
  option that adds visibility without adding a key.
- **No change to `world/skills/`, `world/rules/`, or any runtime module.** This proposal is documentation
  only; every fact stated in the new prose is read from already-archived, already-tested behavior (cited
  by module path in the proposal's Impact section) and is not re-derived here.

## Risks / Trade-offs

- [Risk — found and fixed during review] The original draft claimed `sexual-resist-out-of-combat` and
  both `sexual-catalog-divine-*` proposals were already archived and cited a nonexistent
  `_scan_out_of_combat_sexual_coercion` function and a nonexistent `sexual_unlock.py` module. A
  rubber-duck review caught this by checking the actual repository state (task-completion counts,
  `openspec/specs/` entries, and the cited functions/modules directly). → Fixed: every citation now
  points at real code. The interim correction then over-corrected in the other direction, scoping the
  affinity/auto-leave clause to in-combat casts only; that scoping became stale when
  `sexual-resist-out-of-combat` archived and shipped `_scan_out_of_combat_sexual_coercion`, and this
  implementation's prose states the consequence without combat scoping, re-verified against the
  current repository before writing (tasks 1.4 and 1.6). This is the reason a docs-only change still
  benefits from a correctness review before implementation: the risk was not in the Markdown, it was
  in an unverified claim about the state of the codebase the Markdown would describe as fact.
- [Risk — found and fixed during the implementation rubber-duck review] The first full draft of the
  prose claimed (a) no sexual act is available at character creation except the `divine_sexual_arts`
  gate skill, and (b) a successful resist means "the cast does not execute" while the caster still
  pays resources. Both are wrong against the shipped code: `unlocked_act_keys_for()` treats an empty
  `unlock` table as owned-by-everyone, so the seed acts (solo 3, shame 1, partner 2, combat 1) and
  all seven 神之秘法 acts are available at creation — the divine line's containment is the cast-time
  race gate, not ownership; and on a resisted cast `_step5_effect_resolution` still runs the
  actor-side pleasure/counter effects, `_step6_skill_practice` still grants practice XP, time cost is
  unconditional, and the divine acts declare `cost={}`. → Fixed: the prose now states per-act unlock
  (seeds available at creation, the rest gated by counters), describes a successful resist as leaving
  the target unaffected while the cast still consumes time and the skill's resource cost (if any),
  and the spec delta pins the corrected claims (解鎖, 戰鬥, all three status labels) plus a negative
  assertion that no divine act is named.
- [Risk] The new prose block could drift from the actual resist/affinity behavior if `sexual-resist-*`
  is ever revised later (e.g. the penalty stops being affinity-based, or auto-leave is removed). →
  Mitigation: the spec requirement's substring assertions (好感度, 抵抗, 解鎖, 興奮, 神之秘法) give a
  cheap tripwire — wording that stops matching those tokens fails the test — but a full behavioral
  rewrite still needs a human to notice the docs need a matching edit. (An earlier draft also flagged
  a follow-up trigger for dropping the "in combat only" scoping once `sexual-resist-out-of-combat`
  archived; that proposal has since archived and this implementation has already dropped the scoping,
  so the trigger is closed.)
- [Risk] Keyword-substring assertions are weaker than the scale-token requirement's full-sentence pin,
  so a low-quality edit could satisfy the test while reading badly. → Mitigation: acceptable trade-off
  for a docs-only change with no numeric contract to pin (unlike scale values); a human review of the
  actual prose at merge time covers quality, the test covers presence.
- [Trade-off] Not enumerating individual acts means a curious player must still discover specific acts
  in play rather than reading a spoiler list. → Accepted deliberately: matches the existing convention
  for the 80 elemental spells, and per the source design doc's own framing, discovery-by-play is the
  intended experience for this system, not an oversight to fix.

## Migration Plan

None. Two Markdown files and one spec delta; no code, no data, no deploy step. Lands independently of
every other active change — every proposal it documents (`sexual-act-seeds`, all six catalog lines,
and the full resist chain) is already archived.

## Open Questions

None.
