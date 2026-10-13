# DeerFlow Gateway for Railway (community template).
#
# Wraps the official image ghcr.io/bytedance/deer-flow-backend. Upstream's
# docker-compose bind-mounts config.yaml, extensions_config.json and skills/
# into this container at run time; Railway has no bind mounts, so this image
#   * bakes in the public skills of the SAME release tag as the image,
#   * renders config.yaml from Railway variables at start (railway/render_config.py),
#   * waits for Postgres and Redis to answer before starting (railway/wait_for_services.py),
#   * creates the first admin account over loopback (railway/bootstrap_admin.py),
#   * serves uvicorn on one dual-stack socket (railway/serve.py), so both
#     Railway's IPv4 healthcheck and IPv6 private networking reach it.
#
# Upgrade: change DEERFLOW_VERSION (image tag and skills tag move together).

ARG DEERFLOW_VERSION=v2.1.0

# ── Stage 1: fetch the public skills of the same release ────────────────────
FROM ghcr.io/bytedance/deer-flow-backend:${DEERFLOW_VERSION} AS skills
ARG DEERFLOW_VERSION
ADD https://codeload.github.com/bytedance/deer-flow/tar.gz/refs/tags/${DEERFLOW_VERSION} /tmp/deer-flow.tar.gz
RUN set -eux; \
    mkdir -p /out; \
    tar -xzf /tmp/deer-flow.tar.gz -C /out --strip-components=1 "deer-flow-${DEERFLOW_VERSION#v}/skills"; \
    test -f /out/skills/public/deep-research/SKILL.md

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM ghcr.io/bytedance/deer-flow-backend:${DEERFLOW_VERSION}

COPY --from=skills /out/skills /app/skills
COPY railway/ /opt/railway/
RUN chmod 0755 /opt/railway/entrypoint.sh

# Paths follow upstream docker/docker-compose.yaml (gateway service).
# extensions_config.json lives on the volume because the Gateway rewrites it
# at run time (MCP servers, skill toggles).
ENV DEER_FLOW_PROJECT_ROOT=/app \
    DEER_FLOW_HOME=/app/backend/.deer-flow \
    DEER_FLOW_CONFIG_PATH=/app/backend/config.yaml \
    DEER_FLOW_EXTENSIONS_CONFIG_PATH=/app/backend/.deer-flow/extensions_config.json \
    DEER_FLOW_SKILLS_PATH=/app/skills \
    CI=true \
    PYTHONUNBUFFERED=1 \
    PORT=8001 \
    GATEWAY_WORKERS=1

EXPOSE 8001

CMD ["/opt/railway/entrypoint.sh"]
