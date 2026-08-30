import time
from Motor import DCMotor
from Camera import SetupPICamera, RunPICamera, EndPICamera
from Direction import Direction

left = DCMotor(in1=25, in2=18, pwm=23)
right = DCMotor(in1=12, in2=16, pwm=24)

camera = SetupPICamera()

def turn_right_visual(camera, left_motor, right_motor, speed=0.45, timeout=3.5):
    print("Starting visual turn right...")
    # Differential in-place spin
    left_motor.move(speed)
    right_motor.move(-speed)
    
    time.sleep(0.35)  # Clear the initial turn angle
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        img, direction = RunPICamera(camera)
        if direction == Direction.STRAIGHT:
            print("Successfully aligned to new path!")
            break
            
    left_motor.stop()
    right_motor.stop()



def turn_left_visual(camera, left_motor, right_motor, speed=0.45, timeout=3.5):
    print("Starting visual turn left...")
    # Differential in-place spin left
    left_motor.move(-speed)
    right_motor.move(speed)

    time.sleep(0.35)  # Clear the initial turn angle

    start_time = time.time()
    while time.time() - start_time < timeout:
        img, direction = RunPICamera(camera)
        if direction == Direction.STRAIGHT:
            print("Successfully aligned to new path!")
            break

    left_motor.stop()
    right_motor.stop()


try:
    print("Starting camera...")
    camera.start()
    time.sleep(1)  # Warm up camera

    print("Running motor test loop (Ctrl+C to stop)...")
    while True:
        img, direction = RunPICamera(camera)

        if direction == Direction.STRAIGHT:
            left.move(0.5)
            right.move(0.5)
        elif direction == Direction.RIGHT:
            turn_right_visual(camera, left, right)
        elif direction == Direction.LEFT:
            turn_left_visual(camera, left, right)
        elif direction == Direction.NO_DETECTED:
            left.stop()
            right.stop()

except KeyboardInterrupt:
    pass
finally:
    left.stop()
    right.stop()
    EndPICamera(camera)
