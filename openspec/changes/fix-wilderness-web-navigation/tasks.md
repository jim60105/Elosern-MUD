## 1. Canonical resolver

- [ ] 1.1 Add `resolve_wilderness_destination(room, direction, gateway_rule)` (pure read helper) mirroring `WildernessReturnExit.at_traverse` routing, including the south gateway override
- [ ] 1.2 Unit-test the resolver against the traversal semantics (ordinary neighbors and the gateway south exit)

## 2. Presenter wiring

- [ ] 2.1 In `web/webclient/presentation/local_map.py::_wilderness_layer`, attach `explore.move` action descriptors with canonical destinations for traversable adjacent nodes
- [ ] 2.2 In `web/webclient/presentation/exploration.py::_move_rows`, derive destinations from the resolver instead of `exit_obj.destination`

## 3. Tests and verification

- [ ] 3.1 Tests: minimap wilderness node has a move action with the true destination; gateway south row advertises the grid node
- [ ] 3.2 Run local-map, exploration-presentation, and wilderness movement tests
