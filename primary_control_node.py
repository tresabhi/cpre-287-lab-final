import secrets_db
import time
import networking
import node_config
import command
import heart
import utils

adc_to_V = 2.57 / 51000
c_to_mV = 10
c_to_V = c_to_mV / 1000
V_to_c = 1 / c_to_V

K_p = 2**-1
K_i = 2**-5
K_d = 2**-4

INTEGRAL_SAMPLES = 150
target_temps = [25] * node_config.num_zones


def message_received(client, topic, message):
    for zone in range(node_config.num_zones):
        if topic == f"temperature-zone-{zone + 1}":
            print(f"Received temp for zone {zone}: {message}")
            temps[zone] = utils.f_to_c(float(message))

        if topic == f"set-point-zone-{zone + 1}":
            print(f"Received set point for zone {zone}: {message}")
            target_temps[zone] = float(message)


networking.connect_to_network()
networking.socket_connect("secondary")
networking.mqtt_initialize()
networking.mqtt_connect(
    [
        *[f"temperature-zone-{i + 1}" for i in range(node_config.num_zones)],
        *[f"set-point-zone-{i + 1}" for i in range(node_config.num_zones)],
    ],
    message_received,
)

temps = [0, 0, 0]
last_e = [0] * node_config.num_zones
int_e = [[]] * node_config.num_zones
last_t = 0


def read_lm35s():
    import temp_sensor

    global temps

    adc = temp_sensor.lm35.value
    v = adc * adc_to_V
    T = V_to_c * v

    T_f = utils.c_to_f(T)
    networking.mqtt_publish_message(
        networking.TEMP_FEEDS[secrets_db.zone_id], round(T_f * 100) / 100
    )


def pid():
    import actuation

    global temps, last_e, last_t, int_e, K_p, K_i, K_d

    t = time.monotonic()

    if last_t == 0:
        last_t = t
        return

    dt = t - last_t
    last_t = t
    average_temp = 0

    for zone in range(node_config.num_zones):
        target_temp = target_temps[zone]
        zone_temp = temps[zone]
        average_temp += zone_temp

        e = abs(target_temp - zone_temp)
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

        actuation.set_damper(zone, percentage)

    average_temp /= node_config.num_zones
    heating = average_temp < TARGET_TEMP
    cooling = average_temp > TARGET_TEMP

    heat_cool_command = command.Command(
        type=command.TYPE_HEAT_COOL, values=[f"{heating}", f"{cooling}"]
    )

    networking.socket_send_message(heat_cool_command)
    networking.mqtt_publish_message(networking.COOLING_FEED, f"{cooling}")
    networking.mqtt_publish_message(networking.HEATING_FEED, f"{heating}")

    heart.beat()


def loop():
    if secrets_db.node_type == node_config.NODE_TYPE_TEMPERATURE:
        read_lm35s()
    elif secrets_db.node_type == node_config.NODE_TYPE_PRIMARY:
        pid()
