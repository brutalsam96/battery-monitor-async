#!/bin/bash
set -euo pipefail

INSTALL_DIR="$HOME/.local/share/battery-monitor"
SERVICE_NAME="battery-monitor.service"
SERVICE_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"

echo "Stopping service (if running)…"
systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true

echo "Disabling service…"
systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
systemctl --user daemon-reload

echo "Removing files…"
[ -d "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR"
[ -f "$SERVICE_PATH" ] && rm -f "$SERVICE_PATH"

echo "Uninstall complete"
