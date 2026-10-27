# Spec Delta

## ADDED Requirements

### Requirement: Church enrollment routing documents the selected provider
Both command references and the curated command manifest SHALL document church join <npc> with existing aliases and permissions. Opening a browser enrollment route SHALL focus the existing command input with the explicit target and SHALL NOT submit enrollment.

#### Scenario: Explicit church target
- **WHEN** the enrollment route for one of two clergy is opened
- **THEN** the input names that clergy; later command submission revalidates only it and both documents describe the same syntax
