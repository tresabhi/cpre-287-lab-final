import time
from node_config import *
import gc

# Here we check if we need to use the "built-in" networking of the system instead of CircuitPython's
# wifi and socketpool modules. This is the case if we are running a simulation on "desktop" Python.
USE_BUILTIN_NETWORKING = False

last_target = None

try:
    import wifi
    import socketpool
except ModuleNotFoundError as e:
    import socket

    USE_BUILTIN_NETWORKING = True
import adafruit_minimqtt.adafruit_minimqtt as MQTT
import ssl

# secrets.py contains things that should not be committed to a repository, such as the WiFi SSID,
# your Adafruit IO username and key, and the IP addresses of the control nodes.
try:
    from secrets_db import *
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# TCP port for socket communications
TCP_PORT = 10287

# IPs for the primary and secondary control nodes. Pull these from the secrets dictionary.
PRIMARY_HOST = secrets["primary_node_ip"]
SECONDARY_HOST = secrets["secondary_node_ip"]


# Maximum length of a message sent over the socket. We set this to the same as the maximum Command length.
SOCKET_MESSAGE_MAX_LENGTH = 100

# Heartbeat information for the socket connection. This is used by the primary and secondary nodes to determine if the socket connection still exists
HEARTBEAT_INTERVAL_NS = 6000000000
HEARTBEAT_JITTER_NS = HEARTBEAT_INTERVAL_NS * 2
HEARTBEAT_MESSAGE = "0:Hello!"


# Configure the MQTT connection info. Currently not needed for mosquitto.
# aio_username = secrets["aio_username"]
# aio_key = secrets["aio_key"]

# These are the MQTT feeds used. Feeds that are lists are indexed by zone_id.
TEMP_FEEDS = []
SETPOINT_FEEDS = []
COOLING_FEED = "cooling"
HEATING_FEED = "heating"
COOLING_HEATING_FEED = "cooling-and-heating"
DAMPER_FEEDS = []

# # Set up some socket resources.
if USE_BUILTIN_NETWORKING:
    # The CPython socket module seems to work as a drop-in replacement for CircuitPython's SocketPool.
    pool = socket
    my_socket = socket.socket()
else:
    pool = socketpool.SocketPool(wifi.radio)
    my_socket = None

if ENABLE_MQTT:
    if secrets["mqtt_broker"] is "":
        print("Broker IP address missing")
        raise ValueError("Broker IP must be in secrets.py to connect to mqtt")
    if secrets["port"] is "":
        print("Port missing")
        raise ValueError("Broker Port must be in secrets.py to connect to mqtt")


# Connects to the configured network. Should be called before attempting any network operations.
def connect_to_network():
    if USE_BUILTIN_NETWORKING:
        # Nothing to do in this case.
        print("Using the built-in networking for this platform")
        return
    if ENABLE_MQTT is False and ENABLE_SOCKETS is False:
        print("Enable mqtt or sockets in node_config.py to connect to network")
        return
    # Check if we are not already connected.
    if wifi.radio.ap_info is None:
        # Sometimes the SSID isn't found on the first try, so we loop until connected.
        connected = False
        while not connected:
            print("Connecting to %s" % secrets["ssid"])
            try:
                wifi.radio.connect(secrets["ssid"], secrets["password"])
                print("Connected to %s!" % secrets["ssid"])
                my_ip = str(wifi.radio.ipv4_address)
                print("My IP is: " + str(my_ip))
                connected = True
            except Exception as e:
                print("Failed to connect to Wifi:", e)
    else:
        print("Already connected to WiFi")


def clean_up():
    gc.collect()


# ------------MQTT code-----------------#

# Configure a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker=secrets["mqtt_broker"],
    port=secrets["port"],
    # username=secrets["aio_username"],
    # password=secrets["aio_key"],
    socket_pool=pool,
    # ssl_context=ssl.create_default_context(),
)

# Internal state variable
_mqtt_is_initialized = False

# List of feeds that we're wanting to subscribe to but haven't yet
_queued_feeds = []

# List of feeds that we have subscribed to
_subscribed_feeds = []

# List of MQTT message received callback functions
_message_received_callbacks = []


# Callback function that is called when the MQTT client connects to the broker
def mqtt_connected(client, userdata, flags, rc):
    print("Connected to MQTT broker!")

    # Subscribe to the queued feeds
    for feed in _queued_feeds:
        print(f"Listening for topic changes on {feed}")
        client.subscribe(feed)
        _subscribed_feeds.append(feed)

    # Clear out the queued feeds list
    _queued_feeds.clear()


