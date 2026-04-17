import time
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

K_p = 2**-1
K_i = 2**-5
K_d = 2**-4

INTEGRAL_SAMPLES = 150
# TARGET_TEMP = 25
TARGET_TEMP = 23.3333

# networking.socket_connect("secondary")


def message_received(client, topic, message):
    for zone in range(node_config.num_zones):
        if topic != f"temperature-zone-{zone + 1}":
            continue

        temps[zone] = utils.f_to_c(float(message))

    if topic == f"temperature-zone-{node_config.num_zones + 1}":
        pid()


networking.mqtt_initialize()
networking.mqtt_connect(
    [f"temperature-zone-{i + 1}" for i in range(node_config.num_zones)],
    message_received,
)
# networking.socket_connect("secondary")

temps = [0, 0, 0]
last_e = [0] * node_config.num_zones
int_e = [[]] * node_config.num_zones
last_t = 0


def read_lm35s():
    global temps

    for zone in range(node_config.num_zones):
        # lm35 = sensors.zone_lm35s[zone]
        # adc = lm35.value
        # v = adc * adc_to_V
        # T = V_to_c * v

        # temps[zone] = T

        # T_f = utils.c_to_f(T)
        # networking.mqtt_publish_message(
        #     networking.TEMP_FEEDS[zone], round(T_f * 100) / 100
        # )

        networking.mqtt_publish_message(networking.TEMP_FEEDS[zone], 85)

        # print(f"Zone {zone} temp (f): {T_f}")
        # print(f"Zone {zone} lm35: {adc}")


def pid():
    global temps, last_e, last_t, int_e, K_p, K_i, K_d

    t = time.monotonic()

    if last_t == 0:
        last_t = t
        return

    dt = t - last_t
    last_t = t
    average_temp = 0

    for zone in range(node_config.num_zones):
        zone_temp = temps[zone]
        average_temp += zone_temp

        e = abs(TARGET_TEMP - zone_temp)
        de = e - last_e[zone]
        last_e[zone] = e

        de_dt = de / dt

        int_e[zone].append(e * dt)
        int_e[zone] = int_e[zone][-INTEGRAL_SAMPLES:]
        summed_int_e = sum(int_e[zone])

        u = K_p * e + K_i * summed_int_e + K_d * de_dt
        u = min(1, max(0, u))

        percentage = u * 100

        networking.mqtt_publish_message(
            networking.DAMPER_FEEDS[zone], round(percentage)
        )

    average_temp /= node_config.num_zones
    heating = average_temp < TARGET_TEMP
    cooling = average_temp > TARGET_TEMP

    damper_command = command.Command(
        type=command.TYPE_HEAT_COOL, values=[f"{heating}" f"{cooling}"]
    )

    networking.socket_send_message(damper_command)

    networking.mqtt_publish_message(networking.COOLING_FEED, f"{cooling}")
    networking.mqtt_publish_message(networking.HEATING_FEED, f"{heating}")


def loop():
    read_lm35s()
    pid()
    heart.loop()
