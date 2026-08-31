
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


def RunPICamera_intersection(camera, show_preview: bool = ENABLE_VISUAL_PREVIEW) -> tuple[np.ndarray, list[Direction], float]:
    # Grab a frame
    img = camera.capture_array()

    paths, mask, shift = get_available_paths(img)

    if len(paths) > 1:
        import time
        if not os.path.exists("debug_image"):
            os.makedirs("debug_image")
        
        # Convert camera array (RGB) to OpenCV format (BGR) for saving
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if img.ndim == 3 else img
        
        # Stack the original image and the algorithm mask side-by-side
        combined = np.hstack((img_bgr, mask))
        filename = f"debug_image/debug_{int(time.time()*100)}.jpg"
        cv2.imwrite(filename, combined)
        print(f"Saved debug image to {filename}")

    if show_preview:
        try:
            cv2.imshow("Camera", img)
            cv2.imshow("Modified frame", mask)
            cv2.waitKey(1)
        except Exception:
            pass

    return img, paths, shift


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

    # 5. Calculate Center of Mass for Proportional Shift
    M = cv2.moments(largest_contour)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
    else:
        cx = w_img // 2
        cy = h_img // 2
    
    # Shift is strictly based on how far the center of the tape is from the center of the screen.
    # This naturally centers the robot on the tape and fixes physical veering!
    shift = (cx - (w_img / 2)) / (w_img / 2)  # Range [-1.0, 1.0]

    # Draw centroid
    cv2.circle(visual_mask, (cx, cy), 8, (255, 0, 255), -1)

    # 6. Detect Corners
    h_slice = max(1, int(total_height * 0.25))
    top_slice = tape_binary[y_min : y_min + h_slice, :]
    bot_slice = tape_binary[y_max - h_slice : y_max + 1, :]

    _, x_top = np.where(top_slice > 0)
    _, x_bot = np.where(bot_slice > 0)

    if len(x_top) == 0 or len(x_bot) == 0:
        return Direction.STRAIGHT, visual_mask, shift

    width_top = x_top.max() - x_top.min()
    width_bot = x_bot.max() - x_bot.min()

    cx_top = int(np.mean(x_top))
    cx_bot = int(np.mean(x_bot))

    cv2.circle(visual_mask, (cx_top, y_min + h_slice // 2), 6, (0, 0, 255), -1)
    cv2.circle(visual_mask, (cx_bot, y_max - h_slice // 2), 6, (0, 255, 0), -1)

    # A turn is characterized by a wide horizontal segment at the top 
    # compared to the vertical segment at the bottom.
    is_corner = width_top > (width_bot * 1.15) and width_top > (w_img * 0.05)

    # If a turn is detected, check if the corner (y_min) has crossed the trigger line
    action_y = int(h_img * action_zone_ratio)
    corner_reached = y_min >= action_y

    signal = Direction.STRAIGHT
    if is_corner and corner_reached:
        # Which way does the wide top segment extend relative to the bottom stem?
        if cx_top > cx_bot + (w_img * 0.02):
            signal = Direction.RIGHT
        elif cx_top < cx_bot - (w_img * 0.02):
            signal = Direction.LEFT

    return signal, visual_mask, shift


def get_available_paths(
    image: np.ndarray,
    lower_blue: np.ndarray = np.array([95, 80, 50]),
    upper_blue: np.ndarray = np.array([135, 255, 255]),
    action_zone_ratio: float = 0.35,
) -> tuple[list[Direction], np.ndarray, float]:
    """
    Evaluates blue painter's tape for complex intersections (3-way, 4-way, corners).
    Uses Grid Zone Probing to sample regions around the intersection center.
    Returns a list of all available paths, a visual mask, and the shift for line-following.
    """
    h_img, w_img = image.shape[:2]
    visual_mask = np.zeros((h_img, w_img, 3), dtype=np.uint8)
    
    # 1. Isolate Blue Tape
    if image.ndim == 3 and image.shape[2] == 4:
        image = image[:, :, :3]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV) if image.ndim == 3 else image
    tape_mask = cv2.inRange(hsv, lower_blue, upper_blue)

    # 2. Extract largest contour
    contours, _ = cv2.findContours(tape_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return [Direction.NO_DETECTED], visual_mask, 0.0

    largest_contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest_contour) < 500:
        return [Direction.NO_DETECTED], visual_mask, 0.0

    tape_binary = np.zeros_like(tape_mask)
    cv2.drawContours(tape_binary, [largest_contour], -1, 255, thickness=cv2.FILLED)
    visual_mask[tape_binary > 0] = [255, 120, 0]

    # 3. Calculate basic shift (center of mass)
    M = cv2.moments(largest_contour)
    if M["m00"] != 0:
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
    else:
        cx, cy = w_img // 2, h_img // 2
    shift = (cx - (w_img / 2)) / (w_img / 2)
    cv2.circle(visual_mask, (cx, cy), 8, (255, 0, 255), -1)

    # 4. Find stem (entry point at the bottom)
    y_pts, x_pts = np.where(tape_binary > 0)
    y_max = y_pts.max()
    bot_slice = tape_binary[max(0, y_max - 20) : y_max + 1, :]
    _, x_bot = np.where(bot_slice > 0)
    if len(x_bot) > 0:
        stem_cx = int(np.mean(x_bot))
        stem_width = x_bot.max() - x_bot.min()
    else:
        stem_cx = cx
        stem_width = 40
        
    # Prevent stem_width from being extremely small or large to keep probe boxes sane
    stem_width = max(20, min(stem_width, w_img // 4))

    # 5. Find the junction Y-level
    row_widths = np.sum(tape_binary > 0, axis=1)
    junction_y = int(np.argmax(row_widths))
    
    # 6. Grid-based Zone Probing
    paths = []
    box_size = int(stem_width * 1.5)
    
    def check_zone(center_x, center_y, color):
        x1 = max(0, center_x - box_size // 2)
        x2 = min(w_img, center_x + box_size // 2)
        y1 = max(0, center_y - box_size // 2)
        y2 = min(h_img, center_y + box_size // 2)
        
        cv2.rectangle(visual_mask, (x1, y1), (x2, y2), color, 2)
        
        if x1 >= x2 or y1 >= y2:
            return False
            
        zone = tape_binary[y1:y2, x1:x2]
        blue_pixels = np.sum(zone > 0)
        total_pixels = (x2 - x1) * (y2 - y1)
        
        # If the zone is at least 15% blue tape, the path exists
        return (blue_pixels / total_pixels) > 0.15

    max_width = row_widths.max()
    has_crossbar = max_width > (stem_width * 1.5)
    action_y = int(h_img * action_zone_ratio)
    
    cv2.line(visual_mask, (0, action_y), (w_img, action_y), (255, 255, 0), 1)
    
    if has_crossbar and junction_y >= action_y:
        # Probe LEFT (Green box)
        left_px = stem_cx - int(stem_width * 1.5)
        if check_zone(left_px, junction_y, (0, 255, 0)):
            paths.append(Direction.LEFT)
            
        # Probe RIGHT (Red box)
        right_px = stem_cx + int(stem_width * 1.5)
        if check_zone(right_px, junction_y, (0, 0, 255)):
            paths.append(Direction.RIGHT)
            
        # Probe STRAIGHT (Cyan box)
        top_py = junction_y - int(stem_width * 1.5)
        if check_zone(stem_cx, top_py, (255, 255, 0)):
            paths.append(Direction.STRAIGHT)
            
        cv2.line(visual_mask, (0, junction_y), (w_img, junction_y), (255, 255, 255), 1)
    else:
        # No intersection detected, just follow the line
        paths.append(Direction.STRAIGHT)
        
    if not paths:
        paths.append(Direction.STRAIGHT)
        
    return paths, visual_mask, shift


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
