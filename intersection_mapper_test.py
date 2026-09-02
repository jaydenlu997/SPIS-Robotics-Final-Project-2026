import time
import random
import cv2
import os
import numpy as np
from Motor import DCMotor
from Camera import SetupPICamera, RunPICamera_intersection, EndPICamera
from Direction import Direction

# --- Color Hash Functions ---

def get_color_hash(image, save_debug=False, filename=None):
    """
    Analyzes an image and returns a dictionary with the pixel count of specific colors.
    """
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    color_bounds = {
        "green":  (np.array([40, 60, 60]),  np.array([85, 255, 255]), (0, 255, 0)),
        "yellow": (np.array([20, 100, 100]), np.array([35, 255, 255]), (0, 255, 255)),
        "orange": (np.array([5, 120, 120]),  np.array([18, 255, 255]), (0, 165, 255)),
        "pink":   (np.array([140, 70, 70]),  np.array([170, 255, 255]), (255, 105, 180))
    }
    
    hash_result = {}
    if save_debug:
        debug_canvas = np.zeros_like(image)
        
    for color_name, (lower, upper, bgr_color) in color_bounds.items():
        mask = cv2.inRange(hsv, lower, upper)
        pixel_count = cv2.countNonZero(mask)
        hash_result[color_name] = pixel_count
        
        if save_debug:
            debug_canvas[mask > 0] = bgr_color
            
    if save_debug and filename:
        os.makedirs("debug_image", exist_ok=True)
        img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if image.ndim == 3 else image
        composite = np.hstack((img_bgr, debug_canvas))
        cv2.imwrite(filename, composite)
        print(f"[DEBUG] Wrote visual mask to {filename}")
        
    return hash_result

def compare_hashes(hash1, hash2, margin=0.40, min_pixels=200):
    """
    Compares two color hashes with a given error margin.
    """
    for color in ["green", "yellow", "orange", "pink"]:
        c1 = hash1[color]
        c2 = hash2[color]
        
        if c1 < min_pixels and c2 < min_pixels:
            continue
        if (c1 < min_pixels) != (c2 < min_pixels):
            return False
            
        diff = abs(c1 - c2)
        avg = (c1 + c2) / 2.0
        
        if diff / avg > margin:
            return False
    return True

# --- Motor and Navigation Configuration ---

# Tunable parameters
DRIVE_SPEED = 0.8
TURN_SPEED = 1.0
MIN_TURN_DURATION = 0.70
NO_DETECTED_THRESHOLD = 4
STRAIGHT_KP = 1.0
TURN_FORWARD_DELAY = 0.3

def turn_right_visual(camera, left_motor, right_motor, turn_speed=TURN_SPEED, min_turn_time=MIN_TURN_DURATION, timeout=4.0):
    print(f"Starting in-place turn right (power {turn_speed}, min_time {min_turn_time}s)...")
    
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

# --- Main Mapping Loop ---

if __name__ == "__main__":
    left = DCMotor(in1=25, in2=18, pwm=23)
    right = DCMotor(in1=16, in2=12, pwm=24)
    camera = SetupPICamera()
    
    known_nodes = [] # List of dicts: {"id": int, "hash": dict}
    next_node_id = 1
    
    try:
        print("Starting camera...")
        camera.start()
        time.sleep(1)  # Warm up camera

        print("Running Color Hash Mapper Test Loop (Ctrl+C to stop)...")

        no_detected_count = 0
        is_moving = False

        while True:
            img, paths, shift = RunPICamera_intersection(camera)

            if len(paths) == 1:
                direction = paths[0]
                if direction == Direction.STRAIGHT:
                    no_detected_count = 0
                    
                    if not is_moving:
                        left.move(1.0)
                        right.move(1.0)
                        time.sleep(0.05)
                        is_moving = True
                    
                    left_speed = DRIVE_SPEED
                    right_speed = DRIVE_SPEED
                    
                    if shift > 0:
                        right_speed = max(0.0, DRIVE_SPEED - (shift * STRAIGHT_KP))
                    else:
                        left_speed = max(0.0, DRIVE_SPEED + (shift * STRAIGHT_KP))
                    
                    left.move(left_speed)
                    right.move(right_speed)
                    
                elif direction == Direction.RIGHT:
                    no_detected_count = 0
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
                is_moving = False
                
                # Drive forward slightly to align the wheels with the center of the intersection
                left.move(DRIVE_SPEED)
                right.move(DRIVE_SPEED)
                time.sleep(TURN_FORWARD_DELAY)
                
                left.stop()
                right.stop()
                
                print(f"\n>>> INTERSECTION DETECTED! Available paths: {[p.name for p in paths]}")
                
                # --- NODE COLOR HASHING LOGIC ---
                # Take the hash of the image at the intersection
                current_hash = get_color_hash(img, save_debug=False)
                
                # Check if it matches any known node
                matched_node_id = None
                for node in known_nodes:
                    if compare_hashes(node["hash"], current_hash):
                        matched_node_id = node["id"]
                        break
                        
                if matched_node_id is not None:
                    print(f"--- NODE {matched_node_id} FOUND AGAIN! ---")
                    print(f"Hash: {current_hash}")
                else:
                    matched_node_id = next_node_id
                    next_node_id += 1
                    known_nodes.append({"id": matched_node_id, "hash": current_hash})
                    
                    print(f"*** NEW NODE DISCOVERED: NODE {matched_node_id} ***")
                    print(f"Hash: {current_hash}")
                    
                    # Create debug image for the newly discovered node
                    filename = f"debug_image/node_{matched_node_id}_{int(time.time()*1000)}.jpg"
                    get_color_hash(img, save_debug=True, filename=filename)
                    
                # --------------------------------
                
                # Pause briefly so user can see it stopped at the node
                time.sleep(0.5)
                
                chosen_direction = random.choice(paths)
                print(f"Randomly chose to go: {chosen_direction.name}")

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
        left.stop()
        right.stop()
        EndPICamera(camera)
