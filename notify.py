from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType
from dbus_next.errors import InterfaceNotFoundError, DBusError
from dbus_next.signature import Variant

NTFY_NAME = "org.freedesktop.Notifications"
NTFY_PATH = "/org/freedesktop/Notifications"

URGENCY_LOW = 0
URGENCY_NORMAL = 1
URGENCY_CRITICAL = 2

class Notifier:
    def __init__(self):
        self.interface = None
        self.last_notification_id = 0

    async def connect(self):
        try:
            session_bus = await MessageBus(bus_type=BusType.SESSION).connect()
            ntfy_introspect = await session_bus.introspect(NTFY_NAME, NTFY_PATH)
            ntfy_proxy = session_bus.get_proxy_object(
                NTFY_NAME, NTFY_PATH, ntfy_introspect
            )
            self.interface = ntfy_proxy.get_interface(NTFY_NAME)
            return True
        except (InterfaceNotFoundError, DBusError) as e:
            print(f"Notification setup failed: {e}")
            return False

    async def send(self, summary, body, urgency=URGENCY_NORMAL, icon="battery-caution"):
        if not self.interface:
            print("Notification interface not connected. Cannot send.")
            return

        hints = {"urgency": Variant("y", urgency)}
        timeout_ms = 0 if urgency == URGENCY_CRITICAL else 5000

        try:
            new_id = await self.interface.call_notify(
                "Battery Monitor",
                self.last_notification_id,
                icon,
                summary,
                body,
                [],
                hints,
                timeout_ms,
            )
            self.last_notification_id = new_id
        except Exception as e:
            print(f"Failed to send notification: {e}")