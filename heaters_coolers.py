import board
import digitalio

heating_pins = [board.D13]
cooling_pins = [board.D9, board.D6]
fan_pins = [board.D12]

heating_pins = [digitalio.DigitalInOut(pin) for pin in heating_pins]
cooling_pins = [digitalio.DigitalInOut(pin) for pin in cooling_pins]
fan_pins = [digitalio.DigitalInOut(pin) for pin in fan_pins]

for pin in heating_pins + cooling_pins + fan_pins:
    pin.direction = digitalio.Direction.OUTPUT
