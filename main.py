from camera_test import SetupPiCamera, RunPICamera, EndPICamera

def main():
  camera = SetupPiCamera()

  try:
    RunPICamera(camera)
  except KeyboardInterrupt:
    pass
  finally:
    EndPICamera(camera)


if __name__ == "__main__":
  main()