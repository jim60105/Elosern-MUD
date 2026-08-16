## Why

`sexual-act-seeds` (this proposal's direct dependency) ships three unconditionally-available
獨處線 (solo) seeds — 自撫, 揉捏胸部, 摩擦大腿 — and nothing past them. A player who has masturbated
ten or more times has no new solo content to unlock: `world/skills/sexual_acts/solo.py`'s `SOLO_ACTS`
tuple contains only the three seeds, so `masturbation_count` and `toy_use_count` accumulate with
nothing reading their higher thresholds.

This proposal fills the next three tiers of the 獨處線 catalog: five acts unlocked at
`masturbation_count >= 10`, three toy-flavoured acts at `masturbation_count >= 25`, and three
advanced-toy acts at `masturbation_count >= 25` **and** `toy_use_count >= 15` — eleven acts total, all
expressible through the existing, unmodified `pleasure:`/`sexual_counter:`/`sexual_event:` effect
machinery.

## What Changes

- Add eleven acts to `world/skills/sexual_acts/solo.py`'s `SOLO_ACTS` tuple, all `TargetSpec.SELF`:
  - **Tier 1** (`unlock={"masturbation_count": 10}`): 深度自慰（私處）, 雙手併用（私處）,
    舔舐指尖（口唇）, 撫弄後庭（後庭）, 玩弄乳尖（乳房）.
  - **Tier 2** (`unlock={"masturbation_count": 25}`): 玩具自慰·振動（私處）,
    玩具自慰·夾具（乳房）, 玩具自慰·填充（後庭）. Each credits both `masturbation_count` and
    `toy_use_count` on the actor — a toy act is still a solo act.
  - **Tier 3** (`unlock={"masturbation_count": 25, "toy_use_count": 15}`, a compound gate — see
    design.md D-1's note on why the two thresholds are named together, not `toy_use_count` alone):
    高階玩具·連結（私處, `base_pleasure=24`）, 高階玩具·全身（私處, `base_pleasure=26`）,
    拘束自慰（私處, `base_pleasure=25`, deliberately kept mid-pack rather than the tier's highest —
    see design.md D-4). Same dual-counter crediting as Tier 2.
- **Explicitly defers three acts from the source design document's 獨處線 table**: 快感控制, 寸止,
  and 極限忍耐 (the `restraint_count`-gated pleasure-*reduction* acts). See design.md's Decisions
  section — the landed `SexualActDef`/`_act_family()` contract has no mechanism to express a negative
  pleasure effect (`base_pleasure` is structurally validated as a positive integer, and
  `_apply_pleasure_gain` only ever adds), and `極限忍耐`'s "several rounds immune to `climax_gate`"
  additionally requires a buff/immunity mechanism that does not exist. Building either is out of this
  proposal's scope and is not attempted as a workaround.
- **Ships every act as a pure pleasure/counter/event registration** — no new effect prefix, no new
  `SexualActDef` field, no `_builder.py` change. The source catalog document's "multi-part" flavour
  for 雙手併用/高階玩具·全身/拘束自慰 and 拘束自慰's self-`defense` penalty are narrative-only in this
  proposal (`SexualActDef` carries exactly one `actor_part`; there is no secondary-effect field to
  attach a debuff to). See design.md Decisions for why these are disclosed simplifications, not
  silent omissions.

## Capabilities

### New Capabilities
- `sexual-catalog-solo`: the eleven Tier 1–3 獨處線 acts and their counter-based unlock thresholds.

### Modified Capabilities
- none — `sexual-act-registry`, `sexual-act-effects`, and `sexual-act-seeds`'s existing requirements
  are exercised, not changed.

## Impact

- Code: `world/skills/sexual_acts/solo.py` only, plus a new test module,
  `world/skills/sexual_acts/tests/test_solo_catalog.py`.
- Collateral test updates (same class as `sexual-act-seeds`'s): eight pre-existing test files assert a
  fresh entity's unlocked set as `sorted(SEXUAL_ACT_REGISTRY)` or pin the SEXUAL_ACT category's key
  set, and break the moment any counter-gated act registers. They are updated to read the
  unconditionally-unlocked (empty-`unlock`) subset: `test_registry_structure.py`, `test_handler.py`,
  `test_inventory.py`, `test_registry.py`, `test_status_query.py`, `test_combat_view.py`,
  `test_combat_session.py`, and `web/webclient/presentation/tests/test_character_panel.py`. See
  tasks.md section 6.
- No change to `_builder.py`, `__init__.py`, any other line module, or `world/rules/rulebook/
  sexual.yaml` — every act this proposal adds resolves through already-landed, already-tested
  machinery with no rulebook addition needed (unlike `sexual-act-seeds`, which needed one new
  `sexual.yaml` row for the shame line).
- Deferred, not delivered: 快感控制, 寸止, 極限忍耐 (pleasure-reduction acts — see design.md);
  拘束自慰's self-`defense` penalty flavour (see design.md).
