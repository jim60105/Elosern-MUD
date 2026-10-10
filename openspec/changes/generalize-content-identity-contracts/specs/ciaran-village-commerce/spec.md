# Spec Delta

## MODIFIED Requirements

### Requirement: The village's hosts are its own people
Each declared village host SHALL carry explicit valid authored race, corresponding subrace when declared, and sex. Synchronization SHALL use that creation-time identity with its declared race baselines and SHALL NOT infer personnel identity from the settlement or a default. Village place, dwelling and commerce contracts SHALL remain unchanged.

#### Scenario: Hosts carry the village's own lineage
- **WHEN** declared village hosts are created
- **THEN** each uses its valid authored race/subrace and corresponding race baselines without a settlement-derived identity default

#### Scenario: Host sex is authored, not defaulted
- **WHEN** the village's hosts are created
- **THEN** each carries its authored sex rather than the unspecified default
