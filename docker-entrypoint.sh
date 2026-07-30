#!/bin/sh
set -eu

umask 0002
evennia migrate --noinput
exec evennia start --log
