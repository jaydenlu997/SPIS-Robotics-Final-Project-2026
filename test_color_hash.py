import cv2
import numpy as np
import time
from picamera2 import Picamera2
from libcamera import Transform

def get_color_hash(image):
    """
    Analyzes an image and returns a dictionary with the pixel count of specific colors.
    """
    # Assuming image is grabbed in BGR format
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Define HSV boundaries for the target colors.
    # Note: You may need to tune these Hue/Sat/Val numbers slightly depending on your room lighting!
    color_bounds = {
        "green":  (np.array([40, 60, 60]),  np.array([85, 255, 255])),
        "yellow": (np.array([20, 100, 100]), np.array([35, 255, 255])),
        "orange": (np.array([5, 120, 120]),  np.array([18, 255, 255])),
        "pink":   (np.array([140, 70, 70]),  np.array([170, 255, 255]))
    }
    
    hash_result = {}
    for color_name, (lower, upper) in color_bounds.items():
        mask = cv2.inRange(hsv, lower, upper)
        pixel_count = cv2.countNonZero(mask)
        hash_result[color_name] = pixel_count
        
    return hash_result

def compare_hashes(hash1, hash2, margin=0.40, min_pixels=200):
    """
    Compares two color hashes with a given error margin.
    - margin: allowed percentage difference (0.40 = 40% error allowed)
    - min_pixels: noise floor. If a color has fewer pixels than this, it's considered "0".
    """
    for color in ["green", "yellow", "orange", "pink"]:
        c1 = hash1[color]
        c2 = hash2[color]
        
        # If both are basically zero, they match
        if c1 < min_pixels and c2 < min_pixels:
            continue
            
        # If one is zero but the other has a lot, mismatch!
        if (c1 < min_pixels) != (c2 < min_pixels):
            return False
            
        # If both are present, check if the amounts are roughly similar
        diff = abs(c1 - c2)
        avg = (c1 + c2) / 2.0
        
        # If the difference is greater than the allowed margin, mismatch!
        if diff / avg > margin:
            return False
            
    return True


if __name__ == "__main__":
    camera = Picamera2()
    config = camera.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"},
        controls={"FrameRate": 30},
        transform=Transform(hflip=False, vflip=False)
    )
    camera.configure(config)
    camera.start()
    
    print("\n--- Headless Color Hash Tester ---")
    print("Camera started successfully.")
    
    saved_hash = None
    
    try:
        while True:
            cmd = input("\nCommands: [Enter/p]rint live hash, [s]ave as Node A, [c]ompare, [q]uit: ").strip().lower()
            if cmd == 'q':
                break
                
            # Grab a fresh frame
            img = camera.capture_array()
            current_hash = get_color_hash(img)
            
            if cmd == 'p' or cmd == '':
                print(f"Live Hash: {current_hash}")
            elif cmd == 's':
                saved_hash = current_hash
                print(f"*** SAVED NODE A: {saved_hash} ***")
            elif cmd == 'c':
                print(f"Live Hash: {current_hash}")
                if saved_hash:
                    print(f"Node A:    {saved_hash}")
                    if compare_hashes(saved_hash, current_hash):
                        print("-> RESULT: MATCH! These are the same node.")
                    else:
                        print("-> RESULT: FAILED! These are different nodes.")
                else:
                    print("-> Error: You must save Node A first (press 's')")
                    
    finally:
        camera.stop()
        camera.close()
