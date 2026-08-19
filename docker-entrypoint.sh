#!/bin/sh
set -eu

umask 0002
evennia migrate --noinput
# Refresh the persistent static volume from the baked static tree (which
# includes the built Vue dist, webclient-vue-01-foundation) before serving.
evennia collectstatic --noinput
exec evennia start --log
