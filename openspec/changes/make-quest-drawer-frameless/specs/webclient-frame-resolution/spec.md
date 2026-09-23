## REMOVED Requirements

### Requirement: A drawer follows the stack when its hosted frame pops
**Reason**: No drawer hosts a router frame any more (the bag, shop, and quest drawers are frameless client-local opens), so no frame pop can close a drawer and closing a drawer never pops a frame.
**Migration**: Drawer lifecycle is owned entirely by `webclient-contextual-hud` ("Reference drawers present no router frame and never host a dock row region"): drawers close on an explicit close or on the mode-change / epoch-reset / transport-loss teardown, and a committed update that removes a quest re-renders the quest drawer's own surfaces from the committed panel.
