# Tasks

Future implementation only. Documentation change; follow design.md wording.

## 1. Guide edits

- [ ] 1.1 Apply design D1 and D2 to `docs/lore/monster-creation-guidelines.md`. Check: line 5 is unchanged, the new approval paragraph and section 8 exist, and both relative Docsify links point to existing files.
- [ ] 1.2 Apply design D3 and D4. Check: `grep -n "其餘六變體\|吞潮鱷、穗鳴雀、潮燈蟹各有" docs/lore/monster-creation-guidelines.md` returns nothing and the kit section names no species roster.

## 2. Handoff

- [ ] 2.1 Run `openspec validate affirmative-monster-prose-guidelines --strict` and `uv run --locked python -m tools.contract_gate`. Check: both exit 0 and `git diff --stat` lists only the guide.
