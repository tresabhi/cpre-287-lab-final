import board
import digitalio

heating_pin = board.A0
cooling_pin = board.A1

heating_pin = digitalio.DigitalInOut(heating_pin)
cooling_pin = digitalio.DigitalInOut(cooling_pin)

heating_pin.direction = digitalio.Direction.OUTPUT
cooling_pin.direction = digitalio.Direction.OUTPUT
