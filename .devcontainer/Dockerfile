FROM ubuntu:24.04
USER ubuntu
ARG DEBIAN_FRONTEND=noninteractive

# apt-get installs
USER root
RUN : \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        just \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
USER ubuntu

WORKDIR /workspaces/wakepy

# Install uv
ENV UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# Install dependencies
RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project


