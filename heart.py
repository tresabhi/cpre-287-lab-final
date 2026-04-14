import command
import time
import networking
import sys

t0 = None
dts = []
dt_average = None
max_dropped_heatbeats = 3
kill_after_dead_beats = 9


def listen():
    print("heard beat")
    global t0, dts, dt_average

    if t0 == None:
        t0 = time.monotonic()

    dt = time.monotonic() - t0
    t0 = time.monotonic()

    dts.append(dt)
    dts = dts[-10:]

    dt_average = sum(dts) / len(dts)


def beat():
    print("sending beat")
    beat_command = command.Command(type=command.TYPE_HEARTBEAT, values=[])
    networking.socket_send_message(beat_command)


def loop():
    print("listening for beats")
    global dt_average, t0

    if dt_average in [None, 0]:
        return

    time_since_last = time.monotonic() - t0
    expected_heartbeats = time_since_last / dt_average

    if expected_heartbeats >= kill_after_dead_beats:
        print(
            f"Killing entire process because {kill_after_dead_beats} beats were expected by now expectations"
        )
        sys.exit(1)
    elif expected_heartbeats >= max_dropped_heatbeats:
        print(
            f"Other board is probably dead, expected {round(expected_heartbeats)} beats by now"
        )
