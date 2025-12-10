import dbus

def get_battery_level_dbus():
    try:
        bus = dbus.SystemBus()

        upower_obj = bus.get_object('org.freedesktop.UPower', '/org/freedesktop/UPower')

        upower_interface = dbus.Interface(upower_obj, 'org.freedesktop.UPower')
        device_path = upower_interface.GetDisplayDevice()

        device_obj = bus.get_object('org.freedesktop.UPower', device_path)

        properties_interface = dbus.Interface(device_obj, 'org.freedesktop.Dbus.Properties')

        percentage = properties_interface.Get('org.freedesktop.UPower.Device', 'Percentage')
        state = properties_interface.Get('org.freedesktop.UPower.Device', 'State')

        state_map = {
            1: "Charging",
            2: "Discharging",
            3: "Empty",
            4: "Fully Charged",
            5: "Pending Charge",
            6: "Pending Discharge"
        }

        state_str = state_map.get(state, "Unknown State")

        return f"Battery Level:{percentage:.1f}%, Status: {state_str}"

    except dbus.exceptions.DBusException as e:
        return f"Dbus Error: Couldn't connect to Upower Dbus service. ({e})"
    except Exception as e:
        return f"Unexpected error occured: ({e})"

def main():
    print(get_battery_level_dbus())

if __name__ == "__main__":
    main()
