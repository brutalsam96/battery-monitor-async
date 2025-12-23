import asyncio
from upower_api import UPowerWrapper
from notify import Notifier, URGENCY_LOW, URGENCY_CRITICAL
from dbus_next.signature import Variant

# --- constants ---
WARN_LEVEL = 20
CRIT_LEVEL = 10


# --- Main Class ---
class BatteryMonitor:
    def __init__(self, upower: UPowerWrapper, notifier: Notifier) -> None:
        self.upower = upower
        self.notifier = notifier
        self.device_path = None
        self.device_props_interface = None

        # Battery States return as enums from upower
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

    async def evaluate_state(self):
        pct = self.current_percentage
        state_enum = self.current_state
        state_str = self.states.get(state_enum, "Unknown")

        print(f"Status: {pct}% [{state_str}]")

        # 2 is Discharging
        if state_enum != 2:
            self.warn_notified = False
            self.crit_notified = False

            if state_enum == 1: # Charging
                await self.notifier.send(
                    "Charging", f"Charging from {pct}% 🔌", URGENCY_LOW, "battery-charging"
                )

            return

        # Check Levels (Only runs if state_enum == 2, Discharging)
        if pct <= CRIT_LEVEL:
            if not self.crit_notified:
                await self.notifier.send(
                    "BATTERY CRITICAL!",
                    f"Level is {pct}%. Please Charge your Device",
                    URGENCY_CRITICAL,
                    "battery-level-0-symbolic",
                )
                self.crit_notified = True
                self.warn_notified = True

        elif pct <= WARN_LEVEL:
            if not self.warn_notified:
                await self.notifier.send(
                    "Low Battery",
                    f"Level is {pct}%. Time to Recharge",
                    URGENCY_CRITICAL,
                    "battery-level-10-symbolic",
                )
                self.warn_notified = True

    def on_properties_changed(
        self, interface_name, changed_props, invalidated_props
    ):
        def get_value(prop_value):
            return prop_value.value if isinstance(prop_value, Variant) else prop_value

        updated = False
        if "Percentage" in changed_props:
            self.current_percentage = get_value(changed_props["Percentage"])
            updated = True

        if "State" in changed_props:
            self.current_state = get_value(changed_props["State"])
            updated = True

        if updated:
            # Schedule async evaluation from sync callback
            asyncio.create_task(self.evaluate_state())

    async def start(self):
        try:
            # 1. Setup Connections
            await self.upower.connect()
            if not await self.notifier.connect():
                print("Warning: Notification service unavailable.")

            self.device_path = await self.upower.get_display_device()
            
            # Fallback/Check
            if not self.device_path:
                print("Warning: Could not dynamically resolve battery path. Using default.")
                self.device_path = "/org/freedesktop/UPower/devices/DisplayDevice"

            print(f"Monitor running on path: {self.device_path}")

            # 2. Get Properties Interface for Signals on the DEVICE
            # We use _get_interface as seen in previous usage patterns for manual DBus interaction
            self.device_props_interface = await self.upower._get_interface(
                self.device_path, "org.freedesktop.DBus.Properties"
            )
            self.device_props_interface.on_properties_changed(self.on_properties_changed)

            # 3. Initial State Fetch
            # We use Call GetAll to ensure we get the Enum (int) values to match the signal types
            # rather than the string helper methods.
            current_props = await self.device_props_interface.call_get_all("org.freedesktop.UPower.Device")
            
            if "Percentage" in current_props:
                self.current_percentage = current_props["Percentage"].value
            if "State" in current_props:
                self.current_state = current_props["State"].value

            await self.evaluate_state()

            # 4. Keep Alive
            await asyncio.Future()

        except Exception as e:
            print(f"Monitor encountered a fatal error: {e}")


async def main():
    monitor = BatteryMonitor(UPowerWrapper(), Notifier())
    await monitor.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass