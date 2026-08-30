import time
from Motor import DCMotor
from Camera import SetupPICamera, RunPICamera, EndPICamera
from Direction import Direction

left = DCMotor(in1=25, in2=18, pwm=23)
right = DCMotor(in1=12, in2=16, pwm=24)

camera = SetupPICamera()

def turn_right_visual(camera, left_motor, right_motor, turn_speed=0.95, min_turn_time=0.4, timeout=3.5):
    print(f"Starting in-place turn right (power {turn_speed})...")
    left_motor.move(turn_speed)
    right_motor.move(-turn_speed)
    
    # Phase 1: Guaranteed breakaway time (sleep without spamming camera)
    time.sleep(min_turn_time)
    
    start_time = time.time()
    
    # Phase 2: Require 2 consecutive STRAIGHT frames to confirm alignment on the new line
    straight_confirmations = 0
    while time.time() - start_time < timeout:
        img, direction = RunPICamera(camera)
        if direction == Direction.STRAIGHT:
            straight_confirmations += 1
            if straight_confirmations >= 2:
                print("Confirmed straight path alignment!")
                break
        else:
            straight_confirmations = 0
        time.sleep(0.04)
            
    left_motor.stop()
    right_motor.stop()


def turn_left_visual(camera, left_motor, right_motor, turn_speed=0.95, min_turn_time=0.4, timeout=3.5):
    print(f"Starting in-place turn left (power {turn_speed})...")
    left_motor.move(-turn_speed)
    right_motor.move(turn_speed)

    # Phase 1: Guaranteed breakaway time (sleep without spamming camera)
    time.sleep(min_turn_time)

    start_time = time.time()
    
    # Phase 2: Require 2 consecutive STRAIGHT frames to confirm alignment on the new line
    straight_confirmations = 0
    while time.time() - start_time < timeout:
        img, direction = RunPICamera(camera)
        if direction == Direction.STRAIGHT:
            straight_confirmations += 1
            if straight_confirmations >= 2:
                print("Confirmed straight path alignment!")
                break
        else:
            straight_confirmations = 0
        time.sleep(0.04)

    left_motor.stop()
    right_motor.stop()


try:
    print("Starting camera...")
    camera.start()
    time.sleep(1)  # Warm up camera

    print("Running motor test loop (Ctrl+C to stop)...")

    no_detected_count = 0
    NO_DETECTED_THRESHOLD = 4  # Require 4 consecutive missing frames before stopping

    while True:
        img, direction = RunPICamera(camera)

        if direction == Direction.STRAIGHT:
            no_detected_count = 0
            left.move(0.65)
            right.move(0.65)
        elif direction == Direction.RIGHT:
            no_detected_count = 0
            turn_right_visual(camera, left, right, turn_speed=0.95)
        elif direction == Direction.LEFT:
            no_detected_count = 0
            turn_left_visual(camera, left, right, turn_speed=0.95)
        elif direction == Direction.NO_DETECTED:
            no_detected_count += 1
            if no_detected_count >= NO_DETECTED_THRESHOLD:
                left.stop()
                right.stop()
                print("no line detected")

        time.sleep(0.04)  # ~20-25 Hz camera polling rate to reduce CPU load and bus spam


except KeyboardInterrupt:
    pass
finally:
    left.stop()
    right.stop()
    EndPICamera(camera)
