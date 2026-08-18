"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

import logging
from typing import Any

from evennia.contrib.grid.wilderness.wilderness import WildernessExit, enter_wilderness
from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit
from evennia.objects.objects import DefaultExit

from .objects import ObjectParent
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.movement_settlement import settle_movement

logger = logging.getLogger(__name__)


def after_successful_movement(
    traversing_object: Any,
    source_location: Any,
    *,
    cost_key: str,
    destination: Any | None = None,
    wilderness_coordinates: tuple[int, int] | None = None,
    wilderness_source_coordinates: tuple[int, int] | None = None,
    wilderness_name: str = WILDERNESS_NAME,
) -> None:
    """Complete a successful traversal through the shared movement boundary.

    Runs the success-path sequence every exit lineage shares (onboarding-skip
    coverage design D1): charge the ``cost_key`` clock cost, record the
    destination map-knowledge node, move co-located companions, and finally run
    the onboarding room-entry observer so any arrival outside the guided
    corridor — plain ``Room``, ``GridRoom``, ``TerrainRoom``, or
    ``InstanceRoom`` — marks the guide skipped. ``charge_movement``,
    ``record_arrival``, and ``follow_companions`` are internally no-ops for
    anything that is not a ``PlayerCharacter``; ``charge_movement`` can raise
    when ``WorldClock.advance`` fails — the movement-settlement boundary
    (movement-settlement-atomicity design D1) compensates that failure — and
    ``record_arrival``/``follow_companions`` are exception-isolated. The
    onboarding observer is player-gated and idempotent, so the helper is safe
    to call on any successful traversal from any path. The action-options
    trigger is owned by ``PlayerCharacter.at_post_move`` (the shared post-move
    lifecycle), which every successful hooks-enabled relocation — ordinary
    traversal and direct ``move_to()`` alike — reaches (action-options-wiring-
    hardening design D2).
    """
    from world.rules.map_knowledge import record_arrival
    from world.rules.movement import charge_movement
    from world.rules.onboarding import observe_room_entry
    from world.rules.party import follow_companions

    charge_movement(traversing_object, cost_key)
    record_arrival(traversing_object)
    follow_companions(
        traversing_object,
        source_location,
        destination=destination,
        wilderness_coordinates=wilderness_coordinates,
        wilderness_source_coordinates=wilderness_source_coordinates,
        wilderness_name=wilderness_name,
    )
    observe_room_entry(traversing_object)


