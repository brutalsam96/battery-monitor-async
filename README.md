# Battery Monitor

A lightweight, asynchronous battery monitoring utility for Linux written in Python. It listens to `UPower` PropertiesChanged signal via DBus to track battery state and sends desktop notifications for charging status and low battery warnings.

## Features

*   **Real-time Monitoring:** efficient event-driven monitoring using `dbus-next` and `asyncio` (no polling).
*   **Notifications:** Sends desktop notifications for:
    *   Charger connected/charging started.
    *   Low battery warning.
    *   Critical battery alert.
*   **Configurable:** Customize warning levels and notifications via command-line arguments.
*   **Systemd Integration:** Runs as a user-level background service.

## Requirements

*   Python 3.8+
*   `upower` service running on the system.
*   A notification daemon (e.g., `dunst`, `mako`, `gnome-shell`, etc.).

**Python Dependencies:**

*   `dbus-next`
*   `upower-python-wrapper`

## Installation

An automated installation script is provided to set up the application and the systemd service.

1.  Clone the repository or download the source code.
2.  Make the install script executable (if necessary) and run it:

```bash
chmod +x install.sh
./install.sh
```

This script will:
*   Install the application to `$HOME/.local/share/battery-monitor`.
*   Create a virtual environment and install dependencies.
*   Install and enable a user-level systemd service (`battery-monitor.service`).

## Usage

### Managing the Service

Once installed, the application runs automatically in the background. You can control it using `systemctl`:

*   **Check status:** `systemctl --user status battery-monitor`
*   **Stop service:** `systemctl --user stop battery-monitor`
*   **Restart service:** `systemctl --user restart battery-monitor`
*   **View logs:** `journalctl --user -u battery-monitor -f`

### Manual Execution & Configuration

You can run the script manually or modify the systemd service file to change default behaviors.

```bash
/path/to/venv/python battery-monitor.py [OPTIONS]
```

**Options:**

*   `--debug`: Enable debug logging output.
*   `--no-charger-notify`: Disable the notification sent when the charger is plugged in.
*   `-wl`, `--warn-level [INT]`: Set the percentage for the **Low Battery** warning (default: 20).
*   `-cl`, `--crit-level [INT]`: Set the percentage for the **Critical Battery** warning (default: 10).

**Example:**
To set the warning level to 30% and disable charger notifications:

```bash
python battery-monitor.py --warn-level 30 --no-charger-notify
```

## Uninstallation

To remove the application and service, run the uninstall script:

```bash
chmod +x uninstall.sh
./uninstall.sh
```
