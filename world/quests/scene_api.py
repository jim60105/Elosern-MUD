"""The published scene-package operation contract (quest-scene-encounters).

The four boundary operations the two downstream designs consume, re-exported
from their owning modules so callers import one named surface:

* :func:`publish_scene_package` -- validate and persist an immutable package;
* :func:`lookup_story_role` -- read-only role definition and binding status;
* :func:`activate_scene_encounter` -- the pre-acceptance activation transaction;
* :func:`transition_story_dialogue` -- the revisioned phase transition.

This module is a deterministic boundary: it imports no generative or transport
module and changes no state by itself.
"""

from .encounter_activation import (
    EncounterActivation,
    EncounterUnavailable,
    SceneEncounterNotFound,
    activate_scene_encounter,
    cancel_scene_encounter,
    committed_observations,
)
from .encounters import (
    PublishedPackage,
    ScenePackageNotFound,
    SceneRoleNotFound,
    StoryRoleLookup,
    lookup_story_role,
    publish_scene_package,
)
from .story_dialogue import (
    StalePhaseRevision,
    StoryDialogueError,
    StoryPhaseTransition,
    StoryRoleNotFound,
    transfer_story_knowledge,
    transition_story_dialogue,
)
from .escort_lifecycle import (
    EscortOperationError,
    accept_escort_commission,
    release_escort_bindings,
)
from .escort_events import (
    evaluate_escort_event,
    exclusive_outcome_status,
    resolve_exclusive_outcome,
)

__all__ = [
    "EncounterActivation",
    "EncounterUnavailable",
    "PublishedPackage",
    "SceneEncounterNotFound",
    "ScenePackageNotFound",
    "SceneRoleNotFound",
    "StalePhaseRevision",
    "StoryDialogueError",
    "StoryPhaseTransition",
    "StoryRoleLookup",
    "StoryRoleNotFound",
    "activate_scene_encounter",
    "cancel_scene_encounter",
    "committed_observations",
    "lookup_story_role",
    "publish_scene_package",
    "transfer_story_knowledge",
    "transition_story_dialogue",
    "EscortOperationError",
    "accept_escort_commission",
    "release_escort_bindings",
    "evaluate_escort_event",
    "exclusive_outcome_status",
    "resolve_exclusive_outcome",
]
