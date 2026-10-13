"""Block until Postgres and Redis answer real queries.

Railway starts every service of a template in parallel, and the Gateway image
is usually ready before Postgres has finished initdb. Opening a TCP port is not
enough (Postgres restarts once during first-boot initialisation), so this runs
`SELECT 1` and `PING`. Gives up after DEERFLOW_WAIT_TIMEOUT seconds (default
1100) with exit code 1 so the restart policy retries.
"""

from __future__ import annotations

import os
import sys
import time

TIMEOUT = float(os.environ.get("DEERFLOW_WAIT_TIMEOUT", "1100"))
INTERVAL = 3.0
REPORT_EVERY = 30.0


def log(message: str) -> None:
    print(f"[deerflow-railway] {message}", flush=True)


def postgres_ready(dsn: str) -> str | None:
    """Return None when ready, otherwise a short reason (no credentials)."""
    import psycopg

    try:
        with psycopg.connect(dsn, connect_timeout=5) as conn:
            conn.execute("SELECT 1")
        return None
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready yet"
        return type(exc).__name__


def redis_ready(url: str) -> str | None:
    import redis

    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=5, socket_timeout=5)
        try:
            client.ping()
        finally:
            client.close()
        return None
    except Exception as exc:  # noqa: BLE001
        return type(exc).__name__


def main() -> int:
    checks = []
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if dsn:
        checks.append(("Postgres", lambda: postgres_ready(dsn)))
    redis_url = (os.environ.get("DEER_FLOW_STREAM_BRIDGE_REDIS_URL") or os.environ.get("REDIS_URL") or "").strip()
    if redis_url:
        checks.append(("Redis", lambda: redis_ready(redis_url)))
    if not checks:
        return 0

    started = time.monotonic()
    last_report = 0.0
    pending = list(checks)
    while pending:
        still_pending = []
        reasons = []
        for name, probe in pending:
            reason = probe()
            if reason is None:
                log(f"{name} is ready")
            else:
                still_pending.append((name, probe))
                reasons.append(f"{name}: {reason}")
        pending = still_pending
        if not pending:
            break
        elapsed = time.monotonic() - started
        if elapsed > TIMEOUT:
            log(f"giving up after {int(elapsed)}s waiting for {'; '.join(reasons)}")
            return 1
        if elapsed - last_report >= REPORT_EVERY:
            log(f"waiting for dependencies ({int(elapsed)}s): {'; '.join(reasons)}")
            last_report = elapsed
        time.sleep(INTERVAL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
