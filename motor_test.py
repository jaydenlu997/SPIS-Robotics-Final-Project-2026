import time
from Motor import DCMotor
from Camera import SetupPICamera, RunPICamera, EndPICamera
from Direction import Direction

left = DCMotor(in1=25, in2=18, pwm=23)
right = DCMotor(in1=12, in2=16, pwm=24)

camera = SetupPICamera()

def turn_right_visual(camera, left_motor, right_motor, turn_speed=0.9, timeout=3.5):
    print(f"Starting in-place turn right (power {turn_speed})...")
    # Differential in-place spin: left forward, right backward (zero turning radius)
    left_motor.move(turn_speed)
    right_motor.move(-turn_speed)
    
    time.sleep(0.15)  # Brief initial kick to start rotating off the current angle
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        img, direction = RunPICamera(camera)
        if direction == Direction.STRAIGHT:
            print("Successfully aligned to straight path!")
            break
            
    left_motor.stop()
    right_motor.stop()


def turn_left_visual(camera, left_motor, right_motor, turn_speed=0.9, timeout=3.5):
    print(f"Starting in-place turn left (power {turn_speed})...")
    # Differential in-place spin: left backward, right forward (zero turning radius)
    left_motor.move(-turn_speed)
    right_motor.move(turn_speed)

    time.sleep(0.15)  # Brief initial kick to start rotating off the current angle

    start_time = time.time()
    while time.time() - start_time < timeout:
        img, direction = RunPICamera(camera)
        if direction == Direction.STRAIGHT:
            print("Successfully aligned to straight path!")
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
            left.move(0.65)
            right.move(0.65)
        elif direction == Direction.RIGHT:
            turn_right_visual(camera, left, right, turn_speed=1.0)
        elif direction == Direction.LEFT:
            turn_left_visual(camera, left, right, turn_speed=1.0)
        elif direction == Direction.NO_DETECTED:
            left.stop()
            right.stop()
            print("no line detected")


except KeyboardInterrupt:
    pass
finally:
    left.stop()
    right.stop()
    EndPICamera(camera)
