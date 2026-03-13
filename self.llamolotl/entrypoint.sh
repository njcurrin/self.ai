#!/bin/bash
set -e

# Setup PATH for Python venv
export PATH="/opt/venv/bin:${PATH}"

# Re-link editable install if host bind-mount is present
# This allows live development from the host's ./self.axolotl directory
if [ -f /workspace/axolotl/pyproject.toml ]; then
    pip install --no-build-isolation -q -e /workspace/axolotl 2>/dev/null || true
fi

# Start supervisord in foreground (supervisord runs as PID 1)
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
