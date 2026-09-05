# Delta spec: profession-registries (service-anchoring-gate)

Closes the D6 seam: `default_binding` becomes consumed by the anchoring gate. The stored-not-read
requirement is superseded by its replacement, reproduced in full.

## MODIFIED Requirements

### Requirement: default_binding is a validated vocabulary consumed by the anchoring gate
Each component entry's `default_binding` SHALL be one of `person` or `place`, validated at load;
the value SHALL be stored on the frozen component row and SHALL be consumed by profession
assembly, which copies it onto every component it creates (see the `service-anchoring`
capability). No runtime service gate SHALL read the profession table directly — gates read the
component's persisted binding.

#### Scenario: Assembly copies the binding onto created components
- **WHEN** assembly creates a component from a row whose `default_binding` is `place`
- **THEN** the created component persists `service_binding` `place` exactly as authored

#### Scenario: Runtime gates never read the profession table
- **WHEN** `service_gate.py` and every rewired service caller are searched for
  `profession_config` imports
- **THEN** none exist; availability comes from persisted component bindings only
