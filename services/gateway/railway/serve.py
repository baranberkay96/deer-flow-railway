"""Run the DeerFlow Gateway on one dual-stack socket.

`uvicorn --host ::` is IPv6-only (asyncio sets IPV6_V6ONLY), which Railway's
IPv4 healthcheck cannot reach; `--host 0.0.0.0` is IPv4-only, which older
Railway environments with IPv6-only private networking cannot reach. This
launcher binds a single AF_INET6 socket with IPV6_V6ONLY=0 (IPv4 + IPv6) and
hands it to uvicorn. Falls back to 0.0.0.0 when the container has no IPv6.

Same server settings as upstream's command:
  uvicorn app.gateway.app:app --port 8001 --workers 1 --timeout-graceful-shutdown 10
"""

from __future__ import annotations

import os
import socket

import uvicorn

APP = "app.gateway.app:app"


def bind_socket(port: int) -> socket.socket:
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        sock.bind(("::", port))
        print(f"[deerflow-railway] Gateway listening on [::]:{port} (IPv4 + IPv6)", flush=True)
        return sock
    except OSError as exc:
        print(f"[deerflow-railway] IPv6 unavailable ({exc}); listening on 0.0.0.0:{port}", flush=True)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        return sock


def main() -> None:
    port = int(os.environ.get("PORT", "8001"))
    sock = bind_socket(port)
    config = uvicorn.Config(APP, timeout_graceful_shutdown=10)
    uvicorn.Server(config).run(sockets=[sock])


if __name__ == "__main__":
    main()
