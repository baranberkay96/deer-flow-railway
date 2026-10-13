# Notice

## Upstream software

| Software | License | Images / artifacts used (publisher) |
|---|---|---|
| DeerFlow (Gateway, Frontend, public skills) | MIT. Copyright (c) 2025 Bytedance Ltd. and/or its affiliates; Copyright (c) 2025-2026 DeerFlow Authors | `ghcr.io/bytedance/deer-flow-backend:v2.1.0`, `ghcr.io/bytedance/deer-flow-frontend:v2.1.0`, `skills/` from the `v2.1.0` source tarball (ByteDance / DeerFlow Authors) |
| nginx | BSD-2-Clause | `nginx:1.30.5-alpine` (Docker Official Image) |
| PostgreSQL | PostgreSQL License | `ghcr.io/railwayapp-templates/postgres-ssl:18` (Railway) |
| Redis | RSALv2 / SSPLv1 / AGPLv3 (Redis 8 tri-license) | `redis:8.2` (Docker Official Image) |

Optional third-party services (E2B, Tavily, Jina, LLM providers) are used only when you add their keys and are governed by their own terms.

## Verified against

| What | Upstream file | Ref | URL | Checked |
|---|---|---|---|---|
| Services, commands, env, healthcheck, volumes | `docker/docker-compose.yaml` | `v2.1.0` (commit `345f08b`) | https://github.com/bytedance/deer-flow/blob/v2.1.0/docker/docker-compose.yaml | 2026-10-13 |
| Edge routing | `docker/nginx/nginx.conf` | `v2.1.0` | https://github.com/bytedance/deer-flow/blob/v2.1.0/docker/nginx/nginx.conf | 2026-10-13 |
| Production config (Postgres, Redis, tools, sandbox) and resources | `deploy/helm/deer-flow/values.yaml`, `templates/gateway-deployment.yaml`, `templates/frontend-deployment.yaml` | `v2.1.0` | https://github.com/bytedance/deer-flow/tree/v2.1.0/deploy/helm/deer-flow | 2026-10-13 |
| Config schema and options (`config_version` 45) | `config.example.yaml`, `backend/packages/harness/deerflow/config/*.py` | `v2.1.0` | https://github.com/bytedance/deer-flow/blob/v2.1.0/config.example.yaml | 2026-10-13 |
| Sandbox providers (local, AIO, provisioner, BoxLite, E2B, OpenSandbox, Tenki) | `backend/docs/CONFIGURATION.md`, `deerflow/sandbox/security.py`, `deerflow/community/e2b_sandbox/` | `v2.1.0` | https://github.com/bytedance/deer-flow/blob/v2.1.0/backend/docs/CONFIGURATION.md | 2026-10-13 |
| Auth (setup/initialize, registration switch, CSRF, trusted proxies) | `backend/app/gateway/routers/auth.py`, `csrf_middleware.py`, `auth/config.py` | `v2.1.0` | https://github.com/bytedance/deer-flow/tree/v2.1.0/backend/app/gateway | 2026-10-13 |
| Readiness probe | `backend/app/gateway/health.py` | `v2.1.0` | same | 2026-10-13 |
| Image build (venv path, extras, no USER) | `backend/Dockerfile`, `frontend/Dockerfile`, `.github/workflows/container.yaml` | `v2.1.0` | https://github.com/bytedance/deer-flow/tree/v2.1.0 | 2026-10-13 |
| Frontend runtime env and rewrites | `frontend/next.config.js`, `frontend/src/core/auth/gateway-config.ts` | `v2.1.0` | same | 2026-10-13 |
| Provider presets (model ids, timeouts) | `scripts/wizard/providers.py` | `v2.1.0` | same | 2026-10-13 |
| Next.js listen address (`next start` without `-H`) | `dist/cli/next-start.js`, `dist/server/lib/start-server.js` | `next@16.3.3` | https://unpkg.com/next@16.3.3/ | 2026-10-13 |
| nginx resolver / envsubst behaviour | `entrypoint/15-local-resolvers.envsh`, `entrypoint/20-envsubst-on-templates.sh` | `master` | https://github.com/nginx/docker-nginx/tree/master/entrypoint | 2026-10-13 |
| Railway edge headers (`X-Real-IP`, `X-Forwarded-Proto`) | Public networking specs | — | https://docs.railway.com/networking/public-networking/specs-and-limits | 2026-10-13 |

## Adapted code

| Our file | Source | Copyright / license | Changes |
|---|---|---|---|
| `services/nginx/templates/deerflow.conf.template` | `docker/nginx/nginx.conf` (v2.1.0) | © Bytedance Ltd. and/or its affiliates, DeerFlow Authors — MIT | Same route table, timeouts and body limits; upstream hosts replaced by Railway variables; resolver from `/etc/resolv.conf`; realip from Railway's `X-Real-IP`; provisioner route removed; `/healthz` and the guarded `initialize` route added; common headers moved to a snippet |
| `services/gateway/railway/config.base.yaml` | `config.example.yaml` and `deploy/helm/deer-flow/values.yaml` (v2.1.0) | © Bytedance Ltd. and/or its affiliates, DeerFlow Authors — MIT | Selected sections and values; Postgres/Redis persistence, scheduler, agents API, closed registration |
| Model entries in `services/gateway/railway/render_config.py` | `scripts/wizard/providers.py` (v2.1.0) | © Bytedance Ltd. and/or its affiliates, DeerFlow Authors — MIT | Provider presets reproduced as code; Claude default id updated and fixed-budget thinking removed; output caps adjusted |
| `services/gateway/railway/extensions_config.json` | Helm `extensionsConfig` default (v2.1.0) | MIT, as above | Same empty seed |
| `services/gateway/Dockerfile`, `railway/entrypoint.sh`, `railway/serve.py`, `railway/wait_for_services.py`, `railway/bootstrap_admin.py`, the rest of `railway/render_config.py`, `services/nginx/Dockerfile`, `services/nginx/docker-entrypoint.d/*`, `services/nginx/snippets/deerflow_proxy.conf` | Written for this template | — | — |

MIT License text (applies to the adapted parts above):

```
MIT License

Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
Copyright (c) 2025-2026 DeerFlow Authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Reference only (not copied)

- Marketplace template `deer-flow` ("DeerFlow", source `gridalpha/deerflow-railway`): no license. Read for ideas (four-service shape, loopback admin seed, closing registration). No files or text copied.
- Marketplace template `deerflow` ("DeerFlow V2", source `rpuls/deer-flow-quickstart`, a fork of DeerFlow): read for ideas (Railway pitfalls it documents). No files or text copied.
- The `_upstream/bytedance__deer-flow` working copy is at `main` (2.2.0-dev); everything above was checked against the `v2.1.0` tag instead.

## Trademarks

"DeerFlow" and the DeerFlow logo belong to their respective owners (ByteDance Ltd. and/or its affiliates); "Railway" to Railway Corporation. This is a community template and is not affiliated with or endorsed by ByteDance, the DeerFlow maintainers or Railway.
