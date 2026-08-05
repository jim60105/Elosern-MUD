"""Duplicate-rejecting presenter registry with isolated exception handling.

The registry owns the stable panel allowlist, each panel's schema version, and
its unavailable builder. Presenters execute under isolation: an exception is
logged with the panel name and a bounded correlation ID, then converted to the
exact common unavailable payload so one broken presenter cannot suppress other
panels or narrative output.
"""

from collections.abc import Callable
from dataclasses import dataclass
import secrets
from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    ProtocolValidationError,
    _validate_identifier,
    _validate_panel_name,
    unavailable_payload,
)

# Stable unavailable reasons. The non-internal form carries no correlation ID.
UNAVAILABLE_REASON = ("presentation_unavailable", "目前無法顯示此介面")
_INTERNAL_REASON_CODE = "internal_presenter_error"
_INTERNAL_REASON_MESSAGE = "此介面暫時無法使用"


@dataclass(frozen=True)
class PresenterSpec:
    """One registered panel definition.

    Attributes:
        name: The stable lowercase panel name used on the wire.
        schema_version: The version of this panel's available/unavailable form.
        unavailable_reason: A ``(code, message)`` pair used when canonical
            data is missing or malformed. Safe for the player to see.
        presenter: A callable receiving a :class:`PresentationContext` and
            returning a JSON-safe available payload (including
            ``available: True``).
    """

    name: str
    schema_version: int
    unavailable_reason: tuple[str, str]
    presenter: Callable[[PresentationContext], dict[str, Any]]


class PanelUnavailableError(RuntimeError):
    """A presenter cannot read required canonical data without mutation.

    Raised by a presenter to request its registry-owned non-internal
    unavailable payload (no correlation ID) instead of an internal-failure
    payload.
    """


class PresentationRegistry:
    """A finite allowlist of stable panel names with duplicate rejection.

    Construction fails fast on duplicate names. Unknown names are never exposed
    to the coordinator; ``render`` converts every presenter failure into the
    registry-owned unavailable payload for that panel.
    """

    def __init__(self, name: str = "presentation") -> None:
        self.name = name
        self._specs: dict[str, PresenterSpec] = {}

    def register(self, spec: PresenterSpec) -> None:
        panel_name = _validate_panel_name(spec.name)
        if panel_name in self._specs:
            raise ProtocolValidationError(
                f"duplicate panel registration {panel_name!r}"
            )
        if not isinstance(spec.schema_version, int) or spec.schema_version < 1:
            raise ProtocolValidationError("schema_version must be a positive integer")
        _validate_identifier(spec.unavailable_reason[0], "unavailable reason code")
        self._specs[panel_name] = spec

    @property
    def panel_names(self) -> frozenset[str]:
        """Return the immutable set of registered stable panel names."""
        return frozenset(self._specs)

    def spec(self, panel_name: str) -> PresenterSpec:
        """Return the registered spec for ``panel_name`` or raise."""
        if panel_name not in self._specs:
            raise KeyError(f"unknown panel {panel_name!r}")
        return self._specs[panel_name]

    def build_unavailable(
        self,
        panel_name: str,
        *,
        internal: bool = False,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the exact common unavailable payload owned by a panel spec.

        ``internal=True`` selects the generic internal-failure reason and a
        bounded correlation ID; the ordinary path uses the panel's stable
        reason without a correlation ID.
        """
        spec = self.spec(panel_name)
        if internal:
            reason_code = _INTERNAL_REASON_CODE
            reason_message = _INTERNAL_REASON_MESSAGE
        else:
            reason_code, reason_message = spec.unavailable_reason
        return unavailable_payload(
            spec.schema_version,
            reason_code,
            reason_message,
            correlation_id=correlation_id if internal else None,
        )

    def render(self, panel_name: str, context: PresentationContext) -> dict[str, Any]:
        """Render one panel, converting any presenter exception to unavailable.

        The presenter runs outside the registry's own lookups so an exception
        cannot corrupt registry state. A correlation ID is allocated and logged
        for the internal-failure payload and diagnostics.
        """
        spec = self.spec(panel_name)
        try:
            payload = spec.presenter(context)
        except PanelUnavailableError:
            return self.build_unavailable(panel_name)
        except Exception:
            correlation_id = secrets.token_hex(16)
            try:
                from evennia.utils.logger import log_trace

                log_trace(
                    "presentation registry %r: panel %r failed with correlation %s"
                    % (self.name, panel_name, correlation_id)
                )
            except Exception:
                # Even without a configured logger, presenter failure is
                # isolated and the correlated unavailable payload still ships.
                pass
            return self.build_unavailable(panel_name, internal=True, correlation_id=correlation_id)
        if not isinstance(payload, dict) or payload.get("available") is not True:
            raise ProtocolValidationError(
                f"panel {panel_name!r} returned a non-available payload"
            )
        return payload


def build_production_registry() -> PresentationRegistry:
    """Build the production registry containing the ``status`` and
    ``context_actions`` panels.

    The status presenter lives in ``web.webclient.presentation.status`` and the
    combat panel in ``web.webclient.presentation.combat_panel``; both are
    imported here (rather than at module import) so this module stays
    importable while a presenter is being developed.
    """
    from web.webclient.presentation.art import art_presenter
    from web.webclient.presentation.character import character_presenter
    from web.webclient.presentation.combat_panel import context_actions_presenter
    from web.webclient.presentation.creation import creation_presenter
    from web.webclient.presentation.exploration import exploration_presenter
    from web.webclient.presentation.local_map import local_map_presenter
    from web.webclient.presentation.services import services_presenter
    from web.webclient.presentation.status import status_presenter

    registry = PresentationRegistry("elosern")
    registry.register(
        PresenterSpec(
            name="art",
            schema_version=1,
            unavailable_reason=("art_unavailable", "場景圖像目前無法顯示"),
            presenter=art_presenter,
        )
    )
    registry.register(
        PresenterSpec(
            name="status",
            schema_version=1,
            unavailable_reason=UNAVAILABLE_REASON,
            presenter=status_presenter,
        )
    )
    registry.register(
        PresenterSpec(
            name="context_actions",
            schema_version=2,
            unavailable_reason=UNAVAILABLE_REASON,
            presenter=context_actions_presenter,
        )
    )
    registry.register(
        PresenterSpec(
            name="local_map",
            schema_version=1,
            unavailable_reason=("map_unavailable", "區域地圖目前無法顯示"),
            presenter=local_map_presenter,
        )
    )
    registry.register(
        PresenterSpec(
            name="services",
            schema_version=1,
            unavailable_reason=("services_unavailable", "服務選單目前無法顯示"),
            presenter=services_presenter,
        )
    )
    registry.register(
        PresenterSpec(
            name="creation",
            schema_version=1,
            unavailable_reason=("creation_unavailable", "角色建立畫面目前無法顯示"),
            presenter=creation_presenter,
        )
    )
    registry.register(
        PresenterSpec(
            name="exploration",
            schema_version=1,
            unavailable_reason=("exploration_unavailable", "探索選單目前無法顯示"),
            presenter=exploration_presenter,
        )
    )
    registry.register(
        PresenterSpec(
            name="character",
            schema_version=1,
            unavailable_reason=("character_unavailable", "角色狀態目前無法顯示"),
            presenter=character_presenter,
        )
    )
    return registry
