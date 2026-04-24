import heart
import networking
import command
import heaters_coolers


def set_heaters(value):
    for pin in heaters_coolers.heating_pins:
        pin.value = value


def set_coolers(value):
    for pin in heaters_coolers.cooling_pins:
        pin.value = value


def set_fans(value):
    for pin in heaters_coolers.fan_pins:
        pin.value = value


def command(type, arguments):
    if type == "H":
        set_heaters(arguments[0] == "1")
        set_coolers(arguments[0] != "1")
    elif type == "C":
        set_coolers(arguments[0] == "1")
        set_heaters(arguments[0] != "1")
    elif type == "F":
        set_fans(arguments[0] == "1")


# def listen(message):
#     global test

#     [type, *arguments] = message.split(":")
#     type = int(type)

#     print(message)

#     if type == command.TYPE_HEAT_COOL:
#         heating = arguments[0] == "True"
#         cooling = arguments[1] == "True"

#         print(f"heating = {heating}\tcooling = {cooling}")

#         heaters_coolers.heating_pin.value = heating
#         heaters_coolers.cooling_pin.value = cooling
#     if type == command.TYPE_HEARTBEAT:
#         heart.listen()


# networking.connect_to_network()
# networking.socket_listen(listen)


# def loop():
#     heart.loop()
