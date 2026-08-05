ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Harbor terminus-2 needs these before it can create the agent's tmux session.
# Baking them in removes setup-time package downloads from the benchmark path.
ARG BUILD_HTTP_PROXY
ARG BUILD_HTTPS_PROXY
# Task images embed a retired bridge proxy.  Clear it in the derived image;
# build-time access is passed explicitly and never persisted.
ENV HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy=
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    export HTTP_PROXY="${BUILD_HTTP_PROXY}" HTTPS_PROXY="${BUILD_HTTPS_PROXY}" http_proxy="${BUILD_HTTP_PROXY}" https_proxy="${BUILD_HTTPS_PROXY}"; \
    for attempt in 1 2 3 4 5; do \
      DEBIAN_FRONTEND=noninteractive apt-get update \
      && DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=5 install -y --no-install-recommends tmux asciinema \
      && exit 0; \
    done; \
    exit 1
