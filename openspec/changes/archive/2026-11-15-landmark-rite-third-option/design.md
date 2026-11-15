# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` decision 3, §6 and §11. The shipped document `world/lore/rites/content/landmark_rites.yaml` holds ten archetypes with two options each, with watch scenes from `landmark-rite-watch-perspectives`.

Mechanisms already in place and not changed here: the loader accepts two or three options per archetype with unique keys; the panel lists up to three options; the rite panel gives each a digit; the completion record counts each option separately; the arrival card shows `已體驗 n / <options>`.

## Goals / Non-Goals

**Goals**

- A third option only where it is a different story, not a variation.

**Non-Goals**

- No code, test, schema, bound or specification change.
- No change to an existing option, scene, cost, label or assignment, and no fourth option (the loader rejects it).
- No requirement that every archetype gains one.

## Decisions

### D1. When an archetype gains a third option

Add one only when all three hold:

- it uses the landmark object in a way neither existing option does (a different part of the object, a different posture, or a different demand from the guardian);
- the information the acting body gains differs from both existing options;
- its register differs: if both existing options are enclosed and private, the third may be exposed, or the reverse.

Otherwise leave the archetype at two and record the reason in the review.

### D2. Shape and rules

Append the option after the two existing ones (order is the digit order on the panel):

```yaml
- key: <new key, unique in the archetype>
  label_zh: ...
  seconds: ...
  shame: ...
  exposure: ...
  self:
    scene_id: rite.<archetype>.<key>.self
    revision: r1
    lines: [...]
  watch:   # a scene, or null with a reason in the review
    scene_id: rite.<archetype>.<key>.watch
    revision: r1
    lines: [...]
```

The `self` scene follows the authoring rules of `landmark-rite-content` design D4; the `watch` scene follows `landmark-rite-watch-perspectives` design D2 (the `{name}` placeholder only, no 她 or 他). Costs stay within the loader's bounds and follow the same relation to the story as the existing options.

### D3. Review document

Add a section "Third options" to `docs/lore/landmark-rites-review.md`: for each archetype, either the new option's row (the three conditions of D1, the three beats with line numbers, the §11 rules, the watch rules) or one line stating why the archetype keeps two options. State that this is human review.

## Risks / Trade-offs

- A returning player sees `已體驗 2 / 3` at landmarks whose archetype gained an option. That is the intended invitation to return.
