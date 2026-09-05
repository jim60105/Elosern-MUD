# syntax=docker/dockerfile:1
ARG UID=1001
ARG VERSION=EDGE
ARG RELEASE=0

########################################
# Download stage
########################################
FROM docker.io/library/debian:bookworm-slim AS download

ARG TARGETARCH
ARG TARGETVARIANT

RUN --mount=type=cache,id=apt-$TARGETARCH$TARGETVARIANT,sharing=locked,target=/var/cache/apt \
    --mount=type=cache,id=aptlists-$TARGETARCH$TARGETVARIANT,sharing=locked,target=/var/lib/apt/lists \
    apt-get update && \
    apt-get install --yes --no-install-recommends ca-certificates curl

RUN case "${TARGETARCH}" in \
      amd64) DUMBINIT_ARCH="x86_64"; DUMBINIT_SHA256="e874b55f3279ca41415d290c512a7ba9d08f98041b28ae7c2acb19a545f1c4df" ;; \
      arm64) DUMBINIT_ARCH="aarch64"; DUMBINIT_SHA256="b7d648f97154a99c539b63c55979cd29f005f88430fb383007fe3458340b795e" ;; \
      *) echo "unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
    esac && \
    curl --fail --location --silent --show-error \
      "https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_${DUMBINIT_ARCH}" \
      --output /dumb-init && \
    echo "${DUMBINIT_SHA256}  /dumb-init" | sha256sum --check

########################################
# Build stage
########################################
FROM docker.io/library/python:3.13-slim AS builder

ARG TARGETARCH
ARG TARGETVARIANT

COPY --from=ghcr.io/astral-sh/uv@sha256:606e70c71c852d03f611b1e56a195d08648507018a7057fab82c4974c4eae105 /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/venv \
    VIRTUAL_ENV=/venv

WORKDIR /build

COPY --chown=root:0 pyproject.toml uv.lock ./
RUN --mount=type=cache,id=uv-$TARGETARCH$TARGETVARIANT,sharing=locked,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

########################################
# Vue dist build stage (webclient-vue-01-foundation)
########################################
FROM docker.io/library/node:24-slim AS vue-dist

ARG TARGETARCH
ARG TARGETVARIANT

WORKDIR /build

RUN corepack enable

COPY --chown=root:0 package.json pnpm-lock.yaml vite.config.js ./
RUN --mount=type=cache,id=pnpm-$TARGETARCH$TARGETVARIANT,sharing=locked,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

COPY --chown=root:0 web/ /build/web/
# Emits the stable-entry dist (index.js + index.css + hashed assets/) into the
# static tree; the app-layout stage copies it into the served image root.
RUN pnpm run build

########################################
# Application layout stage
########################################
FROM docker.io/library/python:3.13-slim AS app-layout

COPY --chown=root:0 --chmod=0755 docker-entrypoint.sh /app/docker-entrypoint.sh
COPY --chown=root:0 server/ /app/server/
COPY --chown=root:0 web/ /app/web/
COPY --chown=root:0 commands/ /app/commands/
COPY --chown=root:0 typeclasses/ /app/typeclasses/
COPY --chown=root:0 world/ /app/world/
COPY --chown=root:0 tools/ /app/tools/
# Vendored CC BY name corpus: world/lore/names.py parses it at import time, so
# the runtime tree must carry it (npc-namegen-lore-registry D8).
COPY --chown=root:0 third_party/ /app/third_party/
# Admin-facing prompt data: baked defaults survive image-only runs; the compose
# bind mount below overrides them read-only. World-readable so an external art
# worker can reuse the shipped fragments (design D11, unchanged worker contract).
COPY --chown=root:0 prompts/ /app/prompts/
# Vue SPA dist produced by the vue-dist stage, served from the project origin
# like every other web/static asset (webclient-vue-01-foundation, design D2).
COPY --chown=root:0 --from=vue-dist /build/web/static/webclient/app/dist/ /app/web/static/webclient/app/dist/

RUN find /app -type d -exec chmod 0755 {} + && \
    find /app -type f -exec chmod 0644 {} + && \
    chmod 0755 /app/docker-entrypoint.sh && \
    install -d -m 775 -o root -g 0 /app/server/db && \
    install -d -m 775 -o root -g 0 /app/server/logs && \
    install -d -m 775 -o root -g 0 /app/server/.static && \
    install -d -m 775 -o root -g 0 /app/server/.media && \
    install -d -m 775 -o root -g 0 /app/server/.art && \
    chmod 1775 /app/server

########################################
# Final stage
########################################
FROM docker.io/library/python:3.13-slim AS final

ARG UID

RUN pip uninstall --yes pip setuptools wheel
RUN groupadd --gid "$UID" evennia && \
    useradd --uid "$UID" --gid evennia --groups root --create-home --shell /usr/sbin/nologin evennia

# Linked-layer caching requires Podman 5.6 or later with Buildah 1.41 or later.
COPY --link --chown=root:0 --from=builder /venv /venv
COPY --link --chown=root:0 --chmod=0755 --from=download /dumb-init /usr/local/bin/dumb-init
COPY --link --chown=root:0 --from=app-layout /app /app

ENV PATH="/venv/bin:$PATH" \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
VOLUME ["/app/server/db", "/app/server/logs", "/app/server/.static", "/app/server/.media", "/app/server/.art"]
EXPOSE 4000 4001 4002
USER $UID
STOPSIGNAL SIGINT
ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]
CMD ["/app/docker-entrypoint.sh"]

ARG VERSION
ARG RELEASE
# Buildah does not invalidate LABEL cache entries for changed ARG values alone.
RUN test -n "$VERSION" && test -n "$RELEASE"
LABEL org.opencontainers.image.title="Elosern MUD" \
      org.opencontainers.image.description="Containerized Evennia foundation for the Elosern MUD." \
      org.opencontainers.image.source="https://github.com/jim60105/Elosern-MUD" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${RELEASE}" \
      org.opencontainers.image.licenses="UNLICENSED"
