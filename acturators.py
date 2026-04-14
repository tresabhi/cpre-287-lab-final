import board
import pwmio
import adafruit_motor

SERVO_FREQUENCY = 50
SERVO_ACTUATION_RANGE = 180  # degrees
SERVO_MIN_PULSE = 750  # us, for PWM control
SERVO_MAX_PULSE = 2250  # us, for PWM control

SERVO_FREQUENCY = 50
SERVO_MIN = 45
SERVO_MAX = 135
SERVO_RANGE = SERVO_MAX - SERVO_MIN

zone_servos = [
    board.A0,
    board.A1,
    board.A2,
]

zone_servos = [pwmio.PWMOut(pin, frequency=SERVO_FREQUENCY) for pin in zone_servos]
zone_servos = [
    [adafruit_motor.servo.Servo(servo) for servo in servos] for servos in zone_servos
]
