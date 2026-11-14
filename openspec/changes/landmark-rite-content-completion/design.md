# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §6.3 and §11. The shipped document `world/lore/rites/content/landmark_rites.yaml` (`landmark-rite-content`) holds `spring`, `statue`, `megalith`, `tower` and `tree`, and marks every provisionally assigned district under the comment `# provisional: reassigned by landmark-rite-content-completion`.

The loader requires every declared archetype to be assigned at least one district and every district to be assigned once; the data-contract test `world.lore.tests.test_rite_content_document` runs it against the shipped district document.

## Goals / Non-Goals

**Goals**

- Ten archetypes, and every district assigned by what its landmark is.

**Non-Goals**

- No code, test, schema, bound or specification change.
- No change to the five existing archetypes' scenes, costs or labels.
- No `watch` scene, third option or art.

## Decisions

### D1. Archetypes

Add `grave`, `mine`, `gate`, `cliff` and `plaza` in the shape and under the authoring rules of `landmark-rite-content` design D3 and D4 (two options, `self` scenes of four to eight lines, `watch: null`, scene identifiers `rite.<archetype>.<option>.self`, `revision: r1`). Their registers are the third column of the design's §6.3 table: the dead speaking and shame; dark enclosed spaces and echoes; thresholds and permission to pass; washing, weightlessness and exposure; being seen in the one city square.

### D2. Final assignment

Remove the provisional comment and reassign those districts:

1. The representative landmarks named in the last five rows of the design's §6.3 table take the archetype of their row.
2. The landmark named 王都中央廣場 is `plaza`, and no other district is `plaza`.
3. Otherwise by what the landmark is: a tomb, cairn, barrow, bone mound or ruined cloister is `grave`; a pit, kiln, mill, cave or grotto is `mine`; an arch, gate, marker stone, sluice or bridge is `gate`; a waterfall, cliff, crag or peak is `cliff`.
4. A landmark that fits no family keeps or takes the archetype whose register fits it best; list each such district and the reason in the review document.

Leave the districts that `landmark-rite-content` assigned by its rules 1 and 2 unchanged.

### D3. Review document

Add the five archetypes' sections to `docs/lore/landmark-rites-review.md` in the existing layout, then the list of districts assigned by rule 4 with their reasons, and remove the provisional count.

## Risks / Trade-offs

- Ten more scenes are the whole cost. A missed provisional district keeps a rite of the wrong family; the grep in the tasks finds the comment.
