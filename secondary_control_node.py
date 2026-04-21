import networking
import command
import heart
import heaters_coolers


def listen(message):
    global test

    [type, *arguments] = message.split(":")
    type = int(type)

    print(message)

    if type == command.TYPE_HEAT_COOL:
        heating = arguments[0] == "True"
        cooling = arguments[1] == "True"

        print(f"heating = {heating}\tcooling = {cooling}")

        heaters_coolers.heating_pin.value = heating
        heaters_coolers.cooling_pin.value = cooling


networking.connect_to_network()
networking.socket_listen(listen)


def loop():
    pass
    # heart.beat()
