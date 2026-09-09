"""Single store-root confinement helper for every gallery file operation.

One function decides whether a stored identity may be touched on disk: the
path must be a relative, component-clean root descendant whose every existing
component is a real (non-symlink) directory, and whose fully-resolved target
is strictly under the root. ``resolved_under_root`` is the generic discipline;
``resolved_under_store_root`` pins it to ``ART_STORE_ROOT``. Card deletion in
``world/art/gallery.py``, the resolution chain's identity checks, and the
media route's gallery/defaults branches all resolve through here, so no code
path can ever touch a file outside its own root.

Reads ``settings.ART_STORE_ROOT`` per call (never at import) so
``override_settings`` redirects the store exactly like the queue and worker
do. Imports only stdlib plus Django settings — never the art worker, the
sd-webui client, or any connectivity surface — keeping the deterministic-path
and connectivity import-boundary contracts intact.
"""

from pathlib import Path

from django.conf import settings


def resolved_under_root(root: Path, identity: str) -> Path | None:
    """Return ``identity`` resolved strictly under ``root``, or None.

    Rejected (returning ``None``, never raising): an empty or absolute
    identity, any ``..`` component, an identity equal to the root itself, a
    path resolving outside the root, and any existing symlinked component
    between the root and the target — even a symlink whose target is another
    location inside the root, so a planted link can never masquerade as a
    confined file. ``resolve()`` failures (``OSError``) are ``None`` too.
    A ``ValueError`` from ``resolve()`` (e.g. an embedded NUL) refuses the
    identity the same way.
    """
    if not isinstance(identity, str) or not identity or "\x00" in identity:
        return None
    candidate = Path(identity)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    root = Path(root)
    try:
        root_resolved = root.resolve()
        target = (root / candidate).resolve()
    except (OSError, ValueError):  # observability: ignore R2: unresolvable path is the caller's refusal signal
        return None
    if target == root_resolved or root_resolved not in target.parents:
        return None
    # Reject symlinked components between the root and the target: walk every
    # un-resolved component and refuse the first existing symlink — even one
    # whose target is another location inside the root. A dangling (missing,
    # non-link) final component stays legal; deleting a missing file is the
    # caller's bounded no-op.
    path = root
    for part in candidate.parts:
        path = path / part
        if path.is_symlink():
            return None
    return target


def resolved_under_store_root(identity: str) -> Path | None:
    """Return ``identity`` resolved strictly under ``ART_STORE_ROOT``, or None.

    The store-root pin of :func:`resolved_under_root`, read per call so
    ``override_settings`` redirects the store exactly like the queue and
    worker do.
    """
    return resolved_under_root(Path(settings.ART_STORE_ROOT), identity)
