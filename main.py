import asyncio
from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from dbus_next.errors import DBusError
from dbus_next.signature import Variant

# --- constants ---
WARN_LEVEL = 20
CRIT_LEVEL = 10

URGENCY_LOW = 0
URGENCY_NORMAL = 1
URGENCY_CRITICAL = 2

LAST_NOTIFICATION_ID = 0
# --- Main Class ---
class BatteryMonitor:
    def __init__(self, notif_interface) -> None:
        self.notif_interface = notif_interface
        # Battery States return as enums from upower
        self.states = {
            1: "Charging", 2: "Discharging", 3: "Empty",
            4: "Fully Charged", 5: "Pending Charge", 0: "Unknown"
        }
        
        # --- State Tracking ---
        self.current_percentage = 0
        self.current_state = 0
        self.warn_notified = False
        self.crit_notified = False

    async def send_notification(self, summary, body, urgency=URGENCY_NORMAL, icon="battery"):
        global LAST_NOTIFICATION_ID
        
        hints = {'urgency': Variant('y', urgency)}
        timeout_ms = 0 if urgency == URGENCY_CRITICAL else 5000 
            
        try:
            new_id = await self.notif_interface.call_notify(
                "Battery Monitor", LAST_NOTIFICATION_ID, icon, summary, body, [], hints, timeout_ms
            )
            LAST_NOTIFICATION_ID = new_id
        except Exception as e:
            print(f"Failed to send notification: {e}")


    async def evaluate_state(self):
        pct = self.current_percentage
        state_enum = self.current_state
        state_str = self.states.get(state_enum, "Unknown")
        
        print(f"Status: {pct}% [{state_str}]")

        if state_enum != 2:
            self.warn_notified = False
            self.crit_notified = False
            
            if state_enum == 1:
                await self.send_notification("Charging", f"Charging from {pct}% 🔌", URGENCY_LOW)
            
            return

        # Check Levels (Only runs if state_enum == 2, Discharging)
        if pct <= CRIT_LEVEL:
            if not self.crit_notified:
                await self.send_notification(
                    "BATTERY CRITICAL!", f"Level is {pct}%. Please Charge your Device",
                    URGENCY_CRITICAL, "battery-level-0-symbolic"
                )
                self.crit_notified = True
                self.warn_notified = True

        elif pct <= WARN_LEVEL:
            if not self.warn_notified:
                await self.send_notification(
                    "Low Battery", f"Level is {pct}%. Time to Recharge",
                    URGENCY_CRITICAL, "battery-level-10-symbolic"
                )
                self.warn_notified = True

    async def on_properties_changed(self, interface_name, changed_props, invalidated_props):
        def get_value(prop_value):
            return prop_value.value if isinstance(prop_value, Variant) else prop_value

        if 'Percentage' in changed_props:
            self.current_percentage = get_value(changed_props['Percentage'])
        
        if 'State' in changed_props:
            self.current_state = get_value(changed_props['State'])
        
        await self.evaluate_state()
        
async def find_display_device_path(bus: MessageBus) -> str:
    """Finds the correct battery device path using UPower's GetDisplayDevice method."""
    try:
        upower_root_introspection = await bus.introspect("org.freedesktop.UPower", "/org/freedesktop/UPower")
        upower_root_proxy = bus.get_proxy_object("org.freedesktop.UPower", "/org/freedesktop/UPower", upower_root_introspection)
        
        upower_root_interface = upower_root_proxy.get_interface("org.freedesktop.UPower")
        
        # This call dynamically gets the actual path (e.g., /org/freedesktop/UPower/devices/battery_BAT0)
        device_path = await upower_root_interface.call_get_display_device()
        
        return device_path
    except DBusError as e:
        print(f"Error accessing UPower root object: {e}")
        # Fallback to the hardcoded path if the dynamic lookup fails, though this is discouraged
        return "/org/freedesktop/UPower/devices/DisplayDevice"


async def main():
    sys_bus = None
    ses_bus = None
    try:
        # 1. Connect to both buses
        sys_bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        ses_bus = await MessageBus(bus_type=BusType.SESSION).connect()
        
        # 2. Find the correct device path dynamically
        device_path = await find_display_device_path(sys_bus)
        
        if not device_path or device_path != "/org/freedesktop/UPower/devices/DisplayDevice":
            # If the dynamic path still returns the symlink, check if it's actually valid
            # (A laptop without a battery will often fail here)
            print("Warning: Could not dynamically resolve battery path. Using hardcoded path.")
            device_path = "/org/freedesktop/UPower/devices/DisplayDevice"
            # If your system truly lacks a battery, this is where the script will fail gracefully.
        
        # --- Setup Notifications (Session Bus) ---
        notif_introspection = await ses_bus.introspect("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
        notif_proxy = ses_bus.get_proxy_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications", notif_introspection)
        notif_interface = notif_proxy.get_interface("org.freedesktop.Notifications")

        monitor = BatteryMonitor(notif_interface)

        # --- Setup UPower (System Bus) using the dynamic path ---
        upower_introspection = await sys_bus.introspect("org.freedesktop.UPower", device_path) # Use the discovered path
        upower_proxy = sys_bus.get_proxy_object("org.freedesktop.UPower", device_path, upower_introspection) # Use the discovered path

        device_interface = upower_proxy.get_interface("org.freedesktop.UPower.Device")
        props_interface = upower_proxy.get_interface("org.freedesktop.DBus.Properties")

        # Initial Check (Calls fixed in previous revision)
        pct = await device_interface.get_percentage()
        state = await device_interface.get_state()
        
        monitor.current_percentage = pct
        monitor.current_state = state
        
        await monitor.evaluate_state()

        props_interface.on_properties_changed(monitor.on_properties_changed)
        print(f"Monitor running on path: {device_path}")
        await asyncio.Future()

    except Exception as e:
        print(f"Monitor encountered a fatal error: {e}")
        # We don't exit here, so the finally block can attempt cleanup
    finally:
        # FIX for TypeError: 'NoneType' object can't be awaited
        # We only attempt to disconnect if the variable is not None
        if sys_bus is not None:
            try:
                sys_bus.disconnect()
            except Exception:
                pass # Ignore disconnect errors when force exitting
        if ses_bus is not None:
            try:
                ses_bus.disconnect()
            except Exception:
                pass # Ignore disconnect errors when force exitting


if __name__ == "__main__":
    asyncio.run(main())
