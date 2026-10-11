# Spec Delta

## MODIFIED Requirements

### Requirement: Adding the blueprint changes no shipped host
Introducing an unused profession blueprint SHALL NOT alter existing place rows, service hosts, interiors or dialogue. Host creation SHALL follow current place declarations and shared assembly without implicit profession-default personnel. A later authored roster edit SHALL take effect through its existing sync contract without freezing historical identities.

#### Scenario: The shipped roster is unchanged by the new blueprint
- **WHEN** a synthetic unused blueprint is registered while hosted place declarations stay unchanged
- **THEN** derived identities, professions, anchors and components remain unchanged; adding a place using that blueprint creates only its declared host

