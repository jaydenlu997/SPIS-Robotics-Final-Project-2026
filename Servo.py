from adafruit_servokit import ServoKit

class Servo:
  def __init__(self, servoObj):
    self.servoObj = servoObj

    self.servoObj.throttle = None
    self.servoObj.set_pulse_width_range(1200, 1800)

  def SetThrottle(self, throttle):
    self.servoObj.throttle = throttle


