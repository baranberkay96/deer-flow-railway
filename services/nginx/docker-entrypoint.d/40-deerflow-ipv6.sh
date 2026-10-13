#!/bin/sh
# Railway's network is dual-stack, so the config listens on IPv4 and IPv6.
# On a host without IPv6 the [::] listen makes nginx exit at startup; drop it
# there (same safeguard as upstream's compose launcher).
set -eu
conf=/etc/nginx/conf.d/deerflow.conf
if [ ! -e /proc/net/if_inet6 ] && [ -f "$conf" ]; then
  sed -i '/listen[[:space:]]\+\[::\]/d' "$conf"
  echo "deerflow: no IPv6 in this container, removed the [::] listen"
fi
