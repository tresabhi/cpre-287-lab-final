import networking
import command
import heart


def listen(message):
    [type, *arguments] = message.split(":")
    type = int(type)

    print(message)

    # if type == command.TYPE_HEARTBEAT:
    #     heart.listen()


networking.socket_listen(listen)


def loop():
    heart.beat()
