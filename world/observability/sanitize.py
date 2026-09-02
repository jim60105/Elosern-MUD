"""Log-safe renderers for values that can carry credentials.

Configured endpoint URLs may embed secrets (``user:password@host``
userinfo, ``?api_key=`` queries). Every ``endpoint`` context value must
pass through :func:`safe_endpoint` so operational logs keep the
identifying origin/path while losing the credential material.
"""

from urllib.parse import urlsplit, urlunsplit


def safe_endpoint(url: object) -> str:
    """Render one configured URL without userinfo, query, or fragment."""
    text = str(url)
    try:
        parts = urlsplit(text)
    except ValueError:
        return "[unparseable-url]"
    # rsplit drops userinfo even when no port follows the password.
    netloc = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))
