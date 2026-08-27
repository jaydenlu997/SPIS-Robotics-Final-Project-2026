# This is a basic program to test the camera

# General libraries
import time
# Libraries to control the camera
from picamera2 import Picamera2
import cv2
import numpy as np

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

def RunPICamera(camera):
    # Start the camera
    camera.start()
    
    # Continuously grab camera frames
    print("Starting the camera ...")
    while (True):
        
        # Grab a frame
        img = camera.capture_array()
        
        # Show the frame (OpenCV assumes BRG color representation)
        cv2.imshow("Camera", img)

        # Grab a frame
        img = camera.capture_array()

        print(classify_90deg_turn(img))
        
        # The waitKey command is needed to force openCV to show the image
        # It looks for a keystroke for x ms (with x the argument) 
        cv2.waitKey(1)
        
        

def EndPICamera(camera):
    # Clean up the resources
    print("Stopping the camera ...")
    cv2.destroyAllWindows()
    camera.stop()
    camera.close()






def classify_90deg_turn(image: np.ndarray, shift_threshold: float = 0.15) -> str:
    """
    Classifies an orthogonal path as STRAIGHT, 90_DEG_RIGHT, or 90_DEG_LEFT.
    Accepts 2D grayscale/binary or 3D BGR/RGB NumPy arrays.
    """

    # 1. Convert to grayscale if necessary
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 2. Automatically isolate the line (handles dark-on-light or light-on-dark)
    is_dark_line = np.mean(gray) > 127
    mask = (gray < 127) if is_dark_line else (gray > 127)

    y_indices, x_indices = np.where(mask)
    if len(y_indices) == 0:
        return "NO_LINE_DETECTED"

    # 3. Crop to the path bounding box
    y_min, y_max = y_indices.min(), y_indices.max()
    x_min, x_max = x_indices.min(), x_indices.max()
    total_width = x_max - x_min
    total_height = y_max - y_min

    if total_height == 0 or total_width == 0:
        return "STRAIGHT"

    # 4. Extract top 20% (exit) and bottom 20% (entry) vertical slices
    h_slice = max(1, int(total_height * 0.2))
    top_mask = mask[y_min : y_min + h_slice, :]
    bot_mask = mask[y_max - h_slice : y_max + 1, :]

    _, x_top = np.where(top_mask)
    _, x_bot = np.where(bot_mask)

    if len(x_top) == 0 or len(x_bot) == 0:
        return "STRAIGHT"

    # 5. Compute horizontal centroids
    cx_top = np.mean(x_top)
    cx_bot = np.mean(x_bot)

    # 6. Calculate normalized horizontal shift (Δx / Total Width)
    shift = (cx_top - cx_bot) / total_width

    if shift > shift_threshold:
        return "90_DEG_RIGHT"
    elif shift < -shift_threshold:
        return "90_DEG_LEFT"
    else:
        return "STRAIGHT"