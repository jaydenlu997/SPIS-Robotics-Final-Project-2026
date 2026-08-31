
import os
import sys
sys.path.append("/usr/lib/python3/dist-packages")

# Set to True when connected to a monitor / desktop to see live CV window previews
ENABLE_VISUAL_PREVIEW = False

if not ENABLE_VISUAL_PREVIEW:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Libraries to control the camera
from picamera2 import Picamera2
import cv2
import numpy as np
from Direction import Direction

def SetupPICamera(show_preview: bool = ENABLE_VISUAL_PREVIEW):

    print("Setting up the camera ...")

    # Initialize the camera
    camera = Picamera2()

    # Find sensor mode with the largest area to maximize optical Field-of-View (no digital crop)
    sensor_config = {}
    try:
        modes = camera.sensor_modes
        if modes:
            best_mode = max(modes, key=lambda m: m.get("size", (0, 0))[0] * m.get("size", (0, 0))[1])
            sensor_config = {"output_size": best_mode["size"]}
    except Exception:
        pass

    # Configure camera: full sensor readout scaled to 640x480 for fast CV processing
    config = camera.create_video_configuration(
        main={"size": (640, 480), "format": "RGB888"},
        sensor=sensor_config if sensor_config else None,
    )
    camera.configure(config)

    if show_preview:
        try:
            cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Camera", 800, 600)
            cv2.namedWindow("Modified frame", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Modified frame", 800, 600)
        except Exception:
            pass

    return camera

def RunPICamera(camera, show_preview: bool = ENABLE_VISUAL_PREVIEW) -> tuple[np.ndarray, Direction, float]:
    # Grab a frame
    img = camera.capture_array()

    direction, mask, shift = get_turn_signal(img)
    print(direction)

    if show_preview:
        try:
            cv2.imshow("Camera", img)
            cv2.imshow("Modified frame", mask)
            cv2.waitKey(1)
        except Exception:
            pass

    return img, direction, shift


def EndPICamera(camera, show_preview: bool = ENABLE_VISUAL_PREVIEW):
    # Clean up the resources
    print("Stopping the camera ...")
    if show_preview:
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
    camera.stop()
    camera.close()




# thanks gemini for handling the ML

def get_turn_signal(
    image: np.ndarray,
    lower_blue: np.ndarray = np.array([95, 80, 50]),
    upper_blue: np.ndarray = np.array([135, 255, 255]),
    action_zone_ratio: float = 0.35,  # Corner must reach bottom 35% of frame (y >= 0.65 * H) to trigger turn
    shift_threshold: float = 0.15
):
    """
    Evaluates blue painter's tape and returns strictly one of:
    'left', 'right', 'straight', or 'not detected'.
    
    Also returns a 3-channel visual feedback mask for display.
    """
    h_img, w_img = image.shape[:2]
    
    # 1. Create visualization canvas
    visual_mask = np.zeros((h_img, w_img, 3), dtype=np.uint8)
    
    # Draw the trigger zone boundary line (Cyan)
    action_y = int(h_img * action_zone_ratio)
    cv2.line(visual_mask, (0, action_y), (w_img, action_y), (255, 255, 0), 1)

    # 2. Convert and isolate blue tape
    if image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV) if image.ndim == 3 else image
    tape_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # 3. Extract largest blue contour
    contours, _ = cv2.findContours(tape_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return Direction.NO_DETECTED, visual_mask, 0.0

    largest_contour = max(contours, key=cv2.contourArea)
    tape_binary = np.zeros_like(tape_mask)
    cv2.drawContours(tape_binary, [largest_contour], -1, 255, thickness=cv2.FILLED)
    
    # Render detected tape in blue on the visual mask
    visual_mask[tape_binary > 0] = [255, 120, 0]

    # 4. Extract Path Geometry
    y_pts, x_pts = np.where(tape_binary > 0)
    y_min, y_max = y_pts.min(), y_pts.max()
    x_min, x_max = x_pts.min(), x_pts.max()
    total_width = max(1, x_max - x_min)
    total_height = max(1, y_max - y_min)

    # 5. Measure Entry and Exit Centroids
    h_slice = max(1, int(total_height * 0.15))
    top_slice = tape_binary[y_min : y_min + h_slice, :]
    bot_slice = tape_binary[y_max - h_slice : y_max + 1, :]

    _, x_top = np.where(top_slice > 0)
    _, x_bot = np.where(bot_slice > 0)

    if len(x_top) == 0 or len(x_bot) == 0:
        return Direction.STRAIGHT, visual_mask, 0.0

    cx_top = int(np.mean(x_top))
    cx_bot = int(np.mean(x_bot))
    shift = (cx_top - cx_bot) / total_width

    # Draw entry (green) and exit (red) centroid points
    cv2.circle(visual_mask, (cx_top, y_min + h_slice // 2), 6, (0, 0, 255), -1)
    cv2.circle(visual_mask, (cx_bot, y_max - h_slice // 2), 6, (0, 255, 0), -1)

    # 6. Direction & Proximity Gating
    # If a turn is detected, check if the corner (y_min) has crossed the trigger line
    corner_reached = y_min >= action_y

    if shift > shift_threshold:
        signal = Direction.RIGHT if corner_reached else Direction.STRAIGHT
    elif shift < -shift_threshold:
        signal = Direction.LEFT if corner_reached else Direction.STRAIGHT
    else:
        signal = Direction.STRAIGHT

    return signal, visual_mask, shift


"""
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
"""

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




#import cv2
#import numpy as np

# Initialize ORB detector with 1000 keypoints
orb = cv2.ORB_create(
    nfeatures=1000,
    scaleFactor=1.2,
    nlevels=8,
    edgeThreshold=15,
    firstLevel=0,
    WTA_K=2,
    scoreType=cv2.ORB_HARRIS_SCORE,
    patchSize=31,
    fastThreshold=20,
)

# Fast FLANN matcher for binary descriptors (LSH)
FLANN_INDEX_LSH = 6
index_params = dict(
    algorithm=FLANN_INDEX_LSH,
    table_number=6,
    key_size=12,
    multi_probe_level=1,
)
search_params = dict(checks=50)
flann = cv2.FlannBasedMatcher(index_params, search_params)


def match_places_orb(img1_np: np.ndarray, img2_np: np.ndarray) -> bool:
    """Takes two (H, W, 3) BGR/RGB or (H, W) grayscale NumPy arrays."""
    # 1. Convert to grayscale if needed
    g1 = (
        cv2.cvtColor(img1_np, cv2.COLOR_BGR2GRAY)
        if img1_np.ndim == 3
        else img1_np
    )
    g2 = (
        cv2.cvtColor(img2_np, cv2.COLOR_BGR2GRAY)
        if img2_np.ndim == 3
        else img2_np
    )

    # 2. Extract keypoints & descriptors
    kp1, des1 = orb.detectAndCompute(g1, None)
    kp2, des2 = orb.detectAndCompute(g2, None)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        return False

    # 3. Match descriptors using k-NN (k=2 for Lowe's ratio test)
    matches = flann.knnMatch(des1, des2, k=2)

    # 4. Filter matches with Lowe's ratio test
    good_matches = []
    for m_pair in matches:
        if len(m_pair) == 2:
            m, n = m_pair
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

    if len(good_matches) < 8:
        return False

    # 5. Geometric verification (RANSAC Homography for planar angle shifts)
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(
        -1, 1, 2
    )
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(
        -1, 1, 2
    )

    _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 4.0)

    if mask is None:
        return False

    num_inliers = int(np.sum(mask))
    return num_inliers >= 15  # True if same area verified
