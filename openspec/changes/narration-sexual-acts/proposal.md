# Proposal

## Why

Sexual casts are the clearest example of the reported problem: every act renders
`悠奈 面對 悠花 的意圖，做出了自己的選擇。` / `悠花的快感提升了。` /
`悠花的性行為計數提升了。`, so 挑逗, 親吻 and 交合 are indistinguishable, and the
interaction never says what the characters did or how it landed. After the three preceding
changes the engine, combat prose and both non-sexual families narrate; this change completes
the content so every act tells its own beat.

## What Changes

- Author one row per sexual act for all 66 ACTIVE acts across the six act lines, each carrying
  the act's *attempt* line (contact is never asserted there, because the verdict clause
  completes it) with one or two variants.
- Author the act-specific overrides that the shared pools cannot know: the act's own bodily
  focus wording for its pleasure clause, its own counter phrasing where the act's declaration
  distinguishes performer from participant, and its own line for the transition events it fires.
- Cover every sexual transition event name the catalog can emit (13 names, including the
  pair-event names selected from the participants' sexes) and every lifetime counter the catalog
  declares (8 names), each with performer and participant clauses; both pools are validated for
  exact key-set equality against the catalog-derived sets.
- Remove sexual acts from the pending-family set, leaving it empty: from then on an ACTIVE
  skill of any family without its own narration row fails at import.

## Capabilities

### New Capabilities

### Modified Capabilities
- `action-narration`: adds the per-act coverage requirement, the verdict/role clause contract for
  social acts, and the catalog-derived transition/counter coverage requirement; empties the
  pending-family set.

## Impact

- Six authored data modules under `world/skills/narration/` (one per act line: partner, solo,
  shame, combat, interspecies, divine) plus the catalog aggregate, the shared sexual pools and
  the frozen pending-family constant.
- The coverage-contract slice gains exact act/counter/event-set assertions; the sexual narration
  behavior tests (verdict classes, actor-vs-participant voice, role-aware counters) live in the
  existing catalog test module.
- No change to `sexual.yaml`, the act registry, `SexualActDef`, resist math, pleasure math, or
  the counters themselves; prose only reads those facts.
