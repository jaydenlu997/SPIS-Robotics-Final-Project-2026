from Motor import DCMotor
from Camera import SetupPICamera, RunPICamera, EndPICamera

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
      
      left.move(-1)
      right.move(1)
except KeyboardInterrupt:
    pass
finally:
    left.move(0)
    right.move(0)

    EndPICamera(camera)