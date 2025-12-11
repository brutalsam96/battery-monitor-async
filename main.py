import asyncio
from dbus_next.aio.message_bus import MessageBus
from dbus_next.constants import BusType

async def main():
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    introspection = await bus.introspect(
        "org.freedesktop.UPower",
        "/org/freedesktop/UPower/devices/DisplayDevice"
    )
    proxy_object = bus.get_proxy_object(
        "org.freedesktop.UPower",
        "/org/freedesktop/UPower/devices/DisplayDevice",
        introspection
    )

    device_interface = proxy_object.get_interface("org.freedesktop.UPower.Device")

    percentage = await device_interface.get_percentage()
    state_enum = await device_interface.get_state()

    states = {
        1: "Charging",
        2: "Discharging",
        3: "Empty",
        4: "Fully Charged",
        5: "Pending Charge",
        0: "Unknown"
    }

    state_str = states.get(state_enum, "Unknown")

    print(f"Battery: {percentage}%")
    print(f"Status:  {state_str}")

if __name__ == "__main__":
    asyncio.run(main())
