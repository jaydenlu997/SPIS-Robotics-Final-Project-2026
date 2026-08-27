from camera_test import SetupPICamera, RunPICamera, EndPICamera
import DirectionEnum
import time

def main():
  camera = SetupPICamera()

  try:
    # Continuously grab camera frames
    print("Starting the camera ...")

    # Start the camera
    camera.start()

    while (True):
      img, direction: DirectionEnum.Enum = RunPICamera(camera=camera)
      time.sleep(0.2)

    
  except KeyboardInterrupt:
    pass
  finally:
    EndPICamera(camera)


if __name__ == "__main__":
  main()