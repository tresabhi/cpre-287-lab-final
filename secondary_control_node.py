import heart
import networking
import command as _command
import heaters_coolers


def set_heaters(value):
    for pin in heaters_coolers.heating_pins:
        pin.value = value

    networking.mqtt_publish_message(networking.HEATING_FEED, f"{value}")


def set_coolers(value):
    for pin in heaters_coolers.cooling_pins:
        pin.value = value

    networking.mqtt_publish_message(networking.COOLING_FEED, f"{value}")


def set_fans(value):
    for pin in heaters_coolers.fan_pins:
        pin.value = value

    networking.mqtt_publish_message(networking.FAN_FEED, f"{value}")


def command(type, arguments):
    value = arguments[0] == "1"

    if type == "H":
        set_heaters(value)

        if value:
            set_fans(True)
            set_coolers(False)

    elif type == "C":
        set_coolers(value)

        if value:
            set_fans(True)
            set_heaters(False)

    elif type == "F":
        set_fans(value)

        if not value:
            set_heaters(False)
            set_coolers(False)



set_heaters(False)
set_coolers(False)
set_fans(False)

def listen(message):
    global test

    [type, *arguments] = message.split(":")
    type = int(type)

    print(message)

    if type == _command.TYPE_HEAT_COOL:
        heating = arguments[0] == "True"
        cooling = arguments[1] == "True"

        print(f"heating = {heating}\tcooling = {cooling}")

        heaters_coolers.heating_pin.value = heating
        heaters_coolers.cooling_pin.value = cooling
    if type == _command.TYPE_HEARTBEAT:
        heart.listen()



def auto():
    networking.socket_listen(listen)


def loop():
    heart.loop()
