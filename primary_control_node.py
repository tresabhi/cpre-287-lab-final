import time
import networking
import node_config
import command as _command
import heart
import utils
import acturators

K_p = 2**-1
K_i = 2**-5
K_d = 2**-4

INTEGRAL_SAMPLES = 4
DEFAULT_TEMP = utils.f_to_c(70)
target_temps = [DEFAULT_TEMP] * node_config.num_zones

temps = [DEFAULT_TEMP] * node_config.num_zones
last_e = [0] * node_config.num_zones
int_e = [[]] * node_config.num_zones
last_t = 0


def set_damper(zone, percent):
    percent = max(0, min(100, percent))

    servo = acturators.zone_servos[zone]
    x = percent / 100
    # _min = acturators.SERVO_MIN
    # _range = acturators.SERVO_RANGE

    _min = 35
    _range = 100
    x = 1 - x

    angle = _min + _range * x
    servo.angle = angle

    networking.mqtt_publish_message(networking.DAMPER_FEEDS[zone], f"{percent}")


def command(type, arguments):
    if type == "D":
        zone = int(arguments[0]) - 1

        if zone not in list(range(node_config.num_zones)):
            return

        percentage = float(arguments[1])

        set_damper(zone, percentage)


def message_received(client, topic, message):
    for zone in range(node_config.num_zones):
        if topic == f"temperature-zone-{zone + 1}":
            print(f"Received temp for zone {zone + 1}: {message}")
            temps[zone] = utils.f_to_c(float(message))

        if topic == f"set-point-zone-{zone + 1}":
            print(f"Received set point for zone {zone + 1}: {message}")
            target_temps[zone] = utils.f_to_c(float(message))


def auto():
    networking.socket_connect("secondary")
    networking.mqtt_connect(
        [f"temperature-zone-{i + 1}" for i in range(node_config.num_zones)]
        + [f"set-point-zone-{i + 1}" for i in range(node_config.num_zones)],
        message_received,
    )

    for zone in range(node_config.num_zones):
        set_damper(zone, 0)

        print(f"Defaulting zone {zone + 1} to {utils.c_to_f(DEFAULT_TEMP)} farenheit")
        networking.mqtt_publish_message(
            f"set-point-zone-{zone + 1}", utils.c_to_f(DEFAULT_TEMP)
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
    t_error = 0

    if dt == 0:
        return

    for zone in range(node_config.num_zones):
        target_temp = target_temps[zone]
        zone_temp = temps[zone]
        average_temp += zone_temp

        t_error += zone_temp - target_temp

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

        set_damper(zone, percentage)

    average_temp /= node_config.num_zones
    heating = t_error < 0
    cooling = not heating

    heat_cool_command = _command.Command(
        type=_command.TYPE_HEAT_COOL, values=[f"{heating}", f"{cooling}"]
    )

    networking.socket_send_message(heat_cool_command)
    networking.mqtt_publish_message(networking.COOLING_FEED, f"{cooling}")
    networking.mqtt_publish_message(networking.HEATING_FEED, f"{heating}")

    heart.beat()


def loop():
    pid()
