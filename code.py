import time
import networking
import secrets_db
import node_config

networking.connect_to_network()
networking.mqtt_initialize()

pre_functions = [networking.loop]
post_functions = []

print("You are in manual mode you fucking idiot")

is_manual = True

while is_manual:
    command = input("Manual input: ")
    [type, *arguments] = command.split(" ")

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
    

# if secrets_db.node_type in [
#     node_config.NODE_TYPE_PRIMARY,
#     node_config.NODE_TYPE_TEMPERATURE,
# ]:
#     import primary_control_node

#     frequency = 10
#     pre_functions.extend([primary_control_node.loop])

# elif secrets_db.node_type == node_config.NODE_TYPE_SECONDARY:
#     import secondary_control_node

#     pre_functions.extend([secondary_control_node.loop])

# while True:
#     start_time = start = time.time()

#     for f in pre_functions:
#         f()

#     end_time = start = time.time()
#     elapsed_seconds = end_time - start_time

#     for f in post_functions:
#         f(elapsed_seconds)
