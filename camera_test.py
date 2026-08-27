# This is a basic program to test the camera

# Libraries to control the camera
from picamera2 import Picamera2
import cv2
import numpy as np
import DirectionEnum

def SetupPICamera():

    print("Setting up the camera ...")

    # Initialize the camera
    camera = Picamera2()

    # Configure the camera
    config = camera.create_video_configuration(
        #-----------------------------------------------------
        # Picam natively uses RGB, but OpenCV, which we use for manipulating
        # and displaying images, uses BGR. So we will work with BGR.
        # We can change the settings of picam to give us BGR instead, and
        # we don't need to do an explic conversion. Confusingly, "RGB888"
        # means that frames will be grabbed BGR format (and vice versa).
        #-----------------------------------------------------
        main = {"size": (640, 480), "format": "RGB888"},
    )
    camera.configure(config)

    return camera

def RunPICamera(camera: np.ndarray) -> tuple[np.ndarray, DirectionEnum.Enum]:
    # Grab a frame
    img = camera.capture_array()
    
    # Show the frame (OpenCV assumes BRG color representation)
    cv2.imshow("Camera", img)

    # Grab a frame
    img = camera.capture_array()

    direction, mask = detect_blue_tape_turn(img)
    print(direction)

    cv2.imshow("Modified frame", mask)
    
    # The waitKey command is needed to force openCV to show the image
    # It looks for a keystroke for x ms (with x the argument) 
    cv2.waitKey(1)

    return img, direction
        
        

def EndPICamera(camera):
    # Clean up the resources
    print("Stopping the camera ...")
    cv2.destroyAllWindows()
    camera.stop()
    camera.close()




def detect_blue_tape_turn(
    image: np.ndarray,
    # Standard blue painter's tape HSV bounds in OpenCV (H: 0-180, S: 0-255, V: 0-255)
    lower_blue: np.ndarray = np.array([95, 80, 50]),
    upper_blue: np.ndarray = np.array([135, 255, 255]),
    shift_threshold: float = 0.15
) -> tuple[DirectionEnum.Enum, np.ndarray]:
    """
    Isolates blue painter's tape using HSV thresholding, filters out all other 
    surrounding colors and background, and classifies the turn.
    
    Returns:
        tuple: (direction_label, binary_mask)
    """

    # 1. Normalize image dimensions and color space
    if image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]  # Drop alpha channel if present
        
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    # 2. Isolate only the blue tape
    tape_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # 3. Extract the largest blue contour (discards stray blue noise/dots)
    contours, _ = cv2.findContours(tape_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return DirectionEnum.NO_DETECTED, tape_mask

    largest_contour = max(contours, key=cv2.contourArea)
    clean_mask = np.zeros_like(tape_mask)
    cv2.drawContours(clean_mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

    # 4. Get path bounding coordinates
    y_indices, x_indices = np.where(clean_mask > 0)
    y_min, y_max = y_indices.min(), y_indices.max()
    x_min, x_max = x_indices.min(), x_indices.max()
    
    total_width = x_max - x_min
    total_height = y_max - y_min

    if total_height == 0 or total_width == 0:
        return DirectionEnum.STRAIGHT, clean_mask

    # 5. Extract entry (bottom 15%) and exit (top 15%) slices
    h_slice = max(1, int(total_height * 0.15))
    top_slice = clean_mask[y_min : y_min + h_slice, :]
    bot_slice = clean_mask[y_max - h_slice : y_max + 1, :]

    _, x_top = np.where(top_slice > 0)
    _, x_bot = np.where(bot_slice > 0)

    if len(x_top) == 0 or len(x_bot) == 0:
        return DirectionEnum.STRAIGHT, clean_mask

    # 6. Direction classification via horizontal centroid shift (Δx / Total Width)
    cx_top = np.mean(x_top)
    cx_bot = np.mean(x_bot)
    normalized_shift = (cx_top - cx_bot) / total_width

    if normalized_shift > shift_threshold:
        direction = DirectionEnum.RIGHT
    elif normalized_shift < -shift_threshold:
        direction = DirectionEnum.LEFT
    else:
        direction = DirectionEnum.STRAIGHT

    return direction, clean_mask