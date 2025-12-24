import asyncio
import logging
import argparse
import sys
from upower_api import UPowerWrapper
from notify import Notifier, URGENCY_LOW, URGENCY_CRITICAL
from dbus_next.signature import Variant


# --- logging ---

parser = argparse.ArgumentParser(
    description="Battery Monitor uses dbus_next to listen PropertiesChanged signal to monitor device battery and send notifications on two levels"
)

parser.add_argument("--debug", action="store_true", help="Enable debugging mode")
parser.add_argument(
    "--no-charger-notify",
    action="store_true",
    help="Disable notifications when plugging in charger",
)
parser.add_argument(
    "-wl",
    "--warn-level",
    type=int,
    default=20,
    help="Battery warning level (default: 20)",
)
parser.add_argument(
    "-cl",
    "--crit-level",
    type=int,
    default=10,
    help="Battery critical level (default: 10)",
)
args = parser.parse_args()

LEVEL = "DEBUG" if args.debug else "INFO"
WARN_LEVEL = args.warn_level
CRIT_LEVEL = args.crit_level

logger = logging.getLogger("battery-monitor")
logging.basicConfig(level=LEVEL)


class HardwareNotFoundError(Exception):
    """Exception raised when no monitorable battery or UPS is found."""

    pass


# --- Main Class ---
class BatteryMonitor:
    def __init__(self, upower: UPowerWrapper, notifier: Notifier) -> None:
        self.upower = upower
        self.notifier = notifier
        self.device_path = None
        self.device_props_interface = None

        self.states = {
            1: "Charging",
            2: "Discharging",
            3: "Empty",
            4: "Fully Charged",
            5: "Pending Charge",
            0: "Unknown",
        }

        # --- State Tracking ---
        self.current_percentage = 0
        self.current_state = 0
        self.warn_notified = False
        self.crit_notified = False
        self.chrg_notified = False

    async def evaluate_state(self):
        pct = self.current_percentage
        state_enum = self.current_state
        state_str = self.states.get(state_enum, "Unknown")

        logger.debug(f"Status: {pct}% [{state_str}]")

        # 2 is Discharging
        if state_enum != 2:
            self.warn_notified = False
            self.crit_notified = False

            if state_enum == 1 and not args.no_charger_notify:  # Charging
                if not getattr(self, "chrg_notified", False):
                    await self.notifier.send(
                        "Battery Monitor",
                        "Charging",
                        URGENCY_LOW,
                        "battery-030-charging",
                    )
                    self.chrg_notified = True
            return

        self.chrg_notified = False

        # Check Levels (Only runs if state_enum == 2, Discharging)
        if pct <= CRIT_LEVEL:
            if not self.crit_notified:
                await self.notifier.send(
                    "BATTERY CRITICAL!",
                    f"Battery is at {pct}%. Please Charge your Device",
                    URGENCY_CRITICAL,
                    "battery-010-symbolic",
                )
                self.crit_notified = True
                self.warn_notified = True

        elif pct <= WARN_LEVEL:
            if not self.warn_notified:
                await self.notifier.send(
                    "Low Battery",
                    f"Battery is at {pct}%. Time to Recharge",
                    URGENCY_CRITICAL,
                    "battery-030-symbolic",
                )
                self.warn_notified = True

    def on_properties_changed(self, interface_name, changed_props, invalidated_props):
        def get_value(prop_value):
            return prop_value.value if isinstance(prop_value, Variant) else prop_value

        updated = False
        if "Percentage" in changed_props:
            updated_val = int(get_value(changed_props["Percentage"]))
            if updated_val != getattr(self, "last_reported_percent", -1):
                self.current_percentage = updated_val
                self.last_reported_percent = updated_val
                updated = True

        if "State" in changed_props:
            updated_state = int(get_value(changed_props["State"]))
            if updated_state != getattr(self, "last_reported_state", -1):
                self.current_state = updated_state
                self.last_reported_state = updated_state
                updated = True

        if updated:
            # Schedule async evaluation from sync callback
            asyncio.create_task(self.evaluate_state())

    async def start(self):
        try:
            # 1. Setup Connections
            await self.upower.connect()
            if not await self.notifier.connect():
                logger.warning("Warning: Notification service unavailable.")

            self.device_path = await self.upower.get_display_device()

            if not await self.upower.is_present(self.device_path):
                raise HardwareNotFoundError(
                    "No battery or UPS detected on this system."
                )

            # Fallback/Check
            if not self.device_path:
                logger.warning(
                    "Warning: Could not dynamically resolve battery path. Using default."
                )
                self.device_path = "/org/freedesktop/UPower/devices/DisplayDevice"

            logger.debug(f"Battery Monitor running on path: {self.device_path}")

            # 2. Get Properties Interface for Signals on the DEVICE
            self.device_props_interface = await self.upower._get_interface(
                self.device_path, "org.freedesktop.DBus.Properties"
            )
            self.device_props_interface.on_properties_changed(
                self.on_properties_changed
            )

            # 3. Initial State Fetch
            current_props = await self.device_props_interface.call_get_all(
                "org.freedesktop.UPower.Device"
            )

            if "Percentage" in current_props:
                self.current_percentage = current_props["Percentage"].value
            if "State" in current_props:
                self.current_state = current_props["State"].value

            await self.evaluate_state()

            # 4. Keep Alive
            await asyncio.Future()

        except Exception as e:
            logger.error(f"Monitor encountered a fatal error: {e}")


async def main():
    try:
        monitor = BatteryMonitor(UPowerWrapper(), Notifier())
        await monitor.start()
    except HardwareNotFoundError as e:
        logger.info(f"System: {e}")
        return True
    except Exception:
        return False


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
        sys.exit(0)


#         if state_enum == 1:
#     if not self.chrg_notified and not args.no_charger_notify:
#         await self.notifier.send(
#             "Battery Monitor",
#             "Charging",
#             URGENCY_LOW,
#             "battery-050-charging",
#         )
#         self.chrg_notified = True
#     self.warn_notified = False
#     self.chrg_notified = False
# elif state_enum == 2:
#     self.chrg_notified = False
#
#     # Check Levels (Only runs if state_enum == 2, Discharging)
#     if pct <= CRIT_LEVEL:
#         if not self.crit_notified:
#             await self.notifier.send(
#                 "BATTERY CRITICAL!",
#                 f"Battery is at {pct}%. Please Charge your Device",
#                 URGENCY_CRITICAL,
#                 "battery-010-symbolic",
#             )
#             self.crit_notified = True
#             self.warn_notified = True
#
#     elif pct <= WARN_LEVEL:
#         if not self.warn_notified:
#             await self.notifier.send(
#                 "Low Battery",
#                 f"Battery is at {pct}%. Time to Recharge",
#                 URGENCY_CRITICAL,
#                 "battery-030-symbolic",
#             )
#             self.warn_notified = True
# else:
#     self.chrg_notified = False
#
