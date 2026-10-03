## 1. Explicit architecture amendment

- [ ] 1.1 Amend AI engine design sections 3.1 and 3.2 with a dated ownership decision linked to the approved narrative design; verify all named owners and the proposal-only boundary agree.
- [ ] 1.2 Amend AGENTS.md package descriptions and ownership list without changing registry-only and pre-release rules; verify both documents use the same contract.
- [ ] 1.3 Review the amendment against Sections 2 and 10 of the narrative design; verify no unimplemented modules or gameplay capabilities were added.

## 2. Handoff

- [ ] 2.1 Verify only the two ownership documents changed, their authority lists agree, and no feature code/scaffolding landed; run `openspec validate narrative-subsystem-ownership --strict` and the applicable documentation contract gate.
