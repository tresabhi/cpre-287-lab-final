import networking
import node_config
import command
import heart
import sensors
import utils

adc_to_V = 2.57 / 51000
c_to_mV = 10
c_to_V = c_to_mV / 1000
V_to_c = 1 / c_to_V

# networking.socket_connect("secondary")


def message_received(client, topic, message):
    pass


networking.mqtt_initialize()
networking.mqtt_connect(
    [f"temperature-zone-{i + 1}" for i in range(node_config.num_zones)],
    message_received,
)


def listen(message):
    [type, *arguments] = message.split(":")
    type = int(type)

    if type == command.TYPE_HEARTBEAT:
        heart.listen()


networking.socket_listen(listen)

temps = [0, 0, 0]


def read_lm35s():
    global temps

    for zone in range(node_config.num_zones):
        lm35 = sensors.zone_lm35s[zone]
        adc = lm35.value
        v = adc * adc_to_V
        T = V_to_c * v

        temps[zone] = T

        T_f = utils.c_to_f(T)
        networking.mqtt_publish_message(
            networking.TEMP_FEEDS[zone], round(T_f * 100) / 100
        )

        # print(f"Zone {zone} temp (f): {T_f}")
        print(f"Zone {zone} lm35: {adc}")


def loop():
    read_lm35s()
    heart.loop()
