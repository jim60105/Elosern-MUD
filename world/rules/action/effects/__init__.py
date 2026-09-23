"""Effect-handler modules of the action pipeline.

Importing this package imports every handler module, which registers each
effect prefix as an import side effect. Keep the registry fully populated by
importing the package (or any handler module) before resolving an action.
"""

from world.rules.action.effects import (  # noqa: F401  (import for registration side effects)
    buffs,
    church,
    conferral,
    divine,
    gauge_transfer,
    sexual,
)
