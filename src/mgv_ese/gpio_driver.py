import RPi.GPIO as GPIO

class GPIODriver:
    def __init__(self, pin_red: int, pin_yellow: int, pin_green: int):
        self.pins = {
            "red": pin_red,
            "yellow": pin_yellow,
            "green": pin_green
        }
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for p in self.pins.values():
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, GPIO.LOW)  # HIGH=ON, arrancamos OFF

    def apply(self, key: str, value: str):
        pin = self.pins[key]
        if value == "ON":
            GPIO.output(pin, GPIO.HIGH)
        else:
            GPIO.output(pin, GPIO.LOW)

    def all_off(self):
        for p in self.pins.values():
            GPIO.output(p, GPIO.LOW)

    def cleanup(self):
        try:
            self.all_off()
            GPIO.cleanup()
        except Exception:
            pass
