#!/bin/sh
# Prepare the named official-artwork volume from one trusted operator archive.
#
# Deployment-time only (official-artwork-deployment): the game process never
# runs this script, never extracts an archive, and never fetches anything. The
# compose `artwork-prepare` service runs it in a one-shot container with write
# access to the `evennia-art-official` volume, the operator's archive directory
# mounted read-only, and no network. The archive is trusted operator supply -
# never a player upload and never a game-selected remote source.
#
# Interface (environment variables; positional arguments are ignored because a
# Compose service entrypoint inherits the image's default command as arguments):
#
#   ART_OFFICIAL_ARCHIVE         Archive to install. Unset or empty = no-op:
#                                the prepared tree is neither erased nor
#                                re-extracted. A value containing "/" is used
#                                as a path; a bare name is resolved inside
#                                ART_OFFICIAL_ARCHIVE_DIR.
#   ART_OFFICIAL_ARCHIVE_DIR     Directory holding the archives (default
#                                /app/art-official-archives, where the compose
#                                service mounts the host archive folder).
#   ART_OFFICIAL_CONTENT_DIR     Prepared content subdirectory of the mounted
#                                volume (default /app/art-official/content).
#                                The volume root itself is never replaced;
#                                configure ART_OFFICIAL_ROOT to this
#                                subdirectory.
#   ART_OFFICIAL_MAX_ENTRIES     Maximum archive member count (default 50000).
#   ART_OFFICIAL_MAX_FILE_BYTES  Maximum declared size of one member
#                                (default 67108864 = 64 MiB).
#   ART_OFFICIAL_MAX_TOTAL_BYTES Maximum declared size of all members
#                                (default 8589934592 = 8 GiB).
#
# Safety contract, enforced before anything is written: every member is listed
# first, and absolute paths, parent-directory traversal, link entries
# (symlinks and hard links), device/fifo/socket members, and the entry, per-file
# and total size caps are refused. Extraction runs into a fresh empty staging
# directory on the same filesystem as the destination, so the prepared tree is
# only ever replaced by a completed extraction, moved into place by renames: a
# failed or interrupted run leaves the previously prepared tree unchanged (and
# the next invocation restores it after an interruption between the renames).
#
# The archive is read with the container's native tar. Uncompressed and
# gzip-compressed tar archives are the supported inputs (the runtime image ships
# tar and gzip and nothing else that unpacks archives); prepare any other
# archive format with host tooling, or use the plain-directory or S3 procedure.
# Member listing parses GNU tar's `-tvf` line shape (type, permissions,
# owner/group, size, ISO date, time, name); the C locale below keeps that shape
# and the diagnostics locale-independent, and tar's own refusal of traversal and
# absolute members is the backstop asserted by the repository tests.

set -eu

# Deterministic, locale-independent tar listings and diagnostics.
LC_ALL=C
export LC_ALL

content_dir=${ART_OFFICIAL_CONTENT_DIR:-/app/art-official/content}
archive_dir=${ART_OFFICIAL_ARCHIVE_DIR:-/app/art-official-archives}
archive=${ART_OFFICIAL_ARCHIVE:-}
max_entries=${ART_OFFICIAL_MAX_ENTRIES:-50000}
max_file_bytes=${ART_OFFICIAL_MAX_FILE_BYTES:-67108864}
max_total_bytes=${ART_OFFICIAL_MAX_TOTAL_BYTES:-8589934592}

listing=''
staging=''
previous=''
swapping=''

log() {
    printf 'prepare-official-artwork: %s\n' "$*" >&2
}

die() {
    printf 'prepare-official-artwork: ERROR: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    status=$?
    if [ -n "$swapping" ] && [ -n "$previous" ] && [ -d "$previous" ] &&
        [ ! -e "$content_dir" ]; then
        # Interrupted between the two install renames: put the previously
        # prepared tree back before leaving.
        mv -T -- "$previous" "$content_dir" 2>/dev/null || true
    fi
    if [ -n "$staging" ] && [ -d "$staging" ]; then
        rm -rf -- "$staging" || true
    fi
    if [ -n "$listing" ]; then
        rm -f -- "$listing" || true
    fi
    exit "$status"
}

trap cleanup EXIT
trap 'exit 1' HUP INT TERM

require_positive_integer() {
    case $2 in
        '' | *[!0-9]*) die "$1 must be a positive integer, got '$2'" ;;
    esac
    if [ "$2" -le 0 ]; then
        die "$1 must be a positive integer, got '$2'"
    fi
}

require_positive_integer ART_OFFICIAL_MAX_ENTRIES "$max_entries"
require_positive_integer ART_OFFICIAL_MAX_FILE_BYTES "$max_file_bytes"
require_positive_integer ART_OFFICIAL_MAX_TOTAL_BYTES "$max_total_bytes"

if [ "$#" -gt 0 ]; then
    log "ignoring unexpected arguments: $*"
fi

if [ -z "$archive" ]; then
    log "no archive supplied; leaving ${content_dir} unchanged"
    exit 0
fi