# Callback function that is called when the MQTT client disconnects from the broker
def mqtt_disconnected(client, userdata, rc):
    print("Disconnected from MQTT broker!")


# Callback function that is called when the MQTT client receives a message.
# This function, in turn, calls all registered callbacks from different modules.
def mqtt_message_received(client, topic, message):
    # primary_control_node.message_received(client, topic, message)

    for cb in _message_received_callbacks:
        # print(f"MQTT callback for {cb}")
        try:
            cb(client, topic, message)
        except TypeError as e:
            # Assume this means it's a one-parameter callback, such as the socket comm callback
            if "cooling-and-heating" in topic:
                import command

                cmd = command.Command(type=command.TYPE_HEAT_COOL, values=[message])
                cb(str(cmd))


# Configure the callback functions for the client.
mqtt_client.on_connect = mqtt_connected
mqtt_client.on_disconnect = mqtt_disconnected


# Initializes MQTT, including the feed lists.
def mqtt_initialize():
    global _mqtt_is_initialized

    # This function should be reentrant for simulation purposes
    if _mqtt_is_initialized:
        return

    _mqtt_is_initialized = True

    # Define the feed lists
    TEMP_FEEDS.extend([f"temperature-zone-{i}" for i in range(1, num_zones + 1)])
    SETPOINT_FEEDS.extend([f"set-point-zone-{i}" for i in range(1, num_zones + 1)])
    DAMPER_FEEDS.extend([f"damper-zone-{i}" for i in range(1, num_zones + 1)])

    # Print the defined feeds for debugging purposes
    print(
        f"Feeds available: {TEMP_FEEDS}, {SETPOINT_FEEDS}, {DAMPER_FEEDS}, {COOLING_HEATING_FEED}"
    )

    if not ENABLE_MQTT:
        print("Warning: MQTT feeds created but mqtt connection not enabled")


# Connects to the MQTT broker (if needed) and subscribes to the list of feeds provided.
# message_callback i���?e function that is called when a new message is received from a subbed feed.
def mqtt_connect(feeds=[], message_callback=None):
    if not ENABLE_MQTT:
        print("MQTT connection not enabled in node_config.py")
        return

    # Save the callback function. It will be called in the intermediate callback.
    if message_callback is not None:
        _message_received_callbacks.append(message_callback)

    # Point the MQTT client at the intermediate callback.
    mqtt_client.on_message = mqtt_message_received
    clean_up()

    if mqtt_client.is_connected():
        # Check to see if the client is connected. For some reason this throws an error if it's not, so we're
        # not even bothering to check the return value.
        # print(mqtt_client.is_connected())

        print("MQTT is already connected.")

        # If we are connected and were given feeds to subscribe to, we can do that now.
        for feed in [f for f in feeds if f not in _subscribed_feeds]:
            print(f"Listening for topic changes on {feed}")
            mqtt_client.subscribe(feed)
            _subscribed_feeds.append(feed)

    # This error will be thrown if we're not connected.
    else:
        print("MQTT not connected yet...")

        # Save the given feeds so that we can subscribe to them after we are connected.
        _queued_feeds.extend(feeds)

        # Connect the client to the MQTT broker. If the connection is successful, the on_connect callback will be called.
        print("Connecting to MQTT broker...")
        try:
            mqtt_client.connect()
            time.sleep(1)
        except Exception as e:
            print("MQTT connection error", e)


# This function will check the mqtt connection, if it's not connected it will attempt to reconnect
def mqtt_connection_check():
    if not ENABLE_MQTT:
        return False
    if not mqtt_client.is_connected():
        print("MQTT Disconnected, attempting reconnect")
        try:
            clean_up()
            mqtt_client.reconnect()
            print("MQTT Reconnected")
            return True
        except Exception as e:
            print("MQTT reconnection error: ", e)
            time.sleep(2)
            return False
    else:
        return True


# Publish a message to a feed. feed is the feed to publish to, and value is the body of the message.
def mqtt_publish_message(feed, value):
    if mqtt_connection_check():
        try:
            mqtt_client.publish(feed, value)
        except Exception as e:
            print("MQTT issue", e)


# ------------End MQTT code-----------------#


# -----------Socket comm code-----------#

# A buffer to hold data coming in over the socket connection.
socket_buffer = bytearray([0] * SOCKET_MESSAGE_MAX_LENGTH)


