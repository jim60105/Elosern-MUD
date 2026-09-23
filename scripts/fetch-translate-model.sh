#!/usr/bin/env bash
# fetch-translate-model.sh — seed the prompt-translation model (host-only).
#
# The game server NEVER downloads the translation model (design D2 of
# add-ctranslate2-translate-backend): an operator seeds the model directory
# with this script, on the HOST, and mounts it. An unseeded directory is a
# bounded `art_translate_unavailable`, never a fetch.
#
# It downloads the Argos Open Tech zh->en translation package
# (translate-zh_en-1_9.argosmodel, a zip archive), verifies the archive and
# the expected layout, and unpacks exactly the pieces the backend requires
# into TARGET_DIR:
#
#   TARGET_DIR/
#   ├── model/                OpenNMT CTranslate2 model directory
#   │   ├── config.json
#   │   ├── model.bin
#   │   └── shared_vocabulary.json
#   ├── sentencepiece.model   SentencePiece source model
#   └── README.md             package provenance/licence (informational)
#
# The `stanza/` entry of the package (sentence-boundary data for the Argos
# wrapper) is deliberately not unpacked: the translation seam already splits
# on lines. The licence: the packaged model is derived from the OPUS-MT
# zh->en model, licensed CC-BY 4.0 (stated in the package README).
#
# Usage:
#   scripts/fetch-translate-model.sh [TARGET_DIR] [--force]
#
#   TARGET_DIR  where to write the seed (default: <repo>/server/.translate,
#               the bare-metal ART_TRANSLATE_MODEL_DIR)
#   --force     replace an existing seed at TARGET_DIR (otherwise the script
#               fails if one is present)
#
# The script prints where to mount the result, including a one-shot command
# for seeding the compose `evennia-translate` named volume.

set -euo pipefail

PKG="translate-zh_en-1_9"
URL="https://argos-net.com/v1/${PKG}.argosmodel"
REQUIRED_ENTRIES=(
  "${PKG}/model/config.json"
  "${PKG}/model/model.bin"
  "${PKG}/sentencepiece.model"
)

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." &> /dev/null && pwd)"
DEFAULT_TARGET="${REPO_ROOT}/server/.translate"

target="${DEFAULT_TARGET}"
force=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      force=1
      shift
      ;;
    -h|--help)
      sed -n '2,32p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      target="$1"
      shift
      ;;
  esac
done

for tool in curl unzip; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "ERROR: ${tool} is required but not installed" >&2
    exit 1
  fi
done

if [[ -e "${target}/model" || -e "${target}/sentencepiece.model" ]]; then
  if [[ "${force}" -ne 1 ]]; then
    echo "ERROR: ${target} already contains a model seed." >&2
    echo "       Pass --force to replace it." >&2
    exit 1
  fi
fi

staging="$(mktemp -d "${TMPDIR:-/tmp}/translate-seed.XXXXXX")"
trap 'rm -rf "${staging}"' EXIT INT TERM
archive="${staging}/${PKG}.argosmodel"
replacement="${staging}/replacement"
mkdir -p "${replacement}"

echo "== Downloading ${PKG} =="
if ! curl --fail --location --output "${archive}" "${URL}"; then
  echo "ERROR: download failed: ${URL}" >&2
  exit 1
fi

echo "== Verifying archive =="
if ! unzip -t "${archive}" >/dev/null 2>&1; then
  echo "ERROR: downloaded file is not a valid zip archive (${URL})" >&2
  exit 1
fi

listed="$(unzip -l "${archive}")"
members="$(unzip -Z1 "${archive}")"
while IFS= read -r member; do
  case "${member}" in
    "${PKG}/"*) ;;
    "")
      continue
      ;;
    *)
      echo "ERROR: archive member outside the package directory: ${member}" >&2
      exit 1
      ;;
  esac
  case "${member}" in
    /*|*".."*)
      echo "ERROR: unsafe archive member path: ${member}" >&2
      exit 1
      ;;
  esac
done <<<"${members}"
for entry in "${REQUIRED_ENTRIES[@]}"; do
  if ! grep -q "${entry}" <<<"${listed}"; then
    echo "ERROR: unexpected archive layout — missing ${entry}" >&2
    exit 1
  fi
done

echo "== Unpacking =="
unzip -q "${archive}" "${PKG}/model/*" "${PKG}/sentencepiece.model" "${PKG}/README.md" -d "${staging}/unpacked"

model_dir="${staging}/unpacked/${PKG}/model"
sp_model="${staging}/unpacked/${PKG}/sentencepiece.model"
for check in "${model_dir}/config.json" "${model_dir}/model.bin" "${sp_model}"; do
  if [[ ! -f "${check}" ]]; then
    echo "ERROR: unpacked layout is incomplete — missing ${check}" >&2
    exit 1
  fi
done

# Land the validated seed into the replacement directory first, then swap it
# in atomically — the live model directory is never destroyed before its
# replacement is complete, so an interrupted run cannot leave the deployment
# unseeded or half-seeded.
cp -a "${model_dir}" "${replacement}/model"
cp -a "${sp_model}" "${replacement}/sentencepiece.model"
cp -a "${staging}/unpacked/${PKG}/README.md" "${replacement}/README.md"
mkdir -p "$(dirname -- "${target}")"
if [[ -e "${target}" ]]; then
  rm -rf "${target}.old-seed"
  mv "${target}" "${target}.old-seed"
fi
mv "${replacement}" "${target}"
rm -rf "${target}.old-seed"

echo ""
echo "✅ Seeded ${target}:"
echo "   - model/              (CTranslate2 model: config.json + model.bin)"
echo "   - sentencepiece.model (SentencePiece source model)"
echo "   - README.md           (package provenance; model is CC-BY 4.0, OPUS-MT-derived)"
echo ""
echo "Bare-metal: ART_TRANSLATE_MODEL_DIR=${target} is the default; set"
echo "ART_TRANSLATE_ENABLED=true in .env and restart the server."
echo ""
echo "Compose (seed the named volume once, then restart):"
echo "  podman compose up -d      # creates the evennia-translate volume"
echo "  podman run --rm \\"
echo "    -v evennia-translate:/app/server/.translate \\"
echo "    -v '${target}':/seed:ro,z \\"
echo "    --entrypoint /bin/sh docker.io/library/busybox \\"
echo "    -c 'cp -a /seed/. /app/server/.translate/'"
echo ""
echo "An unseeded volume degrades safely: one art_translate_failed warn per"
echo "generation and the authored prompt is used — the image is still made."