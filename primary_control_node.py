import networking
from node_config import *
import command
import heart


# networking.socket_connect("secondary")


def message_received(client, topic, message):
    pass


networking.mqtt_initialize()
networking.mqtt_connect(
    [f"temperature-zone-{i + 1}" for i in range(num_zones)], message_received
)


def listen(message):
    [type, *arguments] = message.split(":")
    type = int(type)

    if type == command.TYPE_HEARTBEAT:
        heart.listen()


networking.socket_listen(listen)


def loop():
    heart.loop()
