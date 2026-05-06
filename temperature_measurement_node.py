import time
import secrets_db
import networking
import utils

adc_to_V = 2.57 / 51000
c_to_mV = 10
c_to_V = c_to_mV / 1000
V_to_c = 1 / c_to_V


def read_lm35s():
    import temp_sensor

    global temps

    adc = temp_sensor.lm35.value
    v = adc * adc_to_V
    T = V_to_c * v

    T_f = utils.c_to_f(T)
    print(f"Temperature (zone {secrets_db.zone_id}): {T_f} fahrenheit")
    networking.mqtt_publish_message(
        networking.TEMP_FEEDS[secrets_db.zone_id], round(T_f * 100) / 100
    )


def loop():
    read_lm35s()
    time.sleep(2.5)


def auto():
    pass