class MovementCostMixin:
    """Completes a successful player traversal through the shared boundary.

    Hooks ``at_post_traverse`` — which Evennia's stock ``DefaultExit.at_traverse``
    calls only from its successful-``move_to()`` branch — rather than inspecting
    ``at_traverse``'s own return value, which is ``None`` in both branches
    (map-movement-clock design.md D-2). A locked exit never reaches this hook
    (the access check runs first), and a vetoed ``at_pre_move`` aborts before it
    (design.md D-6); neither needs a guard here. On success the traversal runs
    ``after_successful_movement`` — charging the ``movement_cost_key`` cost,
    recording the destination node through ``world.rules.map_knowledge.
    record_arrival`` (map-knowledge-minimap design D3), moving companions, and
    running the onboarding room-entry observer (onboarding-skip coverage design
    D1) — all no-ops for anything that is not a ``PlayerCharacter``.

    ``at_traverse`` is overridden ONLY to open the movement-settlement boundary
    (movement-settlement-atomicity design D5): the stock traversal, relocation,
    and every success-path step above run inside one outer settlement
    transaction, and a failure is compensated before it surfaces, so a failing
    charge can never leave the traverser relocated. The traversal itself is
    delegated to ``super().at_traverse`` and its return value is not inspected
    or reinterpreted — it stays ``None`` on both branches, and success detection
    remains with ``at_post_traverse`` and the callers' location checks.
    """

    movement_cost_key: str = "move"
    # Opt-in per-exit flight gate (movement-skill-waiver). Off for every
    # shipped exit; future map content sets it True on its exit typeclass.
    requires_flight: bool = False

    def access(
        self,
        accessing_obj,
        access_type="access",
        default=False,
        no_superuser_bypass=False,
        **kwargs,
    ):
        """Deny ``traverse`` access on a flight-required exit to non-owners.

        Runs alongside every other lock on the exit: the flight gate is an
        additional access condition, so a denied traverser hits the same
        locked-exit path (never reaches ``at_traverse``, never charges, never
        records) as a lock-denied one. Superusers keep the stock lock-bypass
        semantics (unless ``no_superuser_bypass`` is set), so an admin can
        always reach a flight-required area. Only the ``traverse`` access type
        is gated; viewing, examining, and all other access types are untouched.
        """
        if (
            access_type == "traverse"
            and self.requires_flight
            and not self._owns_movement_waiver(accessing_obj)
            and not self._has_lock_bypass(accessing_obj, no_superuser_bypass)
        ):
            return False
        return super().access(
            accessing_obj,
            access_type,
            default=default,
            no_superuser_bypass=no_superuser_bypass,
            **kwargs,
        )

    def _owns_movement_waiver(self, traversing_object) -> bool:
        """Return whether the traverser owns ``flight`` or ``flash_step``."""
        skills = getattr(traversing_object, "skills", None)
        if skills is None:
            return False
        owned = set(skills.owned_keys())
        return bool(owned & {"flight", "flash_step"})

    def _has_lock_bypass(self, accessing_obj, no_superuser_bypass: bool) -> bool:
        """Mirror Evennia's stock lock-bypass (superuser) semantics.

        The lock handler grants a superuser every access unless
        ``no_superuser_bypass`` is set; the flight gate must not be stricter
        than every other lock on the same exit.
        """
        if no_superuser_bypass:
            return False
        try:
            if accessing_obj.locks.lock_bypass:
                return True
        except AttributeError:
            pass
        if getattr(accessing_obj, "is_superuser", False):
            return True
        account = getattr(accessing_obj, "account", None)
        return bool(getattr(account, "is_superuser", False))

    def at_post_traverse(self, traversing_object, source_location, **kwargs):
        super().at_post_traverse(traversing_object, source_location, **kwargs)
        after_successful_movement(
            traversing_object,
            source_location,
            cost_key=self.movement_cost_key,
            destination=traversing_object.location,
        )

    def at_traverse(self, traversing_object, target_location, **kwargs):
        """Open the movement-settlement boundary around the stock traversal.

        Covers the plain ``Exit`` and ``CostedXYZExit`` lineages (neither
        ``DefaultExit`` nor ``XYZExit`` overrides ``at_traverse``, so the MRO
        reaches this mixin). The boundary (``settle_movement``) wraps the
        relocation, the clock charge, map-knowledge recording, companion
        following, and the onboarding observer in one outer database
        transaction and compensates every Evennia cache surface when any step
        fails (movement-settlement-atomicity design D5).
        """
        stock_traversal = super().at_traverse

        def traverse_stock():
            return stock_traversal(traversing_object, target_location, **kwargs)

        return settle_movement(
            traversing_object,
            traversing_object.location,
            destination=target_location,
            traverse=traverse_stock,
        )


