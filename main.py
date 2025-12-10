import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import sys

def battery_handler(interface, changed_properties, invalidated_properties):
    """
    This function triggers ONLY when upowerd sends a signal.
    """
    # We only care if the 'Percentage' or 'State' actually changed
    if 'Percentage' in changed_properties:
        level = changed_properties['Percentage']
        print(f"Event: Battery is now at {level}%")

        # --- YOUR CUSTOM LOGIC HERE ---
        if level <= 15:
            print("  [!] LOW BATTERY WARNING!")
            # Trigger your notification code here
        elif level <= 5:
            print("  [!!!] CRITICAL BATTERY!")

    if 'State' in changed_properties:
        # State: 1=Charging, 2=Discharging, etc.
        state = changed_properties['State']
        if state == 1:
            print("Event: Charger Plugged In 🔌")
        elif state == 2:
            print("Event: Charger Unplugged 🔋")

def setup_monitor():
    # 1. Integrate D-Bus with the GLib Event Loop (essential for signals)
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    # 2. Connect to System Bus
    bus = dbus.SystemBus()
    
    # 3. Get the "DisplayDevice" object (the composite battery/AC status)
    # We don't read properties here; we just define the object path we want to watch.
    display_device_path = "/org/freedesktop/UPower/devices/DisplayDevice"
    display_device = bus.get_object("org.freedesktop.UPower", display_device_path)

    # 4. Subscribe to the 'PropertiesChanged' signal
    # This connects the 'battery_handler' function to the signal.
    display_device.connect_to_signal(
        "PropertiesChanged", 
        battery_handler, 
        dbus_interface="org.freedesktop.DBus.Properties"
    )

    print("Listening for battery events... (Press Ctrl+C to stop)")
    
    # 5. Start the Event Loop (this puts the process to sleep)
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    setup_monitor()
