#!/bin/bash
set -e

INSTALL_DIR="$HOME/.local/share/battery-monitor"
SERVICE_NAME="battery-monitor.service"

echo "Installing battery-monitor"
mkdir -p "$INSTALL_DIR"
cp notify.py battery-monitor.py requirements.txt "$INSTALL_DIR/"

echo "Creating venv"
python -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

echo "Installing as systemd service..."
mkdir -p "$HOME/.config/systemd/user/"
cp "$SERVICE_NAME" "$HOME/.config/systemd/user/"

echo "Systemctl reload and enable"
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user start "$SERVICE_NAME"

echo "Installation complete"
