import networking
import command
import time
import heart

networking.socket_connect("primary")


def listen(message):
    [type, *arguments] = message.split(":")
    type = int(type)

    if type == command.TYPE_HEARTBEAT:
        heart.listen()


def loop():
    heart.beat()