case $archive in
    */*) archive_path=$archive ;;
    *) archive_path=$archive_dir/$archive ;;
esac

[ -f "$archive_path" ] || die "archive is not a regular file: $archive_path"
[ -r "$archive_path" ] || die "archive is not readable: $archive_path"

content_parent=$(dirname -- "$content_dir")
content_name=$(basename -- "$content_dir")
if [ -z "$content_name" ] || [ "$content_name" = "/" ] || [ "$content_name" = "." ]; then
    die "ART_OFFICIAL_CONTENT_DIR does not name a directory: $content_dir"
fi

# The listing is scratch, never state: keep it in the container tmpfs rather
# than anywhere a caller-set TMPDIR could point (for example the volume).
listing=$(TMPDIR=/tmp mktemp) || die "cannot create a temporary listing file"

# Bounded count pass: a hostile or huge archive cannot make the listing, which
# is written on the next pass, unbounded. A failing tar is masked here by the
# pipeline's last command, so the next pass's `|| die` is the real gate.
counted=$(tar -tf "$archive_path" 2>/dev/null | head -n "$((max_entries + 1))" | wc -l)
counted=$(printf '%s' "$counted" | tr -d ' ')
if [ "$counted" -gt "$max_entries" ]; then
    die "archive has more than $max_entries members"
fi

tar -tvf "$archive_path" > "$listing" 2>/dev/null ||
    die "archive is not a readable tar archive (uncompressed or gzip-compressed tar is supported): $archive_path"

# Validate every member before anything is written.
member_count=0
total_bytes=0
while IFS= read -r line; do
    [ -n "$line" ] || continue
    member_type=${line%"${line#?}"}
    remaining=${line#?}
    # Word splitting is the listing parser: perms, owner/group, size, date,
    # time, then the name (which may contain spaces).
    # shellcheck disable=SC2086
    set -- $remaining
    [ "$#" -ge 6 ] || die "archive listing line is malformed: $line"
    member_size=$3
    shift 5
    member_name=$*
    [ -n "$member_name" ] || die "archive member has no name"

    case $member_type in
        '-' | d) ;;
        l | h) die "refusing link entry in the archive: $member_name" ;;
        *) die "refusing non-regular archive member (type '$member_type'): $member_name" ;;
    esac

    case $member_size in
        '' | *[!0-9]*) die "archive member has no numeric size: $member_name" ;;
    esac
    if [ "${#member_size}" -gt 18 ]; then
        die "archive member declares an implausible size: $member_name"
    fi
    if [ "$member_size" -gt "$max_file_bytes" ]; then
        die "archive member exceeds ART_OFFICIAL_MAX_FILE_BYTES ($max_file_bytes bytes): $member_name"
    fi
    total_bytes=$((total_bytes + member_size))
    if [ "$total_bytes" -gt "$max_total_bytes" ]; then
        die "archive exceeds ART_OFFICIAL_MAX_TOTAL_BYTES ($max_total_bytes bytes)"
    fi
    member_count=$((member_count + 1))
    if [ "$member_count" -gt "$max_entries" ]; then
        die "archive has more than $max_entries members"
    fi

    case $member_name in
        /*) die "refusing absolute path in the archive: $member_name" ;;
    esac
    remaining=$member_name
    while :; do
        case $remaining in
            */*) component=${remaining%%/*}; remaining=${remaining#*/} ;;
            *) component=$remaining; remaining='' ;;
        esac
        if [ "$component" = '..' ]; then
            die "refusing parent-directory traversal in the archive: $member_name"
        fi
        [ -n "$remaining" ] || break
    done
done < "$listing"

# The staging directory shares the destination's filesystem, so installing the
# finished tree is a rename and no partial output can replace the prepared tree.
mkdir -p -- "$content_parent" ||
    die "cannot create $content_parent (is the mounted volume writable?)"

# Recover leftovers of an earlier run that died before its cleanup: a leftover
# `previous` tree is either the last prepared tree (the install was
# interrupted) or a stale copy of it (the install finished).
for candidate in "$content_parent"/."$content_name".previous.*; do
    [ -e "$candidate" ] || continue
    if [ -e "$content_dir" ] || [ -L "$content_dir" ]; then
        rm -rf -- "$candidate" || die "cannot remove the leftover $candidate"
    else
        log "restoring $content_dir from an interrupted earlier preparation"
        mv -T -- "$candidate" "$content_dir" ||
            die "cannot restore $content_dir from $candidate"
    fi
done
for candidate in "$content_parent"/."$content_name".prepare.*; do
    [ -e "$candidate" ] || continue
    log "removing leftover staging directory $candidate"
    rm -rf -- "$candidate" || die "cannot remove the leftover $candidate"
done

staging=$content_parent/.$content_name.prepare.$$
mkdir -- "$staging" || die "cannot create the staging directory $staging"

tar -xf "$archive_path" --no-same-owner --no-same-permissions -C "$staging" ||
    die "extraction failed; $content_dir is unchanged"

unsafe=$(find "$staging" -mindepth 1 ! -type d ! -type f -print | head -n 1)
if [ -n "$unsafe" ]; then
    die "extraction produced a non-regular entry: $unsafe"
fi

previous=$content_parent/.$content_name.previous.$$
swapping=1
if [ -e "$content_dir" ] || [ -L "$content_dir" ]; then
    if ! mv -T -- "$content_dir" "$previous"; then
        swapping=''
        die "cannot move the current $content_dir aside; nothing was replaced"
    fi
    if ! mv -T -- "$staging" "$content_dir"; then
        mv -T -- "$previous" "$content_dir" ||
            log "ERROR: restore $previous to $content_dir manually"
        die "cannot install the prepared tree; the previous tree was restored"
    fi
    swapping=''
    rm -rf -- "$previous" || log "warning: cannot remove the previous tree $previous"
    previous=''
else
    if ! mv -T -- "$staging" "$content_dir"; then
        swapping=''
        die "cannot install the prepared tree"
    fi
    swapping=''
fi
staging=''

if [ "$member_count" -eq 0 ]; then
    log "installed an empty tree (the archive has no members)"
fi
log "prepared $content_dir from $archive_path"
