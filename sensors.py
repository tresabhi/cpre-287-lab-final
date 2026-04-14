import board
import analogio

zone_lm35s = [
    board.A0,
    board.A1,
    board.A2,
]

zone_lm35s = [analogio.AnalogIn(pin) for pin in zone_lm35s]
