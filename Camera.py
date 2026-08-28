# Libraries to control the camera
from picamera2 import Picamera2
import cv2
import numpy as np
from DirectionEnum import Direction

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

def RunPICamera(camera: np.ndarray) -> tuple[np.ndarray, Direction]:
    # Grab a frame
    img = camera.capture_array()
    
    # Show the frame (OpenCV assumes BRG color representation)
    cv2.imshow("Camera", img)

    # Grab a frame
    img = camera.capture_array()

    direction, mask = get_turn_signal(img)
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




# thanks gemini for handling the ML

def get_turn_signal(
    image: np.ndarray,
    lower_blue: np.ndarray = np.array([95, 80, 50]),
    upper_blue: np.ndarray = np.array([135, 255, 255]),
    action_zone_ratio: float = 0.65,  # Trigger only when corner reaches bottom 35% of frame
    shift_threshold: float = 0.15
):
    """
    Evaluates an in-memory NumPy image frame of blue painter's tape.
    Returns strictly: 'LEFT', 'RIGHT', or 'STRAIGHT'.
    """
    if image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]

    h_img = image.shape[0]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV) if image.ndim == 3 else image
    tape_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # 1. Filter out background and stray blue markers
    contours, _ = cv2.findContours(tape_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return Direction.STRAIGHT, tape_mask

    largest_contour = max(contours, key=cv2.contourArea)
    clean_mask = np.zeros_like(tape_mask)
    cv2.drawContours(clean_mask, [largest_contour], -1, 255, thickness=cv2.FILLED)

    # 2. Get path bounding coordinates
    y_pts, x_pts = np.where(clean_mask > 0)
    if len(y_pts) == 0:
        return Direction.STRAIGHT, tape_mask

    y_min, y_max = y_pts.min(), y_pts.max()
    x_min, x_max = x_pts.min(), x_pts.max()
    total_width = max(1, x_max - x_min)
    total_height = max(1, y_max - y_min)

    # 3. Prevent premature triggers (only evaluate turn when corner arrives at action zone)
    corner_y = y_min
    if (corner_y / h_img) < action_zone_ratio:
        return Direction.STRAIGHT, tape_mask

    # 4. Check horizontal centroid shift between exit (top) and entry (bottom)
    h_slice = max(1, int(total_height * 0.15))
    top_slice = clean_mask[y_min : y_min + h_slice, :]
    bot_slice = clean_mask[y_max - h_slice : y_max + 1, :]

    _, x_top = np.where(top_slice > 0)
    _, x_bot = np.where(bot_slice > 0)

    if len(x_top) == 0 or len(x_bot) == 0:
        return Direction.STRAIGHT, tape_mask

    shift = (np.mean(x_top) - np.mean(x_bot)) / total_width

    # 5. Output signal
    if shift > shift_threshold:
        return Direction.RIGHT, tape_mask
    elif shift < -shift_threshold:
        return Direction.LEFT, tape_mask
    else:
        return Direction.STRAIGHT, tape_mask



# 1. Initialize ORB detector
orb = cv2.ORB_create(
    nfeatures=1000,
    scaleFactor=1.2,
    nlevels=8,
    edgeThreshold=15,
    patchSize=31,
    fastThreshold=20,
)

# FLANN Matcher for binary descriptors
FLANN_INDEX_LSH = 6
index_params = dict(
    algorithm=FLANN_INDEX_LSH,
    table_number=6,
    key_size=12,
    multi_probe_level=1,
)
search_params = dict(checks=50)
flann = cv2.FlannBasedMatcher(index_params, search_params)


def create_non_tape_mask_rgb(img_rgb: np.ndarray) -> np.ndarray:
    """Detects blue painter's tape directly from an RGB NumPy array."""
    # Convert RGB -> HSV
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)

    # OpenCV HSV ranges stay the same:
    # H: [100, 135] (Blue)
    lower_blue = np.array([100, 80, 50], dtype=np.uint8)
    upper_blue = np.array([135, 255, 255], dtype=np.uint8)

    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # Dilate slightly to mask the tape borders
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    dilated_blue = cv2.dilate(blue_mask, kernel, iterations=1)

    # Invert: 255 = keep, 0 = ignore tape
    return cv2.bitwise_not(dilated_blue)


def match_places_ignore_tape_rgb(
    img1_rgb: np.ndarray, img2_rgb: np.ndarray
) -> bool:
    """Takes two (H, W, 3) standard RGB uint8 arrays."""
    # 1. Generate masks
    mask1 = create_non_tape_mask_rgb(img1_rgb)
    mask2 = create_non_tape_mask_rgb(img2_rgb)

    # 2. Convert RGB -> Grayscale
    gray1 = cv2.cvtColor(img1_rgb, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(img2_rgb, cv2.COLOR_RGB2GRAY)

    # 3. Detect and compute with ORB using the mask
    kp1, des1 = orb.detectAndCompute(gray1, mask=mask1)
    kp2, des2 = orb.detectAndCompute(gray2, mask=mask2)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        return False

    matches = flann.knnMatch(des1, des2, k=2)
    good_matches = [
        m
        for pair in matches
        if len(pair) == 2
        for m, n in [pair]
        if m.distance < 0.75 * n.distance
    ]

    if len(good_matches) < 8:
        return False

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(
        -1, 1, 2
    )
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(
        -1, 1, 2
    )

    _, inliers = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 4.0)
    return False if inliers is None else bool(int(np.sum(inliers)) >= 15)