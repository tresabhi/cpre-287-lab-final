import time
import networking
import secrets_db
import node_config

networking.connect_to_network()
networking.mqtt_initialize()

if secrets_db.node_type == node_config.NODE_TYPE_SIMULATED:
    import simulation

    sim = simulation.Simulation(node_config.num_zones)
    f = 10

    while True:
        t0 = time.monotonic()
        networking.loop()
        sim.publish()
        t1 = time.monotonic()
        dt = t1 - t0

        loops = round(f * dt)

        i = 0
        while i < loops:
            sim.loop(1 / f)
            i += 1

else:
    pre_functions = [networking.loop]
    post_functions = []

    print("You are in manual mode")

    while True:
        command = input("Manual input: ")
        [type, *arguments] = command.split(" ")

        if type == "auto":
            if secrets_db.node_type in [
                node_config.NODE_TYPE_PRIMARY,
                node_config.NODE_TYPE_TEMPERATURE,
            ]:
                import primary_control_node

                primary_control_node.auto()
                frequency = 10
                pre_functions.extend([primary_control_node.loop])

            elif secrets_db.node_type == node_config.NODE_TYPE_SECONDARY:
                import secondary_control_node

                secondary_control_node.auto()
                pre_functions.extend([secondary_control_node.loop])

            while True:
                start_time = start = time.time()

                for f in pre_functions:
                    f()

                end_time = start = time.time()
                elapsed_seconds = end_time - start_time

                for f in post_functions:
                    f(elapsed_seconds)

        else:
            try:
                if secrets_db.node_type in [
                    node_config.NODE_TYPE_PRIMARY,
                    node_config.NODE_TYPE_TEMPERATURE,
                ]:
                    import primary_control_node

                    primary_control_node.command(type, arguments)
                else:
                    import secondary_control_node

                    secondary_control_node.command(type, arguments)
            except:
                print("Invalid command")
        
