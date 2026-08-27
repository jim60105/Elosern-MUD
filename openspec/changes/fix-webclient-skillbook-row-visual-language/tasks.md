## 1. Category summary: count + chevron

- [ ] 1.1 In `SkillBook.vue`'s `<summary>`, add a trailing count span (`data-testid="skill-book__category-count"`) showing the category's own flattened skill count (sum of `groups[].skills.length`, already computable inline or via a small `categorySkillCount(category)` helper)
- [ ] 1.2 Add a chevron span (`data-testid="skill-book__category-chevron"`, e.g. `›`) after the count, `aria-hidden="true"`
- [ ] 1.3 CSS: `.skill-book__category-summary{display:flex;align-items:center;gap:9px}`; `.skill-book__category-count{margin-left:auto;font-family:var(--f-mono);font-size:11px;color:var(--paper-500)}`; `.skill-book__category-chevron{color:var(--paper-500);transition:transform .2s}`; `details[open]>.skill-book__category-summary .skill-book__category-chevron{transform:rotate(90deg)}`
- [ ] 1.4 Style the existing `.skill-book__category-label` per the draft's `.lab`: `color:var(--gold-400);font-weight:600`

## 2. Group label: colour dot

- [ ] 2.1 Add a local `ELEMENT_DOT_COLORS = { fire: "var(--seal-500)", water: "var(--vit-mp)", wind: "var(--warn)" }` constant in `SkillBook.vue`
- [ ] 2.2 Add a `groupDotColor(category, group)` helper: return `var(--seal-500)` when `category === "sexual_act"`; else return `ELEMENT_DOT_COLORS[group]` when `category === "elemental_magic"` and `group` is a mapped key; else return `null`
- [ ] 2.3 In the group-label template, render a dot span (`data-testid="skill-book__group-dot"`, `:style="{ background: dotColor }"`) **nested inside** `.skill-book__group-label` (immediately before `{{ group.label }}`, not as a preceding sibling of the `<p>`) only when `groupDotColor(...)` is non-null — the draft's `.grp` dot works because it and the text share one `display:flex` container; a sibling-before-`<p>` placement would stack the dot above the label instead of beside it, so `.skill-book__group-label` also needs `display:flex;align-items:center` added in 2.4
- [ ] 2.4 CSS: `.skill-book__group-dot{width:7px;height:7px;border-radius:2px;display:inline-block;margin-right:7px}` (matching the draft's `.grp .dot`); add `display:flex;align-items:center` to `.skill-book__group-label` so the nested dot sits beside the text, not above it

## 3. Cost cell: resource colour-coding

- [ ] 3.1 Add a `costColorClass(row)` (or inline computed style) helper: `"sp" in (row.cost ?? {})` → `--vit-sp`; else `"mp" in (row.cost ?? {})` → `--vit-mp`; else (no cost, or empty `{}`) → `--paper-500`
- [ ] 3.2 Apply the resolved colour to `.skill-book__cost`'s `color` via an inline `:style` binding or a `sp`/`mp`/`free` modifier class, matching the draft's `.cost` / `.cost.sp` / `.cost.free` cascade precedence (sp wins when both present)

## 4. OOC pill: exact styling

- [ ] 4.1 Restyle the `combat` pill added by `fix-webclient-skillbook-descriptor-data` (`data-testid="skill-book__ooc"`) to the draft's `.srow .ooc` rule: `font-size:9px;letter-spacing:.04em;color:var(--ok);border:1px solid rgba(112,150,122,.5);border-radius:4px;padding:0 4px`. Before applying the draft's `margin-left:8px`, check the pill's actual DOM position from the sibling change: in the draft, `.ooc` nests inside `.nm` (the name span) with no other spacing mechanism, so `margin-left:8px` is correct there; but `.skill-book__skill` already has `gap: var(--sp-2)` (8px) between flex children — if the pill lands as a `gap`-separated sibling of `.skill-book__skill-name` rather than nested inside it, drop `margin-left` so the flex `gap` alone provides the spacing (avoiding a stacked 16px gap)

## 5. Passive badge

- [ ] 5.1 On the passive tab, add a trailing `被動` badge (`data-testid="skill-book__passive-badge"`) to each skill row, styled per the draft's `.prf`: `font-family:var(--f-mono);font-size:10px;color:var(--paper-700);margin-left:8px`

## 6. Legend

- [ ] 6.1 Add a legend line (`data-testid="skill-book__legend"`) above the category list, rendered only when `tab === "active"`, matching `index.html:892` exactly: `依分類分群；` + `<span style="color:var(--ok)">戰鬥外</span>` (plain colored text, no border/padding/pill — do NOT reuse the `.ooc` pill class here, it is a different element that reads "combat", not "戰鬥外") + ` 表示非戰鬥亦可施放；未解鎖之性愛行為「藏而不列」。`
- [ ] 6.2 CSS: match the draft's legend `.log` styling (`font-size:12.5px;color:var(--paper-500);margin-bottom:8px`); the inner `戰鬥外` span needs only `color:var(--ok)`, no other rule

## 7. Fixtures and tests

- [ ] 7.1 `SKILLS_SLICE_SAMPLE` already exercises both cost colour classes (`light_blade`: `{sp:6}`; `firestorm`: `{mp:30,sp:5}`, proving the sp-wins-when-mixed precedence) and the `fire`/`water` dot colours (`fire`/`water` groups already present) — no fixture change needed for those. It has **no** `wind` group and **no** `sexual_act` category anywhere: add one `wind` skill row (e.g. under `elemental_magic`, matching the draft's `疾風突進`) and one `sexual_act` category with at least one group, so the wind and sexual-act dot colours are exercised by the fixture too, not just asserted in isolation
- [ ] 7.1b Add one skill row under an unmapped element (e.g. `earth`) so the "no dot for an unsampled element" negative case has fixture backing
- [ ] 7.2 `web/webclient-app/tests/data/skill_book.test.js`: assert the category chevron's `transform` responds to the `<details>` `open` state; assert the group dot renders with the correct colour for `fire`/`water`/`wind`/`sexual_act` and renders absent for a group not in the map (add a fixture row under an unmapped element, e.g. `earth`, to prove the negative case); assert cost colour class/style matches `mp`-only, `sp`-present, and free rows; assert the OOC pill's rendered style matches the draft's rule; assert the passive badge renders on the passive tab only; assert the legend renders on the active tab only
- [ ] 7.3 Storybook: confirm `Data/SkillBook`'s existing stories visually show the new chevron/dot(fire/water)/cost-colour/legend/badge with no new story variant required; the `wind`/`sexual_act`/unmapped-element rows added in 7.1/7.1b render inside the same `ActiveTab` story once the fixture is extended, so still no new story variant is needed — just the fixture extension

## 8. Spec sync and gates

- [ ] 8.1 Confirm `openspec/changes/fix-webclient-skillbook-row-visual-language/specs/webclient-component-showcase/spec.md`'s MODIFIED requirement matches the implemented behavior exactly
- [ ] 8.2 Run `openspec validate fix-webclient-skillbook-row-visual-language --strict`
- [ ] 8.3 Run `npm test` (Vitest) for the affected component/story tests
- [ ] 8.4 Run `tools.spec_traceability check` to confirm the amended requirement's new scenarios have matching tests
- [ ] 8.5 Confirm this change lands after `fix-webclient-skillbook-descriptor-data` is archived (its spec delta is written against that change's post-archive requirement text, not the pre-archive one)
