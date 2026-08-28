from Camera import SetupPICamera, RunPICamera, EndPICamera, match_places_ignore_tape_rgb
from adafruit_servokit import ServoKit
from DirectionEnum import Direction
from Servo import Servo
import time

def main():
  camera = SetupPICamera()

  left_servo_channel = 0
  right_servo_channel = 1

  servo_kit = ServoKit(channels=16)

  LeftServo = Servo(servoObj=servo_kit.continuous_servo[left_servo_channel])
  RightServo = Servo(servoObj=servo_kit.continuous_servo[right_servo_channel])

  seenVertices = []


  try:
    # Continuously grab camera frames
    print("Starting the camera ...")

    # Start the camera
    camera.start()
    while (True):
      img, direction = RunPICamera(camera=camera)


      if direction == Direction.RIGHT or direction == Direction.LEFT:
        seenVertex = False
        for vertex in seenVertices:
          if match_places_ignore_tape_rgb(vertex, img):
            print("found visited vertex")
            seenVertex = True
            break
      
        if not seenVertex:
          seenVertices.append(img)

      time.sleep(0.2)
      print(len(seenVertices))


    """

      match direction:
        case Direction.STRAIGHT:
          LeftServo.SetThrottle(-1.0)
          RightServo.SetThrottle(1.0) 
        case Direction.RIGHT:
          LeftServo.SetThrottle(-1.0)
          RightServo.SetThrottle(-1.0) 

          for vertex in seenVertices:
            print("found visited vertex")
        case Direction.LEFT:
          LeftServo.SetThrottle(1.0)
          RightServo.SetThrottle(1.0) 

          print("found visited vertex")


      time.sleep(0.2)
      LeftServo.SetThrottle(0.0)
      RightServo.SetThrottle(0.0)
    """
    
  except KeyboardInterrupt:
    pass
  finally:
    EndPICamera(camera)
    LeftServo.SetThrottle(0.0)
    RightServo.SetThrottle(0.0)


if __name__ == "__main__":
  main()