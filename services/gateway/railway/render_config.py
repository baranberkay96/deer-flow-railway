"""Render DeerFlow's config.yaml from Railway variables.

Runs at every Gateway start (before uvicorn). DeerFlow refuses to start when a
`$VAR` reference in config.yaml points at an unset variable, so model and tool
entries are only emitted for providers whose key is actually set. Secrets are
never written into the file: entries keep `$VAR` references that DeerFlow
resolves from the environment.

Inputs (all optional):
  DEERFLOW_CONFIG_YAML        complete config.yaml; written verbatim if set
  ANTHROPIC_API_KEY / ANTHROPIC_MODEL
  OPENAI_API_KEY / OPENAI_MODEL / DEERFLOW_OPENAI_BASE_URL
  GEMINI_API_KEY / GEMINI_MODEL
  DEEPSEEK_API_KEY / DEEPSEEK_MODEL
  OPENROUTER_API_KEY / OPENROUTER_MODEL
  DEERFLOW_DEFAULT_MODEL      model id (or entry name) to list first = default
  TAVILY_API_KEY              switch web_search from DuckDuckGo to Tavily
  E2B_API_KEY                 run bash/code in E2B cloud sandboxes
  E2B_TEMPLATE / E2B_DOMAIN   optional E2B template id / self-hosted E2B domain
  DATABASE_URL                Postgres DSN (falls back to SQLite on the volume)
  DEER_FLOW_STREAM_BRIDGE_REDIS_URL  Redis for the run event stream bridge
  DEERFLOW_ALLOW_REGISTRATION, DEERFLOW_AGENTS_API, DEERFLOW_SCHEDULER, DEERFLOW_LOG_LEVEL
*_MODEL variables accept a comma-separated list of model ids.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

import yaml

BASE_CONFIG = Path(__file__).with_name("config.base.yaml")
TRUE_VALUES = {"1", "true", "yes", "on"}


def log(message: str) -> None:
    print(f"[deerflow-railway] {message}", flush=True)


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def env_bool(name: str, default: bool) -> bool:
    raw = env(name)
    if not raw:
        return default
    return raw.lower() in TRUE_VALUES


def model_ids(var: str, default: str) -> list[str]:
    return [item.strip() for item in env(var, default).split(",") if item.strip()]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9.]+", "-", text.lower()).strip("-")


def anthropic_models() -> list[dict]:
    # Current Claude models use adaptive thinking by default and reject the
    # fixed `budget_tokens` toggle upstream's example uses, so no thinking
    # block is configured here.
    return [
        {
            "name": f"anthropic-{slug(model)}",
            "display_name": f"{model} (Anthropic)",
            "use": "langchain_anthropic:ChatAnthropic",
            "model": model,
            "api_key": "$ANTHROPIC_API_KEY",
            "default_request_timeout": 600.0,
            "max_retries": 2,
            "max_tokens": 16000,
            "supports_vision": True,
            "supports_thinking": False,
        }
        for model in model_ids("ANTHROPIC_MODEL", "claude-opus-5-5")
    ]


def openai_models() -> list[dict]:
    # Not OPENAI_BASE_URL: the OpenAI SDK reads that variable itself and an
    # empty value (as a template default) would break every request.
    base_url = env("DEERFLOW_OPENAI_BASE_URL") or env("OPENAI_BASE_URL")
    entries = []
    for model in model_ids("OPENAI_MODEL", "gpt-5"):
        entry = {
            "name": f"openai-{slug(model)}",
            "display_name": f"{model} (OpenAI{' compatible' if base_url else ''})",
            "use": "langchain_openai:ChatOpenAI",
            "model": model,
            "api_key": "$OPENAI_API_KEY",
            "request_timeout": 600.0,
            "max_retries": 2,
            "max_tokens": 16384,
            "supports_vision": not base_url,
        }
        if base_url:
            entry["base_url"] = base_url
        entries.append(entry)
    return entries


def gemini_models() -> list[dict]:
    return [
        {
            "name": f"gemini-{slug(model)}",
            "display_name": f"{model} (Google Gemini)",
            "use": "langchain_google_genai:ChatGoogleGenerativeAI",
            "model": model,
            "gemini_api_key": "$GEMINI_API_KEY",
            "timeout": 600.0,
            "max_retries": 2,
            "max_tokens": 8192,
            "supports_vision": True,
        }
        for model in model_ids("GEMINI_MODEL", "gemini-2.5-pro")
    ]


def deepseek_models() -> list[dict]:
    return [
        {
            "name": f"deepseek-{slug(model)}",
            "display_name": f"{model} (DeepSeek)",
            "use": "deerflow.models.patched_deepseek:PatchedChatDeepSeek",
            "model": model,
            "api_key": "$DEEPSEEK_API_KEY",
            "timeout": 600.0,
            "max_retries": 2,
            "max_tokens": 8192,
            "supports_vision": False,
            "supports_thinking": True,
            "when_thinking_enabled": {"extra_body": {"thinking": {"type": "enabled"}}},
            "when_thinking_disabled": {"extra_body": {"thinking": {"type": "disabled"}}},
        }
        for model in model_ids("DEEPSEEK_MODEL", "deepseek-v4-pro")
    ]


def openrouter_models() -> list[dict]:
    return [
        {
            "name": f"openrouter-{slug(model)}",
            "display_name": f"{model} (OpenRouter)",
            "use": "langchain_openai:ChatOpenAI",
            "model": model,
            "api_key": "$OPENROUTER_API_KEY",
            "base_url": "https://openrouter.ai/api/v1",
            "request_timeout": 600.0,
            "max_retries": 2,
            "max_tokens": 8192,
        }
        for model in model_ids("OPENROUTER_MODEL", "openai/gpt-5")
    ]


PROVIDERS = (
    ("ANTHROPIC_API_KEY", anthropic_models),
    ("OPENAI_API_KEY", openai_models),
    ("GEMINI_API_KEY", gemini_models),
    ("DEEPSEEK_API_KEY", deepseek_models),
    ("OPENROUTER_API_KEY", openrouter_models),
)


def build_models() -> list[dict]:
    models: list[dict] = []
    seen: set[str] = set()
    for key_var, builder in PROVIDERS:
        if not env(key_var):
            continue
        for entry in builder():
            if entry["name"] not in seen:
                seen.add(entry["name"])
                models.append(entry)
    preferred = env("DEERFLOW_DEFAULT_MODEL")
    if preferred:
        match = [m for m in models if preferred in (m["name"], m["model"])]
        if match:
            models = match[:1] + [m for m in models if m is not match[0]]
        else:
            log(f"DEERFLOW_DEFAULT_MODEL={preferred!r} matches no configured model; ignoring")
    return models


def build_sandbox() -> dict:
    if env("E2B_API_KEY"):
        sandbox = {
            "use": "deerflow.community.e2b_sandbox:E2BSandboxProvider",
            "api_key": "$E2B_API_KEY",
            "template": env("E2B_TEMPLATE", "code-interpreter-v1"),
            "home_dir": "/home/user",
            "idle_timeout": 600,
            "replicas": 3,
        }
        if env("E2B_DOMAIN"):
            sandbox["domain"] = env("E2B_DOMAIN")
        return sandbox
    # No Docker on Railway: the AIO/provisioner sandboxes cannot run, and host
    # bash inside the Gateway container is not a security boundary. File tools
    # work on the per-thread workspace; bash/code execution stays disabled.
    return {
        "use": "deerflow.sandbox.local:LocalSandboxProvider",
        "allow_host_bash": False,
        "bash_output_max_chars": 20000,
        "read_file_output_max_chars": 50000,
        "ls_output_max_chars": 20000,
        "bash_command_timeout": 600,
    }


def apply_search(config: dict) -> str:
    if not env("TAVILY_API_KEY"):
        return "duckduckgo"
    for tool in config.get("tools", []):
        if tool.get("name") == "web_search":
            tool["use"] = "deerflow.community.tavily.tools:web_search_tool"
    return "tavily"


def apply_persistence(config: dict) -> str:
    notes = []
    if env("DATABASE_URL"):
        notes.append("postgres")
    else:
        log("WARNING: DATABASE_URL is empty; falling back to SQLite on the volume")
        config["database"] = {"backend": "sqlite", "sqlite_dir": ".deer-flow/data"}
        config.pop("checkpointer", None)
        notes.append("sqlite")
    if env("DEER_FLOW_STREAM_BRIDGE_REDIS_URL") or env("REDIS_URL"):
        notes.append("redis stream bridge")
    else:
        log("WARNING: no Redis URL; using the in-memory stream bridge")
        config["stream_bridge"] = {"type": "memory"}
        notes.append("memory stream bridge")
    return ", ".join(notes)


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        tmp_name = handle.name
    os.replace(tmp_name, path)


def main() -> int:
    target = Path(env("DEER_FLOW_CONFIG_PATH", "/app/backend/config.yaml"))

    custom = os.environ.get("DEERFLOW_CONFIG_YAML", "")
    if custom.strip():
        try:
            yaml.safe_load(custom)
        except yaml.YAMLError as exc:
            log(f"ERROR: DEERFLOW_CONFIG_YAML is not valid YAML: {exc}")
            return 1
        write_atomic(target, custom)
        log(f"wrote {target} verbatim from DEERFLOW_CONFIG_YAML")
        return 0

    config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    config["log_level"] = env("DEERFLOW_LOG_LEVEL", "info")
    config["models"] = build_models()
    config["sandbox"] = build_sandbox()
    search = apply_search(config)
    persistence = apply_persistence(config)
    config["auth"]["local"]["allow_registration"] = env_bool("DEERFLOW_ALLOW_REGISTRATION", False)
    config["agents_api"]["enabled"] = env_bool("DEERFLOW_AGENTS_API", True)
    config["scheduler"]["enabled"] = env_bool("DEERFLOW_SCHEDULER", True)

    header = "# Generated at start by /opt/railway/render_config.py - edits are overwritten.\n"
    write_atomic(target, header + yaml.safe_dump(config, sort_keys=False, allow_unicode=True))

    names = ", ".join(m["name"] for m in config["models"]) or "NONE (set a provider API key on the Gateway service)"
    sandbox = "e2b" if "e2b" in config["sandbox"]["use"] else "local (bash disabled)"
    log(f"config written: models=[{names}] sandbox={sandbox} search={search} persistence={persistence} "
        f"registration={'open' if config['auth']['local']['allow_registration'] else 'closed'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
