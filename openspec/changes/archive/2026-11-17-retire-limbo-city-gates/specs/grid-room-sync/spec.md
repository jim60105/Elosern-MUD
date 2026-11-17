# Spec Delta

## REMOVED Requirements

### Requirement: A single authored, idempotent Exit bridges Limbo and the sample city
**Reason**: Characters start in their subrace's settlement (`subrace-start-settlements`),
and 虛境 only holds creation-pending shells. `sync_grid()` no longer authors any exit
touching 虛境.
**Migration**: None. `sync_limbo()` removes leftover bridge exits (`limbo-one-way-gates`).
