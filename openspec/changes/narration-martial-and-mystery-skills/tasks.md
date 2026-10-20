# Tasks

## 1. Martial and enhancement rows

- [ ] 1.1 Author `world/skills/narration/data_martial.py` with one row per ACTIVE martial-arts
  skill (one or two action variants each, in the steel-and-shadow register) and verify the
  catalog validator accepts the module and that a same-family pair selects different opening
  lines.
- [ ] 1.2 Author the enhancement skill's row in the same module (the body answering its own
  training) and verify it renders instead of the category tier.

## 2. Holy rite and divine mystery rows

- [ ] 2.1 Author `world/skills/narration/data_holy_rite.py` with one row per ACTIVE holy-rite
  skill plus the rite-specific kind overrides its blessing/shelter outcomes need; verify the
  validator accepts it and that each rite's opening line comes from its own row.
- [ ] 2.2 Author `world/skills/narration/data_divine_mystery.py` with one row per ACTIVE
  divine-mystery skill plus the authority-line override where the shared `divine_*` pool would
  read generically; verify each mystery's opening line comes from its own row.

## 3. Close the families and verify

- [ ] 3.1 Import the four data modules in the catalog aggregate and remove martial arts, holy
  rites, divine mysteries and enhancement from the frozen pending-family set; verify import
  fails when one of their rows is deleted and the pinning test names the two remaining pending
  families.
- [ ] 3.2 Extend the coverage-contract slice to assert exact key-set equality for the four
  families, and run the focused catalog, selection and pipeline modules plus the traceability
  check; verify every assertion in this delta has a matching annotated test.

## Workflow follow-up

- Archive the change after review and merge, syncing the added requirement into the
  `action-narration` main spec.
