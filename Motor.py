from gpiozero import OutputDevice, PWMOutputDevice


class DCMotor:
    def __init__(self, in1: int, in2: int, pwm: int, scale: float) -> None:
        self.in1 = OutputDevice(in1)
        self.in2 = OutputDevice(in2)
        self.pwm = PWMOutputDevice(pwm)
        self.scale = scale

    def move(self, speed: float) -> None:
        speed = min(max(speed, -1.0), 1.0) * self.scale
        if speed > 0.0:
            self.in1.on()
            self.in2.off()
        elif speed < 0.0:
            self.in1.off()
            self.in2.on()
        else:
            self.in1.off()
            self.in2.off()
        self.pwm.value = abs(speed)

    def stop(self) -> None:
        self.move(0.0)