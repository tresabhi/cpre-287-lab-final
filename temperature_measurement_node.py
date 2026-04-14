import adafruit_dotstar
import board, digitalio
from node_config import *
import networking
import time
from sensing import *
from simulation import *
import actuation


# Runs periodic node tasks.
def loop(dt):
    sim = get_instance()

    sim.loop(dt)
    time.sleep(0)

    # values = [
    #     f"t = {sim.last_t:.2f}s\t",
    #     f"Outside: {utils.c_to_f(sim.outside_temp):.2f}°f",
    # ]

    # for zone in range(node_config.num_zones):
    #     values.append(
    #         f"{node_config.zone_names[zone]}: {sensing.get_current_temperature_f(zone):.2f}°f"
    #     )

    # values += [
    #     f"Heating: {sim.heating}",
    #     f"Cooling: {sim.cooling}",
    # ]

    # for zone in range(node_config.num_zones):
    #     # values.append(f"theta_{zone} = {sim.angles[zone]:.2f}")
    #     values.append(f"x_{zone} = {sim.xs[zone]:.2f}")

    # print("\t".join(values))

    for zone in range(num_zones):
        current_temp = get_current_temperature_f(zone)
        servos = actuation.zone_servos[zone]
        angle = 0
        instance = get_instance()

        for servo in servos:
            angle += servo.angle

        angle /= len(servos)
        damper = (angle - actuation.SERVO_MIN) * (100 / actuation.SERVO_RANGE)

        networking.mqtt_publish_message(
            networking.TEMP_FEEDS[zone], round(current_temp * 100) / 100
        )
        networking.mqtt_publish_message(networking.DAMPER_FEEDS[zone], round(damper))
        networking.mqtt_publish_message(networking.COOLING_FEED, f"{instance.cooling}")
        networking.mqtt_publish_message(networking.HEATING_FEED, f"{instance.heating}")


ldo2 = digitalio.DigitalInOut(board.LDO2)
ldo2.direction = digitalio.Direction.OUTPUT


def enable_LDO2(state):
    """Set the power for the second on-board LDO to allow no current draw when not needed."""
    ldo2.value = state
    # A small delay to let the IO change state
    time.sleep(0.035)


def dotstar_color_wheel(wheel_pos):
    """Color wheel to allow for cycling through the rainbow of RGB colors."""
    wheel_pos = wheel_pos % 255

    if wheel_pos < 85:
        return 255 - wheel_pos * 3, 0, wheel_pos * 3
    elif wheel_pos < 170:
        wheel_pos -= 85
        return 0, wheel_pos * 3, 255 - wheel_pos * 3
    else:
        wheel_pos -= 170
        return wheel_pos * 3, 255 - wheel_pos * 3, 0


absolute0 = 273.15
min_temp = -5 + absolute0
max_temp = 27 + absolute0

enable_LDO2(True)
dotstar = adafruit_dotstar.DotStar(
    board.APA102_SCK, board.APA102_MOSI, 1, brightness=0.5, auto_write=True
)


def average():
    average = 0
    sim = get_instance()

    for zone in range(num_zones):
        temp = sim.zone_temps[zone]
        average += temp

    average /= num_zones
    average += absolute0

    x = (average - min_temp) / (max_temp - min_temp)
    r = 255 * x
    g = 0
    b = 255 * (1 - x)

    dotstar[0] = (r, g, b, 0.1)
