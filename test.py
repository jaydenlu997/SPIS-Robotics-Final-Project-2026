from adafruit_servokit import ServoKit
from Servo import Servo


left_servo_channel = 0
right_servo_channel = 1


servo_kit = ServoKit(channels=16)

LeftServo = Servo(servoObj=servo_kit.continuous_servo[left_servo_channel])
RightServo = Servo(servoObj=servo_kit.continuous_servo[right_servo_channel])


try:
    while True:
        LeftServo.SetThrottle(-1.0)
        RightServo.SetThrottle(1.0)
finally:
    LeftServo.SetThrottle(0.0)
    RightServo.SetThrottle(0.0)