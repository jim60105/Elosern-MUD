"""Single store-root confinement helper for every gallery file operation.

One function decides whether a stored identity may be touched on disk: the
path must be a relative, component-clean ``ART_STORE_ROOT`` descendant whose
every existing component is a real (non-symlink) directory, and whose
fully-resolved target is strictly under the root. Card deletion in
``world/art/gallery.py`` resolves through here, and later gallery changes
adopt it for every other filesystem touch, so no code path can ever unlink
outside the store root.

Reads ``settings.ART_STORE_ROOT`` per call (never at import) so
``override_settings`` redirects the store exactly like the queue and worker
do. Imports only stdlib plus Django settings — never the art worker, the
sd-webui client, or any connectivity surface — keeping the deterministic-path
and connectivity import-boundary contracts intact.
"""

from pathlib import Path

from django.conf import settings


def resolved_under_store_root(identity: str) -> Path | None:
    """Return ``identity`` resolved strictly under ``ART_STORE_ROOT``, or None.

    Rejected (returning ``None``, never raising): an empty or absolute
    identity, any ``..`` component, an identity equal to the root itself, a
    path resolving outside the root, and any existing symlinked component
    between the root and the target — even a symlink whose target is another
    location inside the root, so a planted link can never masquerade as a
    confined file. ``resolve()`` failures (``OSError``) are ``None`` too.
    """
    if not isinstance(identity, str) or not identity:
        return None
    candidate = Path(identity)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None
    root = Path(settings.ART_STORE_ROOT)
    try:
        root_resolved = root.resolve()
        target = (root / candidate).resolve()
    except OSError:  # observability: ignore R2: unresolvable path is the caller's refusal signal
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
