import networking
from secrets_db import *
from node_config import num_zones, zone_k
import time
from utils import c_to_f, f_to_c
from math import sin, pi
import acturators

# define some values?

SIM_SPEED = 1

TEMP_RANGE = 10
TEMP_AVG = 10

INTEGRAL_SAMPLES = 150

TEMPERATURE_THRESHOLD = 2

# k is the volume of the room divided by the surface area exposed to the outside
# so we need to divide it by some constant to get a reasonable coefficient
# for the derivative of the temperatures respect to time
INITIAL_TARGET_TEMP = 25
START_TEMP = TEMP_AVG

# The Simulation(R)
_sim = None

# We only want ONE Simulation object, and we want to share it between all of the modules. We can accomplish this
# using the singleton design pattern. This function is a key part of that pattern. It returns the singleton instance.
# Call "simulation.get_instance()" to get a Simulation, instead of instantiating a Simulation directly.
def get_instance():
    global _sim

    if _sim is None:
        _sim = Simulation(num_zones)

    return _sim


# A class that simulates the physical environment for the system.
class Simulation:
    initial_time = time.monotonic()
    zone_temps = {}
    outside_temp = 0

    t = 0

    xs = [0] * num_zones
    percentages = [0] * num_zones
    angles = [0] * num_zones

    heating = False
    cooling = False

    last_e = [0] * num_zones
    int_e = [[]] * num_zones

    K_p = 1
    K_i = 1
    K_d = 0.125

    # Initializes the simulation.
    def __init__(self, num_zones):
        # initialize additional class variables. These are probably variables that represent the state of the physical system.

        for id in range(num_zones):
            self.zone_temps[id] = START_TEMP

        self.zone_servos = [acturators.SERVO_MIN] * num_zones
        self.target_temps = [INITIAL_TARGET_TEMP] * num_zones

        networking.mqtt_connect(
            # [f"temperature-zone-{i + 1}" for i in range(node_config.num_zones)]
            # + [f"damper-zone-{i + 1}" for i in range(node_config.num_zones)]
            [f"set-point-zone-{i + 1}" for i in range(node_config.num_zones)],
            self.message_received,
        )

        for zone in range(node_config.num_zones):
            print(f"Defaulting zone {zone + 1} to {c_to_f(INITIAL_TARGET_TEMP)} farenheit")
            networking.mqtt_publish_message(
                f"set-point-zone-{zone + 1}", c_to_f(INITIAL_TARGET_TEMP)
            )

    def message_received(self, client, topic, message):
        print("received")
        for zone in range(node_config.num_zones):
            if topic == f"set-point-zone-{zone + 1}":
                print(f"Received set point for zone {zone + 1}: {message}")
                self.target_temps[zone] = f_to_c(float(message))

    # Returns the current temperature in the zone specified by zone_id
    def get_temperature_f(self, zone_id):
        # implement
        return c_to_f(self.zone_temps[zone_id])

    # Sets the damper(s) for the zone specified by zone_id to the percentage
    # specified by percent. 0 is closed, 100 is fully open.
    def set_damper(self, type, zone_id, percent):
        print("set damper")
        # implement

    # Update the temperatures of the zones, given that elapsed_time_ms milliseconds
    # have elapsed since this was previously called.
    last_t = 0

    def _update_temps(self, t):
        import actuation

        dt = t - self.last_t
        t_days = t / 60 / 60 / 24 + 0.5

        if self.last_t == t:
            return

        self.last_t = t
        self.outside_temp = TEMP_RANGE * sin(2 * pi * (t_days - 0.25)) + TEMP_AVG

        ac_speed = 0

        if self.heating:
            ac_speed += 1

        if self.cooling:
            ac_speed -= 1

        # Update all temps
        for id in range(num_zones):
            T = self.zone_temps[id]
            k = zone_k[id]

            # angle = self.zone_servos[id]
            # x = (angle - acturators.SERVO_MIN) / acturators.SERVO_RANGE

            x = self.xs[id]

            # units for dT/dt = (1 / s) * kelvin = kelvin / s
            dT_dt = -k * (T - self.outside_temp) + ac_speed * x
            # units for dT = kelvin / s * s = kelvin
            # yay! units work out cleanly
            dT = dT_dt * dt

            self.zone_temps[id] += dT
            # self.zone_temps[id] = sensing.lm35_temperature_c(id)

    def _update_dampers(self, t):
        import actuation

        # for zone in range(num_zones):
        #     zone_temp = self.zone_temps[zone]
        #     cooling = min(1, max(0, zone_temp - TARGET_TEMP)) * 100
        #     heating = min(1, max(0, TARGET_TEMP - zone_temp)) * 100

        #     self.set_damper("cooling", zone, cooling)
        #     self.set_damper("heating", zone, heating)

        zone_id = 0
        average_temp = 0
        t_error = 0


        for zone in range(num_zones):
            zone_temp = self.zone_temps[zone]
            average_temp += zone_temp

            # percentage = (TARGET_TEMP - zone_temp) / 25
            # percentage = math.pow(abs(percentage), 1 / 3)
            # percentage = min(1, max(0, percentage))
            # percentage *= 100

            target_temp = self.target_temps[zone]
            e = abs(target_temp - zone_temp)
            de = e - self.last_e[zone]
            self.last_e[zone] = e

            dt = t - self.last_t
            de_dt = de / dt

            self.int_e[zone] = self.int_e[zone][1:INTEGRAL_SAMPLES]
            self.int_e[zone] += [e * dt]
            int_e = sum(self.int_e[zone])

            u = self.K_p * e + self.K_i * int_e + self.K_d * de_dt
            u = min(1, max(0, u))
            self.xs[zone] = u

            percentage = u * 100
            self.percentages[zone] = percentage

            angle = actuation.set_damper(zone, percentage)
            self.angles[zone] = angle

            t_error += zone_temp - target_temp

            zone_id += 1

        average_temp /= num_zones
        self.heating = t_error < 0
        self.cooling = not self.heating

        # if self.heating:
        #     # heater is already on; keep it on till we go well over the target temperature
        #     self.heating = average_temp < TARGET_TEMP + TEMPERATURE_THRESHOLD
        # else:
        #     # heating is off right now, turn it on if we get too cold
        #     self.heating = average_temp < TARGET_TEMP

        # # same logic as above but for cooling
        # if self.cooling:
        #     self.cooling = average_temp > TARGET_TEMP - TEMPERATURE_THRESHOLD
        # else:
        #     self.cooling = average_temp > TARGET_TEMP

    # Runs periodic simulation actions.
    def loop(self, dt):
        import actuation

        # Calculate the amount of time elapsed since this last time this function was run. See CircuitPython's time module documentation
        # at http://docs.circuitpython.org/en/latest/shared-bindings/time/index.html. We recommend time.monotonic_ns(). Also note that
        # temperature_measurement_node.py has an elapsed time calculation, and you may be able to use a similar approach here.

        # pass in the actual elapsed time.
        # t = SIM_SPEED * (time.monotonic() - self.initial_time)
        t = self.t + dt
        self.t = t

        self._update_dampers(t)
        self._update_temps(t)

        actuation.set_heating(self.heating)
        actuation.set_cooling(self.cooling)

        debug = ""

        debug += f"Out: {c_to_f(self.outside_temp):.3g}F \t"

        for zone in range(num_zones):
            debug += f"T{zone + 1}: {c_to_f(self.zone_temps[zone]):.3g}F \t"
        
        for zone in range(num_zones):
            debug += f"X{zone + 1}: {self.percentages[zone]:.0f}% \t"

        debug += f"H: {self.heating} \t"
        debug += f"C: {self.cooling}"

        print(debug)

    def publish(self):
        for zone in range(num_zones):
            temp = self.zone_temps[zone]
            percent = self.percentages[zone]

            networking.mqtt_publish_message(f"temperature-zone-{zone + 1}", c_to_f(temp))
            networking.mqtt_publish_message(f"damper-zone-{zone + 1}", percent)
            networking.mqtt_publish_message(networking.COOLING_FEED, f"{self.cooling}")
            networking.mqtt_publish_message(networking.HEATING_FEED, f"{self.heating}")
