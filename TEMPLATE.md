# DeerFlow v2 Deep Research Super Agent — Railway template spec

## Listing

| Field | Value |
|---|---|
| Name | **DeerFlow v2 Deep Research Super Agent** (`v2` = DeerFlow major version; images pinned to `v2.1.0`) |
| Description | ByteDance's open-source agent that researches the web and writes reports. (73 chars) |
| Category | AI/ML |
| Tags | deerflow, deer-flow, ai-agent, deep-research, langgraph, llm, research, agents |
| Icon | `https://cdn.jsdelivr.net/gh/bytedance/deer-flow@v2.1.0/frontend/public/images/deer.svg` (HTTP 200, image/svg+xml, checked 2026-10-13) |
| User input at deploy | **None required.** The template boots without any key. To run agents, set at least one LLM key on **Gateway** (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY` or `OPENROUTER_API_KEY`). Optional: `TAVILY_API_KEY`, `JINA_API_KEY`, `E2B_API_KEY`. |

**Listing wording.** DeerFlow writes code and files in every configuration, but *executing* code needs a sandbox. Railway has no Docker-in-Docker, so code execution is off by default and turns on only with an E2B key (see "Sandbox decision"). The listing therefore says "researches the web and writes reports" and does not promise built-in code execution.

## Base market template

| Code | Name | Stats (2026-10-13) | Verdict |
|---|---|---|---|
| `deerflow` | "DeerFlow V2" (`rpuls/deer-flow-quickstart`, a fork) | 53 projects, 23 active | Most deployed. Builds a fork from source at HEAD (minutes per build, unpinned), exposes the Gateway **and** Postgres (TCP proxy on 5432) publicly, no volume for thread files, no healthchecks, no Redis. Not used as base. |
| `deer-flow` | "DeerFlow" (`gridalpha/deerflow-railway`) | 2 projects, 1 active | **Chosen as structural base**: same four-service shape as upstream (nginx edge, Gateway, Frontend, Postgres) with an admin seed. Kept the shape; fixed version skew (`:latest` images with v2.0.0 skills), missing Redis, baked-in extensions config, IPv4-only Gateway, no frontend healthcheck. |

Neither market repo's files were copied: `gridalpha/deerflow-railway` has no license; `rpuls/deer-flow-quickstart` was read for ideas only. All files under `services/` were written for this template or adapted from the MIT-licensed upstream (see NOTICE.md).

## Pinned versions

| Service | Image / source | Tag | Release / build date | Checked |
|---|---|---|---|---|
| Gateway | `ghcr.io/bytedance/deer-flow-backend` (wrapped: `services/gateway`) | `v2.1.0` (revision `345f08b`, built with the `postgres` + `redis` extras) | 2026-09-24 | 2026-10-13 |
| Gateway skills | `bytedance/deer-flow` release tarball, `skills/` only (23 public skills) | `v2.1.0` | 2026-09-24 | 2026-10-13 |
| Frontend | `ghcr.io/bytedance/deer-flow-frontend` | `v2.1.0` (revision `345f08b`) | 2026-09-24 | 2026-10-13 |
| Nginx | `nginx` (wrapped: `services/nginx`) | `1.30.5-alpine` (stable line) | image build 2026-09-26 | 2026-10-13 |
| Postgres | `ghcr.io/railwayapp-templates/postgres-ssl` | `18` | Railway base | 2026-10-13 |
| Redis | `redis` | `8.2` | Railway base | 2026-10-13 |

Both DeerFlow images exist on GHCR with tag `v2.1.0` (single-platform `linux/amd64`, labels `org.opencontainers.image.version=v2.1.0`). The provisioner image (`deer-flow-provisioner:v2.1.0`) also exists but is not used (it needs Kubernetes).

**Upgrade path:** change `ARG DEERFLOW_VERSION` in `services/gateway/Dockerfile` (image and skills move together) and the Frontend image tag to the same release, then compare the new `config.example.yaml` `config_version` with `services/gateway/railway/config.base.yaml` (45 for v2.1.0) and port any renamed keys. Schema migrations run inside the Gateway on start.

## Architecture

```
Internet --HTTPS--> Nginx (only public domain, :2026)
                     |- /api/langgraph/*  -> rewrite /api/* -> Gateway :8001
                     |- /api/*, /health, /docs, /redoc, /openapi.json -> Gateway :8001
                     |- POST /api/v1/auth/initialize -> 403 (admin is created by the Gateway)
                     '- everything else -> Frontend :3000 (Next.js)
Frontend (SSR auth checks) ---------------------------> Gateway :8001 (private)
Gateway -> Postgres (users, threads, checkpoints, LangGraph store, run events, custom agents, schedules)
        -> Redis (run event stream bridge: live SSE delivery and reconnect replay)
        -> volume /app/backend/.deer-flow (thread uploads/workspace/outputs, memory, custom skills, extensions_config.json)
        -> LLM providers, web search/fetch, optional E2B sandboxes (internet egress)
```

Why a separate Nginx service: the Frontend image's Next.js `/api/*` rewrites are frozen at build time to `127.0.0.1:8001`, and DeerFlow needs UI and API on one origin (session cookie + CSRF double-submit). Railway routes one domain to one port, so upstream's own path-routing proxy is kept as its own service.

### Deviations from upstream `docker/docker-compose.yaml` (v2.1.0) and why

- **config.yaml is rendered, not mounted.** `services/gateway/railway/render_config.py` writes it at every start from `config.base.yaml` plus Railway variables. DeerFlow aborts on an unset `$VAR`, so model/tool entries are emitted only for keys that are set. `DEERFLOW_CONFIG_YAML` replaces the whole file for advanced setups.
- **Skills are baked into the Gateway image** from the same release tarball (upstream bind-mounts `../skills`). Custom skills go to the volume (`users/{id}/skills/custom`).
- **extensions_config.json is seeded onto the volume** (upstream bind-mounts it writable; the Gateway rewrites it for MCP servers and skill toggles).
- **Postgres instead of SQLite** for `database`, `checkpointer`, `run_events` and `agent_storage` (upstream compose default is SQLite; Helm uses Postgres). Redis stream bridge as in compose.
- **No provisioner / AIO sandbox / DooD overlay** (no Docker or Kubernetes on Railway). See "Sandbox decision".
- **Admin bootstrap:** upstream lets the first visitor of `/setup` create the admin. Here the Gateway creates it from generated variables over loopback, and Nginx blocks the public `initialize` call. `auth.local.allow_registration` is set to `false` (upstream default: open).
- **Dual-stack Gateway listener** (`serve.py`) instead of `--host 0.0.0.0`: Railway's healthcheck is IPv4, legacy private networks are IPv6-only, and single-worker uvicorn on `::` is IPv6-only.
- **Client IP:** Nginx restores the client address from Railway's `X-Real-IP` (realip module); `AUTH_TRUSTED_PROXIES` lists private ranges (plain and IPv4-mapped, because the dual-stack socket reports IPv4 peers as `::ffff:a.b.c.d`) so the login lockout counts real clients. Upstream compose trusts the `nginx` hostname, which Railway cannot express.
- **Self-calls use loopback** (`DEER_FLOW_CHANNELS_*_URL=http://127.0.0.1:8001`) instead of `http://gateway:8001`: a service cannot resolve its own private name at boot.
- **Graceful shutdown:** `RAILWAY_DEPLOYMENT_DRAINING_SECONDS=90` mirrors compose's `stop_grace_period: 90s` (30 s memory flush).
- **Nginx:** route table from upstream `docker/nginx/nginx.conf`; provisioner route dropped; upstreams from variables and resolved per request through Railway DNS; `/healthz` added; IPv6 listen removed automatically on hosts without IPv6.

## Sandbox decision

DeerFlow's agent runs file tools always, and bash/code through a sandbox provider. Options in v2.1.0 and their fit on Railway:

| Provider | Needs | On Railway |
|---|---|---|
| `AioSandboxProvider` (Docker, default for `make up` with DooD) | Docker socket | **Not possible** (no Docker-in-Docker, never mount a socket) |
| `AioSandboxProvider` + provisioner | Kubernetes API | **Not possible** |
| `BoxliteProvider` | KVM micro-VMs | **Not possible** (no virtualization) |
| `LocalSandboxProvider` with `allow_host_bash: true` | nothing | Possible but **unsafe**: commands run inside the Gateway container, which holds the database URL, JWT secret and provider keys. A prompt-injected web page could exfiltrate them. **Not offered.** |
| `LocalSandboxProvider` with `allow_host_bash: false` | nothing | **Default.** Agents read/write files in their per-thread workspace on the volume; the `bash` tool and bash sub-agent are removed by DeerFlow itself. |
| `E2BSandboxProvider` (E2B cloud micro-VMs, SDK bundled in the image) | `E2B_API_KEY` | **Opt-in.** Setting the key on Gateway switches the sandbox; bash/Python run in isolated E2B VMs, ownership shared through Redis. |
| `TenkiSandboxProvider`, `OpenSandboxProvider` | extra SDK not in the image / an OpenSandbox server that itself needs Docker or K8s | Not wired. |

Result: **code execution is disabled by default and stated in the README**; it becomes available with an E2B key. Skills that run scripts (charts, slides, data analysis, podcasts) need E2B; research and report writing do not.

## Services

Creation order does not matter: Nginx resolves upstreams per request and the Gateway waits for Postgres and Redis. Values are entered exactly as shown (Railway resolves `${{...}}`). Service names matter: the references and Nginx's fallback hosts assume `Nginx`, `Frontend`, `Gateway`, `Postgres`, `Redis`.

### Nginx

- **Source:** GitHub repo `baranberkay96/deer-flow-railway`, root directory `/services/nginx` (Dockerfile build)
- **Start command:** image default
- **Healthcheck:** `/healthz` (timeout 60 s)
- **Public domain:** yes → target port `2026`
- **TCP proxy:** none
- **Volume:** none
- **Restart policy:** ON_FAILURE (max 10 retries)
- **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `PORT` | `2026` | Port nginx listens on; the public domain targets it. |
| `DEERFLOW_GATEWAY_UPSTREAM` | `${{Gateway.RAILWAY_PRIVATE_DOMAIN}}:8001` | Gateway private address (/api/*, /health, API docs). |
| `DEERFLOW_FRONTEND_UPSTREAM` | `${{Frontend.RAILWAY_PRIVATE_DOMAIN}}:3000` | Frontend private address (everything else). |
| `DEERFLOW_ALLOW_PUBLIC_SETUP` | `false` | true re-opens the browser /setup page; keep false, the Gateway creates the admin itself. |

### Frontend

- **Source:** Docker image `ghcr.io/bytedance/deer-flow-frontend:v2.1.0`
- **Start command:** image default
- **Healthcheck:** `/` (timeout 300 s)
- **Public domain:** no (private network only)
- **TCP proxy:** none
- **Volume:** none
- **Restart policy:** ON_FAILURE (max 10 retries)
- **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `PORT` | `3000` | Next.js listen port (Railway health-checks this port). |
| `NODE_ENV` | `production` | Node environment. |
| `DEER_FLOW_INTERNAL_GATEWAY_BASE_URL` | `http://${{Gateway.RAILWAY_PRIVATE_DOMAIN}}:8001` | Gateway URL used by server-side rendering for auth checks (private network). |
| `DEER_FLOW_TRUSTED_ORIGINS` | `https://${{Nginx.RAILWAY_PUBLIC_DOMAIN}}` | Public browser origin (update when you add a custom domain). |
| `BETTER_AUTH_SECRET` | `${{secret(48, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Frontend session secret required by upstream compose (32+ characters). |
| `NEXT_TELEMETRY_DISABLED` | `1` | Disable Next.js telemetry. |

### Gateway

- **Source:** GitHub repo `baranberkay96/deer-flow-railway`, root directory `/services/gateway` (Dockerfile build)
- **Start command:** image default
- **Healthcheck:** `/health/ready` (timeout 1200 s)
- **Public domain:** no (private network only)
- **TCP proxy:** none
- **Volume:** `/app/backend/.deer-flow`
- **Restart policy:** ALWAYS
- **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `PORT` | `8001` | Gateway (FastAPI) listen port; Railway health-checks this port. |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | Postgres for users, threads, checkpoints, run events, custom agents and scheduled tasks. |
| `DEER_FLOW_STREAM_BRIDGE_REDIS_URL` | `${{Redis.REDIS_URL}}/0` | Redis Streams bridge for live run events (SSE resume/replay). |
| `AUTH_JWT_SECRET` | `${{secret(64, "abcdef0123456789")}}` | Signs session tokens. Changing it signs everyone out. |
| `DEER_FLOW_INTERNAL_AUTH_TOKEN` | `${{secret(48, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Internal token for Gateway self-calls (IM channels, scheduler). |
| `DEERFLOW_ADMIN_EMAIL` | `admin@example.com` | Login email of the admin account created on first boot. Change before deploying if you like. |
| `DEERFLOW_ADMIN_PASSWORD` | `${{secret(24, "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789")}}` | Password of that admin account (generated). Read it here to sign in. |
| `DEER_FLOW_ENV` | `production` | Production mode: refuses the DEER_FLOW_AUTH_DISABLED bypass. |
| `GATEWAY_ENABLE_DOCS` | `false` | true exposes Swagger/ReDoc at /docs and /redoc. |
| `GATEWAY_CORS_ORIGINS` | `https://${{Nginx.RAILWAY_PUBLIC_DOMAIN}}` | Allowed browser origin for auth/CSRF checks (add custom domains, comma-separated). |
| `AUTH_TRUSTED_PROXIES` | `10.0.0.0/8,100.64.0.0/10,172.16.0.0/12,192.168.0.0/16,fc00::/7,::ffff:10.0.0.0/104,::ffff:100.64.0.0/106,::ffff:172.16.0.0/108,::ffff:192.168.0.0/112` | Private ranges (plain and IPv4-mapped) whose X-Real-IP is trusted, i.e. the Nginx service, for the per-IP login lockout. |
| `GATEWAY_WORKERS` | `1` | Uvicorn workers. Keep 1 (upstream default; run control is in-process). >1 falls back to an IPv4-only listener. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `90` | Shutdown grace so the memory queue flush (30 s) finishes on redeploy. |
| `DEERFLOW_ALLOW_REGISTRATION` | `false` | true lets anyone with the URL create an account and spend your model credits. |
| `DEERFLOW_AGENTS_API` | `true` | Custom-agent management in the UI (auth is enforced). |
| `DEERFLOW_SCHEDULER` | `true` | Background scheduler for scheduled agent runs. |
| `DEERFLOW_LOG_LEVEL` | `info` | DeerFlow log level (debug, info, warning, error). |
| `ANTHROPIC_API_KEY` | *(empty)* | Optional. Anthropic key; adds Claude models (ANTHROPIC_MODEL). |
| `ANTHROPIC_MODEL` | `claude-opus-5-5` | Claude model id(s), comma-separated. Used only when ANTHROPIC_API_KEY is set. |
| `OPENAI_API_KEY` | *(empty)* | Optional. OpenAI (or OpenAI-compatible) key; adds OPENAI_MODEL. |
| `OPENAI_MODEL` | `gpt-5` | OpenAI model id(s), comma-separated. Used only when OPENAI_API_KEY is set. |
| `DEERFLOW_OPENAI_BASE_URL` | *(empty)* | Optional. Base URL of an OpenAI-compatible API (vLLM, Groq, Together, ...); empty = OpenAI. |
| `GEMINI_API_KEY` | *(empty)* | Optional. Google AI Studio key; adds GEMINI_MODEL. |
| `GEMINI_MODEL` | `gemini-2.5-pro` | Gemini model id(s), comma-separated. Used only when GEMINI_API_KEY is set. |
| `DEEPSEEK_API_KEY` | *(empty)* | Optional. DeepSeek key; adds DEEPSEEK_MODEL. |
| `DEEPSEEK_MODEL` | `deepseek-v4-pro` | DeepSeek model id(s), comma-separated. Used only when DEEPSEEK_API_KEY is set. |
| `OPENROUTER_API_KEY` | *(empty)* | Optional. OpenRouter key; adds OPENROUTER_MODEL. |
| `OPENROUTER_MODEL` | `openai/gpt-5` | OpenRouter model id(s), comma-separated. Used only when OPENROUTER_API_KEY is set. |
| `DEERFLOW_DEFAULT_MODEL` | *(empty)* | Optional. Model id to list first (default model). Empty = first configured provider. |
| `TAVILY_API_KEY` | *(empty)* | Optional. Tavily key; replaces keyless DuckDuckGo web search. |
| `JINA_API_KEY` | *(empty)* | Optional. Jina Reader key; raises the web_fetch rate limit. |
| `E2B_API_KEY` | *(empty)* | Optional. E2B key; enables bash/code execution in E2B cloud sandboxes (off without it). |

### Postgres

- **Source:** Docker image `ghcr.io/railwayapp-templates/postgres-ssl:18`
- **Start command:** image default
- **Healthcheck:** none (no HTTP endpoint)
- **Public domain:** no (private network only)
- **TCP proxy:** none
- **Volume:** `/var/lib/postgresql/data`
- **Restart policy:** ON_FAILURE (max 10 retries)
- **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `PGDATA` | `/var/lib/postgresql/data/pgdata` | Location where the database will be initialized |
| `PGHOST` | `${{RAILWAY_PRIVATE_DOMAIN}}` | Railway Private Domain Name. |
| `PGPORT` | `5432` | Port to connect to Postgres. |
| `PGUSER` | `${{ POSTGRES_USER }}` | Required variable for Data panel |
| `PGDATABASE` | `${{POSTGRES_DB}}` | Required variable for the data panel. |
| `PGPASSWORD` | `${{POSTGRES_PASSWORD}}` | Required variable for Data panel |
| `POSTGRES_DB` | `railway` | Default database created when image is started. |
| `DATABASE_URL` | `postgresql://${{PGUSER}}:${{POSTGRES_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:5432/${{PGDATABASE}}` | URL to connect to Postgres database. |
| `POSTGRES_USER` | `postgres` | User to connect to Postgres DB |
| `SSL_CERT_DAYS` | `820` | SSL certificate expiry in days. |
| `POSTGRES_PASSWORD` | `${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}` | Password to connect to DB |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Allow Postgres to cleanly shut down |

### Redis

- **Source:** Docker image `redis:8.2`
- **Start command:** `/bin/sh -c "rm -rf $RAILWAY_VOLUME_MOUNT_PATH/lost+found/ && exec docker-entrypoint.sh redis-server --requirepass $REDIS_PASSWORD --save 60 1 --dir $RAILWAY_VOLUME_MOUNT_PATH"`
- **Healthcheck:** none (no HTTP endpoint)
- **Public domain:** no (private network only)
- **TCP proxy:** none
- **Volume:** `/data`
- **Restart policy:** ON_FAILURE (max 10 retries)
- **Replicas:** 1

| Variable | Value | Description |
|---|---|---|
| `REDISHOST` | `${{RAILWAY_PRIVATE_DOMAIN}}` | Private network hostname of the Redis service, only resolvable from services in the same environment |
| `REDISPORT` | `6379` | Port that Redis listens on |
| `REDISUSER` | `default` | Username for authenticating with Redis |
| `REDIS_URL` | `redis://${{ REDISUSER }}:${{ REDIS_PASSWORD }}@${{ REDISHOST }}:${{ REDISPORT }}` | Connection string for connecting to Redis using the private network |
| `REDISPASSWORD` | `${{REDIS_PASSWORD}}` | Alias of REDIS_PASSWORD for clients that expect the unseparated name |
| `REDIS_PASSWORD` | `${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}` | Randomly generated password for authenticating with Redis |

## Improvements over market templates

| # | Market issue | This template |
|---|---|---|
| 1 | `deer-flow`: Frontend `:latest` and Gateway built from `deer-flow-backend:latest` with skills from `v2.0.0` (version skew now that `latest` = v2.1.0). `deerflow`: builds a fork's HEAD from source | Both images pinned to `v2.1.0`; skills fetched from the same tag; one `ARG` moves both |
| 2 | No Redis in either template (upstream compose and Helm run the Redis stream bridge) | **Redis** service (Railway base) for the run-event stream bridge and E2B sandbox ownership |
| 3 | `deerflow`: Gateway gets a public domain and Postgres a public TCP proxy (5432) | Only **Nginx** is public; Gateway, Frontend, Postgres and Redis are private |
| 4 | `deerflow`: no volume, so uploads, agent outputs and memory vanish on redeploy | Volume on Gateway at `/app/backend/.deer-flow` (upstream's `DEER_FLOW_HOME`) |
| 5 | `deer-flow`: `extensions_config.json` baked into the image, so MCP servers and skill toggles reset on every redeploy | Seeded once onto the volume, then owned by the Gateway |
| 6 | First-run race: `deerflow` leaves `/setup` open to the first visitor; `deer-flow` seeds the admin but still serves the public `initialize` route | Admin created from generated variables over loopback **and** `POST /api/v1/auth/initialize` returns 403 at the edge; `auth.local.allow_registration: false` through DeerFlow's own setting |
| 7 | `deer-flow`: model entries always present with empty `$LLM_API_KEY`, so the UI lists models that fail at run time | Model entries rendered only for providers whose key is set; five providers, comma-separated model lists, `DEERFLOW_DEFAULT_MODEL` |
| 8 | No way to execute code (host bash off, no sandbox) | Optional **E2B** sandbox with one variable; default stays safe and is documented |
| 9 | `deerflow`: no healthchecks at all; `deer-flow`: none on Frontend | Gateway `/health/ready` (DB + checkpointer), Frontend `/`, Nginx `/healthz` |
| 10 | Gateway starts in parallel with Postgres and crashes or hangs on first boot | `wait_for_services.py` runs `SELECT 1` / `PING` before uvicorn; restart policy `ALWAYS`; healthcheck window 1200 s |
| 11 | `deer-flow`: Gateway on `0.0.0.0` only | Dual-stack socket (IPv4 healthcheck + IPv6 private networking) |
| 12 | Login lockout keyed on the proxy's IP (one attacker locks everyone out) | Client IP restored from Railway's `X-Real-IP`, private ranges trusted via `AUTH_TRUSTED_PROXIES` |
| 13 | Run events in memory; custom agents in files | `run_events: db`, `agent_storage: db`, scheduler enabled, all in Postgres |
| 14 | `deerflow`: Postgres 17 with a public TCP proxy | Railway base Postgres 18 and Redis 8.2 copied from `_railway-base`, private only |
| 15 | Both use `RAILWAY_DOCKERFILE_PATH` against a whole-repo context | Per-service `rootDirectory` (`/services/gateway`, `/services/nginx`) with small contexts |

## Scaling

- **Gateway:** keep **1 replica and `GATEWAY_WORKERS=1`**. Upstream keeps run control (cancel, dedup), IM channels and browser sessions in process; more workers need `run_ownership.heartbeat_enabled` and give up the dual-stack listener. A volume also prevents replicas. Scale vertically (RAM/CPU) for more concurrent runs; `subagent_runtime.max_running` (default 3) caps parallel sub-agents per process (`DEERFLOW_CONFIG_YAML` to change).
- **Frontend:** stateless; replicas are possible but rarely needed.
- **Nginx:** stateless; one replica is plenty.
- **Postgres / Redis:** single instance (volumes). Railway can convert Postgres to HA from the service settings.

## Resource estimate

Prices: RAM $10/GB-month, vCPU $20/vCPU-month, volume $0.15/GB-month. Estimates from upstream Helm requests/limits (Gateway 512 Mi request / 2 Gi limit, Frontend 256 Mi / 512 Mi, nginx 64 Mi) and typical footprints; **not measured on Railway** (no local run was possible, see below). LLM, search and E2B usage are billed by those providers, not Railway.

| Service | Idle RAM | Typical RAM | Typical vCPU | Volume |
|---|---|---|---|---|
| Nginx | 15 MB | 30 MB | 0.01 | — |
| Frontend (Next.js) | 200 MB | 300 MB | 0.03 | — |
| Gateway (FastAPI + LangGraph agent runtime) | 500 MB | 1.2 GB (2 GB+ during long multi-agent runs) | 0.05 idle / 0.3 typical | ~2 GB |
| Postgres | 80 MB | 250 MB | 0.03 | ~1 GB |
| Redis | 10 MB | 40 MB | 0.01 | ~0.1 GB |
| **Total** | **≈ 0.8 GB** | **≈ 1.8 GB** | **≈ 0.1 idle / 0.4 typical** | **≈ 3 GB** |

- **Idle:** 0.8 GB × $10 + 0.1 vCPU × $20 + 3 GB × $0.15 ≈ **$11/month**
- **Typical (one team, a few runs a day):** 1.8 GB × $10 + 0.4 vCPU × $20 + $0.45 ≈ **$27/month**
- **Heavy (several concurrent long research runs):** Gateway 2–3 GB and ~1 vCPU ≈ **$45–60/month**.
- **Minimum plan: Hobby.** Trial's 1 GB per service is tight for the Gateway during long runs and its volume limit is small. Pro for teams that run many agents in parallel.

## Verification checklist

None of these were run yet (see "Local verification"). Run all on the first Railway deploy:

1. All five services *Active*. Healthchecks green: Nginx `/healthz`, Frontend `/`, Gateway `/health/ready`.
2. Gateway logs, in order: `config written: models=[NONE ...] sandbox=local (bash disabled) search=duckduckgo persistence=postgres, redis stream bridge registration=closed`, `Postgres is ready`, `Redis is ready`, `Gateway listening on [::]:8001 (IPv4 + IPv6)`, then `[deerflow-bootstrap] admin account created: admin@example.com`.
3. Nginx logs: `deerflow: gateway=gateway.railway.internal:8001 frontend=frontend.railway.internal:3000 public_setup=false`.
4. Open `https://{nginx-domain}/` (landing page) → `/workspace` redirects to `/login`. Sign in with `DEERFLOW_ADMIN_EMAIL` / `DEERFLOW_ADMIN_PASSWORD` (Gateway variables). `/setup` must not offer account creation; `curl -X POST https://{nginx-domain}/api/v1/auth/initialize` → 403.
5. `curl -X POST https://{nginx-domain}/api/v1/auth/register -H 'Content-Type: application/json' -d '{"email":"x@example.com","password":"Zq8-long-pass"}'` → 403 (registration disabled).
6. Add `ANTHROPIC_API_KEY` (or another provider key) on Gateway → redeploy → the model appears in the composer. Ask for a short researched briefing with sources → the run streams (SSE through `/api/langgraph/`), uses `web_search` + `web_fetch`, and writes a report file to the thread.
7. Reload the page mid-run → the stream resumes (Redis stream bridge).
8. Upload a PDF to a thread (≤ 50 MB) → visible to the agent.
9. Redeploy Gateway, Frontend and Postgres → chats, uploaded files, outputs, memory and custom agents are still there.
10. Settings → Skills lists the 23 public skills; toggle one, redeploy, the toggle persists (extensions config on the volume).
11. Optional: set `E2B_API_KEY` → logs show `sandbox=e2b`; ask the agent to run `python -c "print(2+2)"` → it executes in E2B.
12. Wrong password five times from one browser → that client is locked out for 5 minutes, another client can still log in (proves real client IPs).

## Open questions

- **Not run anywhere yet.** The shared Docker daemon froze (host disk full) before any image could be pulled, and Docker work was stopped. No image was built or started locally; Railway's deploy test is the first real run. What *was* verified locally is listed under "Local verification".
- **Frontend healthcheck `/`**: the landing page is static in v2.1.0 (no middleware, no gateway call), so it should return 200 even while the Gateway is still starting. If a future release redirects `/`, switch to `/login`.
- **`pnpm start` at run time**: the official Frontend image starts through corepack/pnpm (cached at build). If Railway logs show corepack trying to download pnpm, set the start command to `node /app/frontend/node_modules/next/dist/bin/next start` with working dir `/app/frontend` (Railway has no working-dir field, so use `sh -c "cd /app/frontend && node node_modules/next/dist/bin/next start"`).
- **Default model ids** (`claude-opus-5-5`, `gpt-5`, `gemini-2.5-pro`, `deepseek-v4-pro`, `openai/gpt-5`) follow the providers' current names and upstream's setup-wizard presets; providers retire models, so the ids are variables. Claude entries configure no `thinking` block: current Claude models think adaptively by default and reject the fixed `budget_tokens` toggle in upstream's example, so the UI thinking switch has no effect for them.
- **E2B path** was validated only at config level (DeerFlow's own `AppConfig` accepts the rendered sandbox block). A real E2B run needs an account.
- **`AUTH_TRUSTED_PROXIES`**: assumes Railway private addresses fall in RFC1918/CGNAT/ULA ranges (true for `fd12::/16` and the IPv4 ranges seen so far). If lockouts hit everybody at once, check the peer address in Gateway logs and extend the list.
- **Custom domain:** add it on Nginx, then update `GATEWAY_CORS_ORIGINS` (Gateway) and `DEER_FLOW_TRUSTED_ORIGINS` (Frontend).
- **Admin email default `admin@example.com`** is accepted by DeerFlow's validator (tested with email-validator 2.3.0 / pydantic 2.13.3, the versions in v2.1.0's lockfile). The email can be changed later through the account settings (change-password API with `new_email`).

## Local verification (2026-10-13)

Docker could not be used: the shared daemon returned I/O errors on the first `docker pull` (host disk at 100 %), later commands hung, and the coordinator stopped all Docker work. **No Dockerfile was built and no container was started.** Checks that ran without Docker:

| Check | Result |
|---|---|
| Rendered `config.yaml` for 3 variable sets (no keys; all five providers + E2B + Tavily + default model; no DB/Redis fallback) validated with DeerFlow v2.1.0's own `AppConfig.model_validate` (harness source at tag v2.1.0) | **Pass** (0 / 6 / 0 models, local vs E2B sandbox, postgres+redis vs sqlite+memory) |
| `DEERFLOW_CONFIG_YAML` verbatim mode and invalid-YAML rejection | **Pass** (invalid YAML exits 1) |
| `serve.py` with uvicorn 0.46.0 (lockfile version) on a dummy ASGI app: one socket answers `127.0.0.1` and `::1`, clean SIGTERM shutdown | **Pass** (IPv4 peers appear as `::ffff:127.0.0.1`, hence the mapped ranges in `AUTH_TRUSTED_PROXIES`) |
| `bootstrap_admin.py` against a mock Gateway: create, already-exists, no credentials, rejected password, not-ready timeout | **Pass**; password and response bodies never printed |
| `wait_for_services.py` with unreachable Postgres/Redis and an 8 s timeout | **Pass** (exit 1 after 10 s, no credentials in the log) |
| `admin@example.com` against pydantic `EmailStr` (email-validator 2.3.0) | **Pass** (`*.local` would be rejected) |
| Nginx template rendered with Railway-like values and parsed by `crossplane` (directive context/argument checks) | **Pass**, no unsubstituted variables |
| Shell syntax (`sh -n`) for all entrypoint scripts; `py_compile` for all helpers | **Pass** |
| Skills extraction command run against the real `v2.1.0` tarball | **Pass** (23 public skills, 872 KB) |
| Image tags exist (registry API, no pull): `deer-flow-backend:v2.1.0`, `deer-flow-frontend:v2.1.0` (amd64, revision `345f08b`), `nginx:1.30.5-alpine` | **Pass** |
| `docker build --platform linux/amd64` of `services/gateway` and `services/nginx`; running the stack with `docker run --init` | **Not run (unverified)** |
