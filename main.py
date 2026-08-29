
import sys
sys.path.append("/usr/lib/python3/dist-packages")
from Camera import SetupPICamera, RunPICamera, EndPICamera, match_places_ignore_tape_rgb, match_places_orb
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

  lastTime = time.time()
  lastTurnTime = time.time()

  vertexCtr = 0
  
  seenVertices = []
  graphMap = [0]



  try:
    # Continuously grab camera frames
    print("Starting the camera ...")

    # Start the camera
    camera.start()
    while (True):
      img, direction = RunPICamera(camera=camera)

      """
      # run vertex recognition every 0.5 sec
      currentTime = time.time()
      if currentTime - lastTime > 0.5:

        if direction == Direction.RIGHT or direction == Direction.LEFT:
          seenVertex = False
          for vertex in seenVertices:
            if match_places_orb(vertex, img):
              print("found visited vertex")
              seenVertex = True
              break
        
          if not seenVertex:
            seenVertices.append(img)
            vertexCtr += 1

        
        lastTime = currentTime
      """

      match direction:
          case Direction.STRAIGHT:
              LeftServo.SetThrottle(1.0)
              RightServo.SetThrottle(-1.0) 

          case Direction.RIGHT:
              LeftServo.SetThrottle(None)
              RightServo.SetThrottle(None) 

              time.sleep(0.5)

              LeftServo.SetThrottle(1.0)
              RightServo.SetThrottle(None) 

              time.sleep(0.5)

          #for vertex in seenVertices:
          # print("found visited vertex")
          case Direction.LEFT:
              LeftServo.SetThrottle(None)
              RightServo.SetThrottle(None) 

              time.sleep(0.5)

              LeftServo.SetThrottle(None)
              RightServo.SetThrottle(-1) 

              time.sleep(0.5)


  
    
  except KeyboardInterrupt:
    pass
  finally:
    EndPICamera(camera)
    LeftServo.SetThrottle(None)
    RightServo.SetThrottle(None)


if __name__ == "__main__":
  main()