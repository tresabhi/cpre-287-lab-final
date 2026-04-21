import networking
import command
import heart


def listen(message):
    [type, *arguments] = message.split(":")
    type = int(type)

    print(message)

    if type == command.TYPE_HEAT_COOL:
        heating = arguments[0]
        cooling = arguments[1]

        print(f"heating = {heating}\tcooling = {cooling}")


networking.connect_to_network()
networking.socket_listen(listen)


def loop():
    pass
    # heart.beat()
