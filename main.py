from camera_test import SetupPICamera, RunPICamera, EndPICamera

def main():
  camera = SetupPICamera()

  try:
    RunPICamera(camera)
  except KeyboardInterrupt:
    pass
  finally:
    EndPICamera(camera)


if __name__ == "__main__":
  main()