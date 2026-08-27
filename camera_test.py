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

    # Run the camera for this many seconds
    duration = 5


    # Start the camera
    camera.start()
    start_time = time.time()
    
    # Continuously grab camera frames
    print("Starting the camera ...")
    while (True):
        
        # Grab a frame
        img = camera.capture_array()
        
        # Show the frame (OpenCV assumes BRG color representation)
        cv2.imshow("Camera", img)

        # Grab a frame
        img = camera.capture_array()

        print(classify_curve_array(img))
        
        time.sleep(5)
        #img1 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # The waitKey command is needed to force openCV to show the image
        # It looks for a keystroke for x ms (with x the argument) 
        cv2.waitKey(1)
        
        

def EndPICamera(camera):
    # Clean up the resources
    print("Stopping the camera ...")
    cv2.destroyAllWindows()
    camera.stop()
    camera.close()



def classify_curve_array(
    image: np.ndarray, 
    curvature_threshold: float = 0.0005,
) -> str:
    
    # 1. Normalize input channel dimensions
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        annotated_img = image.copy()
    else:
        gray = image.copy()
        annotated_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    # 2. Extract line coordinates (threshold if not already binary)
    if gray.dtype != np.uint8:
        gray = (gray * 255).astype(np.uint8)

    # If the image is not strictly binary (0 or 255), apply a threshold
    unique_vals = np.unique(gray)
    if len(unique_vals) > 2:
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    else:
        thresh = gray

    # 3. Extract non-zero (x, y) coordinates
    points = cv2.findNonZero(thresh)
    if points is None or len(points) < 3:
        return "NO_LINE_DETECTED", 0.0, annotated_img

    points = points.squeeze()
    x = points[:, 0]
    y = points[:, 1]

    # 4. Fit 2nd-degree polynomial: x = a*y^2 + b*y + c
    a, b, c = np.polyfit(y, x, 2)

    # 5. Classify direction
    if abs(a) < curvature_threshold:
        direction = "STRAIGHT"
    elif a > 0:
        direction = "TURNS RIGHT"
    else:
        direction = "TURNS LEFT"

    return direction