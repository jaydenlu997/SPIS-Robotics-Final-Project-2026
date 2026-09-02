import time
import random
from Motor import DCMotor
from Camera import SetupPICamera, RunPICamera_intersection, EndPICamera
from Direction import Direction

left = DCMotor(in1=25, in2=18, pwm=23)
right = DCMotor(in1=16, in2=12, pwm=24)

camera = SetupPICamera()

# Tunable parameters
DRIVE_SPEED = 0.8       # Forward straight speed (0.0 to 1.0)
TURN_SPEED = 1.0       # Turning power (0.0 to 1.0)
MIN_TURN_DURATION = 0.70  # Minimum time (seconds) to rotate before checking alignment
NO_DETECTED_THRESHOLD = 4 # Consecutive frames without tape before stopping
STRAIGHT_KP = 1.0        # Proportional gain for straight driving micro-adjustments
TURN_FORWARD_DELAY = 0.3 # Time (seconds) to drive forward to align wheelbase before pivoting

def turn_right_visual(camera, left_motor, right_motor, turn_speed=TURN_SPEED, min_turn_time=MIN_TURN_DURATION, timeout=4.0):
    print(f"Starting in-place turn right (power {turn_speed}, min_time {min_turn_time}s)...")
    
    # Kickstart burst to overcome static friction
    left_motor.move(1.0)
    right_motor.move(-1.0)
    time.sleep(0.05)
    
    left_motor.move(turn_speed)
    right_motor.move(-turn_speed)
    
    # Phase 1: Guaranteed rotation time to get close to 90 degrees
    time.sleep(min_turn_time)
    
    start_time = time.time()
    
    # Phase 2: Require consecutive STRAIGHT frames to confirm alignment on the new line
    straight_confirmations = 0
    while time.time() - start_time < timeout:
        img, paths, shift = RunPICamera_intersection(camera)
        if Direction.STRAIGHT in paths:
            straight_confirmations += 1
            if straight_confirmations >= 2:
                print("Confirmed straight path alignment!")
                break
        else:
            straight_confirmations = 0
        time.sleep(0.04)
            
    left_motor.stop()
    right_motor.stop()


def turn_left_visual(camera, left_motor, right_motor, turn_speed=TURN_SPEED, min_turn_time=MIN_TURN_DURATION, timeout=4.0):
    print(f"Starting in-place turn left (power {turn_speed}, min_time {min_turn_time}s)...")
    
    # Kickstart burst to overcome static friction
    left_motor.move(-1.0)
    right_motor.move(1.0)
    time.sleep(0.05)
    
    left_motor.move(-turn_speed)
    right_motor.move(turn_speed)

    # Phase 1: Guaranteed rotation time to get close to 90 degrees
    time.sleep(min_turn_time)

    start_time = time.time()
    
    # Phase 2: Require consecutive STRAIGHT frames to confirm alignment on the new line
    straight_confirmations = 0
    while time.time() - start_time < timeout:
        img, paths, shift = RunPICamera_intersection(camera)
        if Direction.STRAIGHT in paths:
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

    print("Running intersection motor test loop (Ctrl+C to stop)...")

    no_detected_count = 0
    NO_DETECTED_THRESHOLD = 4  # Require 4 consecutive missing frames before stopping
    is_moving = False

    while True:
        img, paths, shift = RunPICamera_intersection(camera)

        if len(paths) == 1:
            direction = paths[0]
            if direction == Direction.STRAIGHT:
                no_detected_count = 0
                
                if not is_moving:
                    # Kickstart burst to overcome static friction when starting from a stop
                    left.move(1.0)
                    right.move(1.0)
                    time.sleep(0.05)
                    is_moving = True
                
                # Calculate adjusted speeds based on shift
                left_speed = DRIVE_SPEED
                right_speed = DRIVE_SPEED
                
                if shift > 0:
                    # Steer right: slow down the right motor
                    right_speed = max(0.0, DRIVE_SPEED - (shift * STRAIGHT_KP))
                else:
                    # Steer left: slow down the left motor (shift is negative)
                    left_speed = max(0.0, DRIVE_SPEED + (shift * STRAIGHT_KP))
                
                left.move(left_speed)
                right.move(right_speed)
            elif direction == Direction.RIGHT:
                no_detected_count = 0
                
                # Drive forward slightly to align the wheels with the corner
                left.move(DRIVE_SPEED)
                right.move(DRIVE_SPEED)
                time.sleep(TURN_FORWARD_DELAY)

                is_moving = False
                left.stop()
                right.stop()
                time.sleep(0.5)
                turn_right_visual(camera, left, right, turn_speed=TURN_SPEED)
            elif direction == Direction.LEFT:
                no_detected_count = 0
                
                # Drive forward slightly to align the wheels with the corner
                left.move(DRIVE_SPEED)
                right.move(DRIVE_SPEED)
                time.sleep(TURN_FORWARD_DELAY)
                
                is_moving = False
                left.stop()
                right.stop()
                time.sleep(0.5)
                turn_left_visual(camera, left, right, turn_speed=TURN_SPEED)
            elif direction == Direction.NO_DETECTED:
                no_detected_count += 1
                if no_detected_count >= NO_DETECTED_THRESHOLD:
                    is_moving = False
                    left.stop()
                    right.stop()
                    print("no line detected")
        elif len(paths) > 1:
            # INTERSECTION DETECTED (3-way or 4-way)
            no_detected_count = 0
            
            chosen_direction = random.choice(paths)
            print(f"INTERSECTION DETECTED! Available paths: {[p.name for p in paths]}")
            print(f"Randomly chose to go: {chosen_direction.name}")

            # Drive forward slightly to align the wheels with the center of the intersection
            left.move(DRIVE_SPEED)
            right.move(DRIVE_SPEED)
            time.sleep(TURN_FORWARD_DELAY)
            
            is_moving = False
            left.stop()
            right.stop()
            time.sleep(0.5)

            if chosen_direction == Direction.LEFT:
                turn_left_visual(camera, left, right, turn_speed=TURN_SPEED)
            elif chosen_direction == Direction.RIGHT:
                turn_right_visual(camera, left, right, turn_speed=TURN_SPEED)
            elif chosen_direction == Direction.STRAIGHT:
                # If we chose to go straight through the intersection, just continue!
                # We already drove into the intersection, so the next frames will pick up the straight line again.
                pass

        time.sleep(0.04)  # ~20-25 Hz camera polling rate to reduce CPU load and bus spam

except KeyboardInterrupt:
    pass
finally:
    left.stop()
    right.stop()
    EndPICamera(camera)

