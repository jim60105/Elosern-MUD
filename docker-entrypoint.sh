#!/bin/sh
set -eu

umask 0002
# Apply a world-save restore staged by the GM portal (gm-portal-s5-saves)
# before migrations, so an older save is migrated forward. The final image
# has no uv; /venv's python is the uv-synced project interpreter.
python -m server.saves.restore --apply-pending
evennia migrate --noinput
# Refresh the persistent static volume from the baked static tree (which
# includes the built Vue dist, webclient-vue-01-foundation) before serving.
evennia collectstatic --noinput
exec evennia start --log
