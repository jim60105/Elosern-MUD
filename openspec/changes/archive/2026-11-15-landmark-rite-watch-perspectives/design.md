# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §6 and §11 (rule 5 governs the watch perspective). When this change was authored, the shipped document was `world/lore/rites/content/landmark_rites.yaml` (`landmark-rite-content`): ten archetypes, two options each, every `watch` was `null`.

Mechanisms already in place and not changed here:

- The loader accepts a `watch` scene with the same bounds as a `self` scene and requires at least one narration line and document-wide unique `scene_id` values.
- The delivery replaces every literal `{name}` in a watch scene's line text with the performing companion's name (`landmark-rite-action` design D1). A watch scene cannot name the companion any other way.
- The settlement writes sexual state to the companion and the record to the player character; the panel marks the option `companion: true`.

## Goals / Non-Goals

**Goals**

- A watch scene for every option that reads naturally with a companion of any gender.

**Non-Goals**

- No code, test, schema, bound or specification change.
- No change to any `self` scene, cost, label or assignment.
- No third option (`landmark-rite-third-option`).

## Decisions

### D1. Shape

For each option, replace `watch: null` with:

```yaml
watch:
  scene_id: rite.<archetype>.<option>.watch
  revision: r1
  lines:
    - {kind: narration, text: ...}
```

Three to seven lines. Speakers are only `actor` (the companion) and `host` (the guardian).

### D2. Authoring rules

All of the design's §11 applies. Specific to the watch perspective:

- Third person. The reader is the player character watching.
- The companion appears only as `{name}`. Never write a fixed name, 她, 他, 她的, 他的, 妳 or a gendered noun (少女, 青年 and the like) for the companion. Body parts are named directly or with `{name}的`.
- The acting body's anatomy is not assumed: a watch scene describes what the watcher sees and hears (posture, breath, the object's response, the guardian's words), so it reads correctly for any companion. Do not name genitals of a specific sex in a watch scene.
- The same three beats as the `self` scene of that option, seen from outside: the companion gains information, interacts with the landmark object, and climaxes. Show them; do not state them.
- The guardian is never male or male-figured; no male or male-figured partner appears.
- A watch scene is not the `self` scene with pronouns swapped. Write what a bystander would notice.

An option stays `watch: null` only when its ritual cannot be witnessed or shared without contradicting its own story. Expect few or none; list each with its reason in the review.

### D3. Review document

Add a section "Watch perspectives" to `docs/lore/landmark-rites-review.md`: one row per option with the result against each rule of D2 (placeholder only, no gendered word, three beats with line numbers, guardian rule), then the list of options kept solo-only with their reasons. State that this is human review.

## Risks / Trade-offs

- A watch scene that slips in a gendered pronoun reads wrongly for some companions. Only the human review catches it; the grep in the tasks is an aid, not a gate.
