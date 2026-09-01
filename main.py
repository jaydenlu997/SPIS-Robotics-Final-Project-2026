import sys
sys.path.append("/usr/lib/python3/dist-packages")
from Camera import SetupPICamera, RunPICamera_intersection, EndPICamera, match_places_ignore_tape_rgb, match_places_orb
from DirectionEnum import Direction
from Motor import DCMotor
import time
import random

# Tunable parameters
DRIVE_SPEED = 0.8       # Forward straight speed (0.0 to 1.0)
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


def main():
    camera = SetupPICamera()

    left = DCMotor(
        in1=25,
        in2=18,
        pwm=23,
    )

    right = DCMotor(
        in1=12,
        in2=16,
        pwm=24,
    )
    
    lastTime = time.time()
    lastTurnTime = time.time()
    
    # time to roughly keep track of our position
    startCoordTime = time.time()
    xCoord = 0
    yCoord = 0
    
    vertexCtr = 0
    seenVertices = []
    graphMap = [0]
    
    try:
        print("Starting the camera ...")
        camera.start()
        time.sleep(1)  # Warm up camera

        no_detected_count = 0
        NO_DETECTED_THRESHOLD = 4  # Require 4 consecutive missing frames before stopping
        is_moving = False

        while True:
            img, paths, shift = RunPICamera_intersection(camera)

            """
            # run vertex recognition every 0.5 sec
            currentTime = time.time()
            if currentTime - lastTime > 0.5:
                if Direction.RIGHT in paths or Direction.LEFT in paths:
                    seenVertex = False
                    for vertex in seenVertices:
                        if match_places_orb(vertex, img):
                            print("found visited vertex")
                            seenVertex = True
                            break
                    if not seenVertex:
                        seenVertices.append(img)
                        vertexCtr += 1
                lastTime = currentTime
            """

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
                    pass

            time.sleep(0.04)
    
    except KeyboardInterrupt:
        pass
    finally:
        EndPICamera(camera)
        left.move(0)
        right.move(0)

if __name__ == "__main__":
    main()