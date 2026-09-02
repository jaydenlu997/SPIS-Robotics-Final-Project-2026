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
    
    print("Camera started.")
    print("Commands:")
    print("  Press 's' to SAVE the current view as Node A")
    print("  Press 'c' to COMPARE the current view against Node A")
    print("  Press 'q' to QUIT")
    
    saved_hash = None
    
    try:
        while True:
            img = camera.capture_array()
            
            # Show live camera and current color pixel counts on screen
            current_hash = get_color_hash(img)
            
            # Print current hash onto the video frame
            y_offset = 30
            for color, count in current_hash.items():
                cv2.putText(img, f"{color}: {count}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                y_offset += 30
                
            if saved_hash:
                is_match = compare_hashes(saved_hash, current_hash)
                status_text = "MATCHES NODE A!" if is_match else "No Match"
                color = (0, 255, 0) if is_match else (0, 0, 255)
                cv2.putText(img, status_text, (10, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)

            cv2.imshow("Color Hash Test", img)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                saved_hash = current_hash
                print(f"\n[SAVED NODE A] {saved_hash}")
            elif key == ord('c'):
                if saved_hash:
                    print(f"\n[COMPARING]")
                    print(f"Node A:  {saved_hash}")
                    print(f"Current: {current_hash}")
                    if compare_hashes(saved_hash, current_hash):
                        print("-> RESULT: SUCCESS! Matches Node A.")
                    else:
                        print("-> RESULT: FAILED! Does not match.")
                else:
                    print("Press 's' to save a node first!")
                    
    finally:
        cv2.destroyAllWindows()
        camera.stop()
        camera.close()
