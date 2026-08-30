from Motor import DCMotor
from Camera import SetupPICamera, RunPICamera, EndPICamera
import time

left = DCMotor( # motor a
  in1=25,
  in2=18,
  pwm=23,
)

right = DCMotor( # Motor b
  in1=12,
  in2=16,
  pwm=24,
)

print("start")


camera = SetupPICamera()

try:

  print("Starting the camera ...")

    # Start the camera
  camera.start()
    
  while True:
      RunPICamera(camera)
      
      #LeftServo.SetThrottle(None)
      #RightServo.SetThrottle(None) 

      left.stop()
      right.stop()

      time.sleep(0.5)

      #LeftServo.SetThrottle(1.0)
      #RightServo.SetThrottle(None) 

      left.move(1)
      right.stop()

      time.sleep(1.55)

      left.stop()
      right.stop()

      
except KeyboardInterrupt:
    pass
finally:
    left.move(0)
    right.move(0)

    EndPICamera(camera)