class Exit(MovementCostMixin, ObjectParent, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property and overrides some hooks
    and methods to represent the exits.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects child classes like this.

    """

    pass


class CostedXYZExit(MovementCostMixin, XYZExit):
    """An xyzgrid exit that charges the ordinary ``move`` cost on traversal.

    Every coordinate tag, ``.xyz``/``.xyz_destination`` property, and
    ``.create()`` behavior is inherited from the contrib ``XYZExit`` unchanged;
    this class adds only the movement-cost hook (map-movement-clock design.md
    D-3).
    """


def _grid_room_for_anchor(anchor_key: str):
    """Return the grid room this anchor's wilderness gate is attached to.

    Looked up through the gate exit itself (rather than from a coordinate) so
    the return target is exactly the room the character left from, wherever
    ``sync_wilderness()`` placed the gate.
    """

    for gate in WildernessGateExit.objects.all():
        if gate.db.anchor_key == anchor_key:
            return gate.location
    return None


class WildernessGateExit(Exit):
    """Ordinary Exit at a grid room (e.g. capital_altoria's North Gate) whose
    at_traverse is fully overridden -- mirrors WildernessExit's own pattern of
    ignoring target_location entirely. db.anchor_key is set by sync_wilderness()
    at creation time -- it is NOT optional, and a gate exit created without it
    will KeyError on first use (map-wilderness design.md D-7). A successful
    entry charges wilderness_move, records the destination ``wild:`` node
    (map-knowledge-minimap design D3), and completes through the shared
    ``after_successful_movement`` boundary (onboarding-skip coverage design D1).
    The whole entry body runs inside the movement-settlement boundary
    (movement-settlement-atomicity design D5), so a failing charge returns the
    traverser to the grid room with every cache surface reconciled.
    """

    def at_traverse(self, traversing_object, target_location, **kwargs):
        entry = WILDERNESS_ENTRY_REGISTRY[self.db.anchor_key]
        source_location = traversing_object.location

        def gate_traversal():
            # Honor the same at_pre_move veto every other exit in the game
            # honors, so entering the wilderness never silently bypasses a
            # future movement-blocking convention (combat lock, restraint,
            # quest gating).
            if not traversing_object.at_pre_move(None):
                return False

            ok = enter_wilderness(
                traversing_object, coordinates=entry.wilderness_xy, name=WILDERNESS_NAME
            )
            if not ok:
                return False

            if source_location:
                source_location.msg_contents(
                    f"{traversing_object.key} leaves into the wilderness.",
                    exclude=[traversing_object],
                )
            traversing_object.location.msg_contents(
                f"{traversing_object.key} arrives from {source_location}.",
                exclude=[traversing_object],
            )
            traversing_object.at_post_move(None)
            after_successful_movement(
                traversing_object,
                source_location,
                cost_key="wilderness_move",
                wilderness_coordinates=entry.wilderness_xy,
                wilderness_name=WILDERNESS_NAME,
            )
            return True

        return settle_movement(
            traversing_object,
            source_location,
            wilderness_coordinates=entry.wilderness_xy,
            traverse=gate_traversal,
        )


class WildernessReturnExit(WildernessExit):
    """The wilderness's own exit typeclass: routes exactly one registered
    coordinate-and-direction pair (the entry coordinate, direction ``"south"``)
    back into the grid room, and routes everything else like a stock
    WildernessExit. The clock cost is charged on EVERY successful traversal --
    special-cased return branch and ordinary fallback alike -- so no wilderness
    step is free (map-wilderness design.md D-6's correction note). Every
    successful step also records its destination node through
    ``record_arrival`` (map-knowledge-minimap design D3); both branches
    complete through the shared ``after_successful_movement`` boundary
    (onboarding-skip coverage design D1). Both branches run inside the
    movement-settlement boundary (movement-settlement-atomicity design D5), and
    the return-branch falsy-return-with-relocation case (a ``move_to`` hook
    raising after relocation) is compensated as a failure.
    """

    def at_traverse(self, traversing_object, target_location):
        itemcoordinates = self.location.wilderness.db.itemcoordinates
        current = itemcoordinates[traversing_object]
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            if current == entry.wilderness_xy and self.key == "south":
                grid_room = _grid_room_for_anchor(entry.anchor_key)
                if grid_room is None:
                    # Misconfiguration (gate exit missing or wrong anchor_key):
                    # do not report success or charge time for a move that
                    # cannot happen -- the spec's "failed traversal does not
                    # advance the clock" applies here too.
                    return False

                def return_traversal():
                    if not traversing_object.move_to(grid_room, quiet=False):
                        return False
                    after_successful_movement(
                        traversing_object,
                        self.location,
                        cost_key="wilderness_move",
                        destination=grid_room,
                        wilderness_source_coordinates=current,
                    )
                    return True

                return settle_movement(
                    traversing_object,
                    self.location,
                    destination=grid_room,
                    wilderness_source_coordinates=current,
                    traverse=return_traversal,
                )
        # ORDINARY wilderness movement -- every coordinate/direction that is not
        # a registered gateway. Not free: a successful step still pays
        # wilderness_move; only the routing decision is gated.
        stock_step = super().at_traverse

        def step_traversal():
            result = stock_step(traversing_object, target_location)
            if result:
                after_successful_movement(
                    traversing_object,
                    self.location,
                    cost_key="wilderness_move",
                    wilderness_coordinates=traversing_object.location.coordinates,
                    wilderness_source_coordinates=current,
                )
            return result

        return settle_movement(
            traversing_object,
            self.location,
            wilderness_coordinates=traversing_object.location.coordinates,
            wilderness_source_coordinates=current,
            traverse=step_traversal,
        )
