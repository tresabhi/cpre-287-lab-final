import networking
import command
import heart
import heaters_coolers

test = True


def listen(message):
    global test

    [type, *arguments] = message.split(":")
    type = int(type)

    print(message)

    if type == command.TYPE_HEAT_COOL:
        heating = arguments[0]
        cooling = arguments[1]

        # print(f"heating = {heating}\tcooling = {cooling}")

        heaters_coolers.heating_pin.value = test
        heaters_coolers.cooling_pin.value = not test
        test = not test

        print(
            f"heating = {heaters_coolers.heating_pin.value}\tcooling = {heaters_coolers.cooling_pin.value}"
        )


networking.connect_to_network()
networking.socket_listen(listen)


def loop():
    pass
    # heart.beat()
