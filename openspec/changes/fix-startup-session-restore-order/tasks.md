## 1. Startup ordering

- [ ] 1.1 Reorder `at_server_start` so persisted-session restoration runs before `sync_wilderness`
- [ ] 1.2 Confirm the moved restoration step still registers clock sources and skip-safety state correctly

## 2. Reconciliation participant guard

- [ ] 2.1 In `world/maps/wilderness_population.py::ensure_population`, skip monsters referenced by any persisted `active_combat` record

## 3. Tests and verification

- [ ] 3.1 Test: committed wilderness kill followed by restart settles as victory (not defeat), with the monster reconciled only afterwards
- [ ] 3.2 Test: reconciliation without sessions behaves exactly as before
- [ ] 3.3 Run wilderness-population, startup, and combat-session restore tests
