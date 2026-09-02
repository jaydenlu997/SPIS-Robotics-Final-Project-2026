import sys
sys.path.append("/usr/lib/python3/dist-packages")
from Camera import SetupPICamera, RunPICamera_intersection, EndPICamera, match_places_ignore_tape_rgb, match_places_orb
from DirectionEnum import Direction
from Motor import DCMotor
import time
import random

# Tunable parameters
DRIVE_SPEED = 0.7       # Forward straight speed (0.0 to 1.0)
TURN_SPEED = 1.0        # Turning power (0.0 to 1.0)
MIN_TURN_DURATION = 0.70 # Minimum time (seconds) to rotate before checking alignment
STRAIGHT_KP = 1.3       # Proportional gain for straight driving micro-adjustments
TURN_FORWARD_DELAY = 0.3 # Time (seconds) to drive forward to align wheelbase before pivoting

def turn_right_visual(camera, left_motor, right_motor, turn_speed=TURN_SPEED, min_turn_time=MIN_TURN_DURATION, timeout=4.0):
    print(f"Starting in-place turn right (power {turn_speed}, min_time {min_turn_time}s)...")
    
    # Kickstart burst to overcome static friction
    left_motor.move(1.0)
    right_motor.move(-1.0)
    time.sleep(0.05)
    
    left_motor.move(turn_speed)
    right_motor.move(-turn_speed)
    
    time.sleep(min_turn_time)
    
    start_time = time.time()
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

    time.sleep(min_turn_time)

    start_time = time.time()
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

def turn_180_visual(camera, left_motor, right_motor, turn_speed=TURN_SPEED, min_turn_time=MIN_TURN_DURATION * 1.8, timeout=4.0):
    print(f"Starting in-place U-Turn (power {turn_speed}, min_time {min_turn_time}s)...")
    
    # Kickstart burst to overcome static friction
    left_motor.move(1.0)
    right_motor.move(-1.0)
    time.sleep(0.05)
    
    left_motor.move(turn_speed)
    right_motor.move(-turn_speed)
    
    time.sleep(min_turn_time)
    
    start_time = time.time()
    straight_confirmations = 0
    while time.time() - start_time < timeout:
        img, paths, shift = RunPICamera_intersection(camera)
        if Direction.STRAIGHT in paths:
            straight_confirmations += 1
            if straight_confirmations >= 2:
                print("Confirmed straight path alignment after U-Turn!")
                break
        else:
            straight_confirmations = 0
        time.sleep(0.04)
            
    left_motor.stop()
    right_motor.stop()

from MazeMapper import MazeMapper

def main():
    camera = SetupPICamera()

    left = DCMotor(
        in1=25,
        in2=18,
        pwm=23,
    )

    right = DCMotor(
        in1=16,
        in2=12,
        pwm=24,
    )
    
    mapper = MazeMapper(distance_threshold=2.0)
    
    last_loop_time = time.time()
    
    try:
        print("Starting the camera ...")
        camera.start()
        time.sleep(1)  # Warm up camera

        no_detected_count = 0
        NO_DETECTED_THRESHOLD = 4  # Require 4 consecutive missing frames before stopping
        is_moving = False

        while True:
            current_time = time.time()
            dt = current_time - last_loop_time
            last_loop_time = current_time
            
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
                    
                    # Update Odometry when driving straight
                    mapper.update_odometry(dt)
                    
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
                    
                    # Corner found while not formally in an intersection? 
                    # Treat it as a forced right turn (e.g. L-corner)
                    left.move(DRIVE_SPEED)
                    right.move(DRIVE_SPEED)
                    time.sleep(TURN_FORWARD_DELAY)

                    is_moving = False
                    left.stop()
                    right.stop()
                    time.sleep(0.5)
                    turn_right_visual(camera, left, right, turn_speed=TURN_SPEED)
                    # Update mapper heading blindly since it's a forced turn
                    mapper.heading.turn(Direction.RIGHT)
                    
                elif direction == Direction.LEFT:
                    no_detected_count = 0
                    
                    left.move(DRIVE_SPEED)
                    right.move(DRIVE_SPEED)
                    time.sleep(TURN_FORWARD_DELAY)
                    
                    is_moving = False
                    left.stop()
                    right.stop()
                    time.sleep(0.5)
                    turn_left_visual(camera, left, right, turn_speed=TURN_SPEED)
                    # Update mapper heading blindly since it's a forced turn
                    mapper.heading.turn(Direction.LEFT)
                    
                elif direction == Direction.NO_DETECTED:
                    no_detected_count += 1
                    if no_detected_count >= NO_DETECTED_THRESHOLD:
                        is_moving = False
                        left.stop()
                        right.stop()
                        print("no line detected")
                        
                        action = mapper.register_dead_end()
                        if action == "U_TURN":
                            turn_180_visual(camera, left, right, turn_speed=TURN_SPEED)
                            
            elif len(paths) > 1:
                # INTERSECTION DETECTED (3-way or 4-way)
                no_detected_count = 0
                
                # Drive forward slightly to align the wheels with the center of the intersection
                left.move(DRIVE_SPEED)
                right.move(DRIVE_SPEED)
                time.sleep(TURN_FORWARD_DELAY)
                
                is_moving = False
                left.stop()
                right.stop()
                time.sleep(0.5)

                # Ask the mapper what to do!
                chosen_direction = mapper.process_intersection(img, paths, match_places_orb)
                
                if chosen_direction == Direction.LEFT:
                    turn_left_visual(camera, left, right, turn_speed=TURN_SPEED)
                elif chosen_direction == Direction.RIGHT:
                    turn_right_visual(camera, left, right, turn_speed=TURN_SPEED)
                elif chosen_direction == "U_TURN":
                    turn_180_visual(camera, left, right, turn_speed=TURN_SPEED)
                elif chosen_direction == Direction.STRAIGHT:
                    pass

            # Since the loop takes time (including turns), we reset last_loop_time here
            # so we only measure the dt of the sleep and camera processing.
            last_loop_time = time.time()
            time.sleep(0.04)
    
    except KeyboardInterrupt:
        pass
    finally:
        EndPICamera(camera)
        left.move(0)
        right.move(0)

if __name__ == "__main__":
    main()
