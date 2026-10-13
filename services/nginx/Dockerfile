# DeerFlow edge proxy for Railway (community template).
#
# Same routing table as upstream docker/nginx/nginx.conf (DeerFlow v2.1.0):
# /api/* and the API docs go to the Gateway, everything else to the Next.js
# frontend, all on one public origin. Differences: upstreams come from Railway
# variables and are resolved per request through Railway's private DNS (so this
# service boots before the others), the client IP comes from Railway's edge
# (X-Real-IP), and first-run setup is blocked from the internet because the
# Gateway creates the admin account itself.
FROM nginx:1.30.5-alpine

# 15-local-resolvers.envsh exports NGINX_LOCAL_RESOLVERS from /etc/resolv.conf
# (IPv6-aware). Only the variables matched by the filter are substituted, so
# nginx runtime variables ($host, $http_upgrade, ...) stay intact.
ENV NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1 \
    NGINX_ENVSUBST_FILTER="^(PORT|DEERFLOW_|NGINX_)" \
    PORT=2026 \
    DEERFLOW_GATEWAY_UPSTREAM=gateway.railway.internal:8001 \
    DEERFLOW_FRONTEND_UPSTREAM=frontend.railway.internal:3000 \
    DEERFLOW_ALLOW_PUBLIC_SETUP=false

RUN rm -f /etc/nginx/conf.d/default.conf
COPY snippets/ /etc/nginx/snippets/
COPY templates/ /etc/nginx/templates/
COPY docker-entrypoint.d/ /docker-entrypoint.d/
RUN chmod 0755 /docker-entrypoint.d/16-deerflow-upstreams.envsh /docker-entrypoint.d/40-deerflow-ipv6.sh

EXPOSE 2026
