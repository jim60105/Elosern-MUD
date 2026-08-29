# webclient-exploration-menu Delta Specification

## REMOVED Requirements

### Requirement: The legacy client tolerates the version-5 character payload
**Reason**: The requirement was explicitly transitional — "Until the Vue
breakdown renderer lands" — and P7 IS that renderer. With the breakdown UI
shipped, the v4 tolerance window closes: schema version 5 becomes the only
accepted character payload version at every wire validator (Python, legacy
JS, Vue store path), and the retained v4 validator branches, v4 fixtures,
and v4 branch tests are deleted (unreleased project, no compatibility
requirement). The legacy client keeps its totals-only rendering, now at v5
exclusively.
**Migration**: No users exist. Existing consumers must send version-5
character payloads only; a v4 payload (available or unavailable form)
rejects at every wire validator. The Node-gate fixtures migrate to exact v5
shapes, and the totals-rendering guarantee moves into a single-version v5
test (layers ignored, no console errors).
