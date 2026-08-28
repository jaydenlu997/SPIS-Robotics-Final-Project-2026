from adafruit_servokit import ServoKit

class Servo:
  def __init__(self, servoObj):
    self.servoObj.throttle = 0.0
    self.servoObj = servoObj

    self.servoObj.set_pulse_width_range(1200, 1800)

  def SetThrottle(self, throttle: float):
    self.servoObj.throttle = throttle
    

