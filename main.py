
import sys
sys.path.append("/usr/lib/python3/dist-packages")
from Camera import SetupPICamera, RunPICamera, EndPICamera, match_places_ignore_tape_rgb, match_places_orb
# from adafruit_servokit import ServoKit
from DirectionEnum import Direction
from Motor import DCMotor
import time

def main():
  camera = SetupPICamera()

  motor_left = DCMotor(
    in1=25,
    in2=18,
    pwm=23,
  )

  motor_right = DCMotor(
    in1=12,
    in2=16,
    pwm=24,
  )
  
  lastTime = time.time()
  lastTurnTime = time.time()

  # time to roughly keep track of our position
  startCoordTime = time.time()
  xCoord = 0
  yCoord = 0


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

      currentTime = time.time()

   

      match direction:
          case Direction.STRAIGHT:
              #LeftServo.SetThrottle(1.0)
              #RightServo.SetThrottle(-1.0) 

              motor_left.move(0.5)
              motor_right.move(0.5)

          case Direction.RIGHT:
              #LeftServo.SetThrottle(None)
              #RightServo.SetThrottle(None) 

              motor_left.stop()
              motor_right.stop()

              time.sleep(0.5)

              #LeftServo.SetThrottle(1.0)
              #RightServo.SetThrottle(None) 

              motor_left.move(0.5)
              motor_right.stop()

              time.sleep(0.5)

          #for vertex in seenVertices:
          # print("found visited vertex")
          case Direction.LEFT:
              #LeftServo.SetThrottle(None)
              #RightServo.SetThrottle(None) 

              motor_left.stop()
              motor_right.stop()

              time.sleep(0.5)

              #LeftServo.SetThrottle(None)
              #RightServo.SetThrottle(-1) 

              motor_left.stop()
              motor_right.move(-0.5)

              time.sleep(0.5)

          case Direction.NO_DETECTED:
              motor_left.move(0)
              motor_right.move(0)

              print('NO TAPE DETECTED\n')
  
    
  except KeyboardInterrupt:
    pass
  finally:
    EndPICamera(camera)
    #LeftServo.SetThrottle(None)
    #RightServo.SetThrottle(None)

    motor_left.move(0)
    motor_right.move(0)



if __name__ == "__main__":
  main()