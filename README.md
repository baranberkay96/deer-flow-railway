# Deploy and Host DeerFlow with Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/deerflow-v2-deep-research-super-agent?referralCode=20H68q)

DeerFlow is ByteDance's open-source (MIT) super-agent harness: give it a goal and a lead agent plans, searches the web, reads sources, delegates to sub-agents and delivers a cited report or other files. This community template runs DeerFlow v2.1.0 on Railway behind one HTTPS URL, with login, Postgres and Redis.

## About Hosting DeerFlow

A self-hosted DeerFlow is more than one container. A FastAPI Gateway runs the LangGraph agent runtime, a Next.js frontend serves the workspace, and an nginx edge puts both on one origin. Postgres keeps users, conversations, checkpoints, run history, custom agents and schedules; Redis carries live run events so a reloaded page picks up a running task; a volume holds each thread's uploads, workspace and outputs. This template wires all of it with private networking, pinned upstream images, a generated admin account, closed self-registration and a config file rendered from Railway variables, so adding a model is just adding an API key.

## Common Use Cases

- Market, competitor and technology research that ends in a cited briefing instead of thirty open tabs
- Literature reviews and paper summaries with the bundled academic and systematic-review skills
- Recurring research digests and newsletters on a schedule
- A private research assistant for a team, using your own model contract and keeping history on your infrastructure
- Custom agents with their own prompts, skills and MCP tools for internal workflows

## Dependencies for DeerFlow Hosting

- DeerFlow Gateway (`ghcr.io/bytedance/deer-flow-backend:v2.1.0`, wrapped with config rendering and the release's skills)
- DeerFlow Frontend (`ghcr.io/bytedance/deer-flow-frontend:v2.1.0`)
- nginx edge proxy (upstream routing table, built from this repository)
- PostgreSQL and Redis (Railway base images)
- At least one LLM provider key (Anthropic, OpenAI or compatible, Google Gemini, DeepSeek or OpenRouter) to run agents

### Deployment Dependencies

- DeerFlow source, docs and releases: https://github.com/bytedance/deer-flow
- Configuration reference: https://github.com/bytedance/deer-flow/blob/v2.1.0/backend/docs/CONFIGURATION.md
- Example configuration (all options): https://github.com/bytedance/deer-flow/blob/v2.1.0/config.example.yaml
- Optional code sandbox: https://e2b.dev
- Optional search and fetch keys: https://tavily.com and https://jina.ai/reader

### Implementation Details

| Service | Image | Role | Public |
|---|---|---|---|
| Nginx | nginx 1.30 (repo build) | One origin: `/api/*` and API docs to Gateway, everything else to Frontend; blocks the public first-run setup call | **yes** |
| Frontend | `deer-flow-frontend:v2.1.0` | Next.js workspace UI | no |
| Gateway | `deer-flow-backend:v2.1.0` (repo build) | Agent runtime and API; renders config.yaml, waits for the databases, creates the admin; volume for thread files | no |
| Postgres | Railway Postgres 18 | Users, threads, checkpoints, run events, custom agents, schedules | no |
| Redis | Railway Redis 8.2 | Live run-event stream bridge | no |

**First login**

1. Wait until the Gateway logs `admin account created` (1–3 minutes on first boot).
2. Open the Nginx URL, click through to the workspace and sign in with `DEERFLOW_ADMIN_EMAIL` and `DEERFLOW_ADMIN_PASSWORD` from the **Gateway** service variables. Public sign-up is off (`DEERFLOW_ALLOW_REGISTRATION=false`).
3. Add a model: set one of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY` or `OPENROUTER_API_KEY` on Gateway and redeploy it. Model ids are variables too (`ANTHROPIC_MODEL`, `OPENAI_MODEL`, ...; comma-separated for several). For an OpenAI-compatible server, set `OPENAI_API_KEY` plus `DEERFLOW_OPENAI_BASE_URL`.
4. Web search works without a key (DuckDuckGo). `TAVILY_API_KEY` switches search to Tavily, `JINA_API_KEY` lifts page-fetch rate limits.

**Code execution:** Railway has no Docker-in-Docker, so DeerFlow's container sandbox cannot run here, and running shell commands inside the Gateway would expose its secrets. Bash and code execution are therefore **off by default**; agents still research, read and write files and reports. Set `E2B_API_KEY` on Gateway to run code in isolated E2B cloud sandboxes (needed by skills that build charts, slides or run data analysis).

**Custom domain:** add it to the **Nginx** service, then add `https://{your-domain}` to `GATEWAY_CORS_ORIGINS` (Gateway) and `DEER_FLOW_TRUSTED_ORIGINS` (Frontend).

**Advanced configuration:** to use options the variables do not cover (other providers, MCP servers in config, sub-agent limits), put a complete `config.yaml` into `DEERFLOW_CONFIG_YAML` on Gateway; it replaces the generated file. Keep secrets as `$VAR` references.

**Scaling:** the Gateway keeps run control in process, so run it as one replica with one worker (upstream's default) and give it more RAM and CPU for more concurrent runs. Frontend and Nginx are stateless. Postgres can be converted to Railway's HA setup.

**Pinning and upgrading:** every image is pinned. To upgrade, read the DeerFlow release notes, change `DEERFLOW_VERSION` in `services/gateway/Dockerfile` and the Frontend image tag to the same release, and compare `config_version` in the new `config.example.yaml` with `services/gateway/railway/config.base.yaml`. The Gateway migrates its database on start; back up Postgres first.

This is a community template. It is not made, endorsed or supported by ByteDance or the DeerFlow maintainers. DeerFlow is MIT-licensed; model, search and sandbox providers bill you directly.

### Why Deploy DeerFlow on Railway?

Railway runs the whole DeerFlow stack in one project with private networking, managed TLS, persistent volumes and managed Postgres and Redis, so you get a production-shaped research agent without writing Docker Compose or a reverse-proxy config. Add a model key, redeploy one service, and pay only for the resources the agents actually use.
