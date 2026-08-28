from adafruit_servokit import ServoKit
from DirectionEnum import Direction
import time
from Servo import Servo


left_servo_channel = 15
right_servo_channel = 0


servo_kit = ServoKit(channels=16)

left = servo_kit.continuous_servo[left_servo_channel]
right = servo_kit.continuous_servo[right_servo_channel] 

LeftServo = Servo(servoObj=servo_kit.continuous_servo[left_servo_channel])
RightServo = Servo(servoObj=servo_kit.continuous_servo[right_servo_channel])

directions = [Direction.STRAIGHT, Direction.LEFT, Direction.STRAIGHT, Direction.RIGHT, Direction.LEFT]

try:
    while True:
        i = input('a')

        if i == 'l':
            direction = Direction.LEFT
        elif i == 'r':
            direction = Direction.RIGHT
        else:
            direction = Direction.STRAIGHT

        print(direction)

        match direction:
            case Direction.STRAIGHT:
                LeftServo.SetThrottle(1.0)
                RightServo.SetThrottle(-1.0) 
            case Direction.RIGHT:
                LeftServo.SetThrottle(1.0)
                RightServo.SetThrottle(None) 

            #for vertex in seenVertices:
            # print("found visited vertex")
            case Direction.LEFT:
                LeftServo.SetThrottle(None)
                RightServo.SetThrottle(-1) 

            #print("found visited vertex")

        time.sleep(2)

except KeyboardInterrupt:
    pass
finally:
    left.throttle = None
    right.throttle = None

    LeftServo.SetThrottle(None)
    RightServo.SetThrottle(None)