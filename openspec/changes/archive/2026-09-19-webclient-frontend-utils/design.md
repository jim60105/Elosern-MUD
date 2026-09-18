## Context

Both component duplications were caught already-identical; the store boilerplate is
mechanical. The constraints are the Vitest suite (existing tests mount the components and
assert rendered text/`aria-label`s — they must stay green without edits) and the showcase
evidence gates (component coverage is by file, not internals).

## Decisions

### D1 — `lib/condition_label.js::conditionLabel(condition)`; components keep thin delegates

```js
export function conditionLabel(condition) {
  const parts = [condition.label ?? condition.code];
  if (typeof condition.remaining_seconds === "number") {
    parts.push(`剩 ${condition.remaining_seconds} 秒`);
  }
  const mods = condition.modifiers;
  if (mods && typeof mods === "object") {
    for (const [key, value] of Object.entries(mods)) parts.push(`${key} ${value}`);
  }
  return parts.join("，");
}
```

Byte-identical body incl. zh-TW literals. `ConditionChips.vue` keeps
`const chipName = conditionLabel;` and `CharacterStatusDrawer.vue` keeps
`const conditionName = conditionLabel;` — template bindings (`chipName(condition)`,
`conditionName(condition)`) and any `wrapper.vm` introspection stay intact.

### D2 — `lib/narrative_line_nodes.js` owns the line→vnode pipeline

`narrativeLineNodes(h, line, index)` takes `h` as a parameter (the util stays Vue-import-free
except types, matching how `narrative-renderer.js` receives vnodes) — or imports `h` itself;
either is fine as long as both call sites pass through the SAME tokenize/render pipeline.
Pick: import `h` and `renderNarrativeTokens` + `NarrativeMarkup` inside the util; components
just call `narrativeLineNodes(line, index)`. The `BOX_DRAWING` regex lives once in the util
as `/[\u2500-\u257f]/` (same code-point set as the feed's literal spelling — verify with a
unit assertion that both forms agree on a box-drawing sample and a CJK sample).

### D3 — `readPanel(rs, key)` returns the raw panel-or-null ONLY

The per-panel predicates differ by contract (`party`/`objectives`/`roster`: `available === true`;
`status`/`exploration`: `available !== false`), so the helper must NOT normalize availability:

```js
function readPanel(rs, key) {
  return (rs.panels && rs.panels[key]) || null;
}
```

and replace the four `(rs.panels && rs.panels.X) || null` reads inside `buildView`
(party, objectives, roster, exploration). The vitals read already goes through the
`panels = rs.panels || {}` alias (`panels.status`), a different shape, and stays where it
is. The `available`/`Array.isArray` guards stay verbatim at each read site. Keeping it
non-exported avoids inviting callers outside `buildView`.

## Risks / Trade-offs

- Moving `lineNodes` out of the components' closures removes its implicit capture of
  `NarrativeMarkup`/`renderNarrativeTokens`; the util imports them directly — identical
  modules, no behavior delta, one extra module in the Vite graph (tree-shaken anyway).
- The Vitest suite is the regression net; add `tests/condition_label.test.js` and
  `tests/narrative_line_nodes.test.js` pinning the extracted rules (label join shape,
  divider-only-at-index-0 rule, box-drawing class) so the util itself carries the contract
  after extraction.