# Connect to the secondary node over the network socket.
def socket_connect(target):
    global last_target
    host = SECONDARY_HOST if target is "secondary" else PRIMARY_HOST
    last_target = target

    if node_type == NODE_TYPE_SIMULATED or not ENABLE_SOCKETS:
        # If we're simulating, there's nothing to do here.
        print("Setting up simulated socket connection")
        return

    # Refresh the socket - seems to help sometimes
    global my_socket
    print(f"Connecting to {target} control node {host} on port {TCP_PORT}...")

    connected = False
    while not connected:
        # Refresh the socket - seems to help
        if my_socket:
            my_socket.close()
            print("closed")
        my_socket = pool.socket()
        print("new")

        # CP's connect automatically temporarily sets the socket to blocking mode
        my_socket.setblocking(True)

        try:
            print(f"conencting to {host} {TCP_PORT}")
            my_socket.connect((host, TCP_PORT))
            print("after connect")
            connected = True
        except Exception as e:
            print(e)
            time.sleep(1)


# Internal variable for tracking if we're currently listening (secondary control node does this).
_socket_listening = False

# Handle to the function that will be called when a message is received over the socket.
_socket_callback = None


# Starts listening for incoming connections. callback_function is the function that should be
# called when a message is received.
def socket_listen(callback_function):
    # Save the callback function for later.
    global _socket_callback
    _socket_callback = callback_function

    # Update our state.
    global _socket_listening
    _socket_listening = True

    if node_type == NODE_TYPE_SIMULATED or not ENABLE_SOCKETS:
        # If we're simulating, nothing else to do here.
        print("Setting up simulated socket listen")
        return

    # Refresh the socket - seems to help sometimes
    global my_socket
    my_socket = pool.socket()
    my_socket.setblocking(False)

    my_ip = str(wifi.radio.ipv4_address)

    print(f"Binding to {my_ip} on port {TCP_PORT}")
    my_socket.bind((my_ip, TCP_PORT))

    # Start listening, allowing one connection at most.
    my_socket.listen(1)
    print("Listening for connections...")


# Send a message over the socket. msg is the message to be sent and should be a string.
def socket_send_message(msg):
    global last_target
    msg = f"{msg}|"

    if len(msg) > SOCKET_MESSAGE_MAX_LENGTH:
        print("Warning: message to long, dropped")
        return
    # print("Sending socket Message: " + msg)

    # If it's a simulated node, we directly hand the message to the receive callback function.
    if node_type == NODE_TYPE_SIMULATED or not ENABLE_SOCKETS:
        if _socket_callback is not None:
            _socket_callback(msg)
        else:
            print("Warning: simulated socket connection not found")
        return

    try:
        size = my_socket.send(msg)
        print("Sent " + str(size) + " bytes")
    except OSError as e:
        print("Error: message could not be send. Reconnecting")
        socket_connect(last_target)


# Disconnect the socket. Might not actually get called since our application lives "forever."
def socket_disconnect():
    global _socket_listening
    _socket_listening = False
    my_socket.close()


# -----------End socket comm code-----------#


# Timing variables
LOOP_INTERVAL_NS = 100000000
_prev_time = time.monotonic_ns()

connected_socket = None


# Perform regular network tasks. This includes checking for new messages on subbed MQTT feeds, and
# checking for new connections on the socket (if we are listening).
def loop():
    # Only run this function's code if LOOP_INTERVAL_NS have elapsed since the last time it was run.
    global _prev_time
    curr_time = time.monotonic_ns()
    if curr_time - _prev_time < LOOP_INTERVAL_NS:
        return

    _prev_time = curr_time

    if ENABLE_MQTT:
        # Check for new MQTT messages.
        try:
            mqtt_connection_check()
            mqtt_client.loop()
        except MQTT.MMQTTException as e:
            print("Warning: MQTT loop failed")
            pass
        except Exception as e:
            print("Warning: MQTT loop failed", e)
            pass

    if ENABLE_SOCKETS and _socket_listening:
        global connected_socket, my_socket, socket_buffer
        # Check for new socket connections.
        try:
            (new_conn, (remoteaddr, new_port)) = my_socket.accept()
            print("Connection from: " + str(remoteaddr))

            # If we already had a socket connection, close the old one
            if connected_socket:
                connected_socket.close()

            connected_socket = new_conn

        except OSError as e:
            pass

        if connected_socket:
            try:
                n = connected_socket.recv_into(socket_buffer, SOCKET_MESSAGE_MAX_LENGTH)

                msg = socket_buffer[:n].decode()
                # print("Message Received: " + str(msg))
                commands = msg.split("|")
                for command in commands:
                    if not (command.isspace() or command is ""):
                        _socket_callback(command)
            except OSError as e:
                pass
            except NameError as e:
                pass
