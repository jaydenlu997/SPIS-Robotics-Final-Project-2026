import cv2
import numpy as np
import sys
from Camera import get_available_paths

def test_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to load {image_path}")
        return
    paths, mask, shift = get_available_paths(img)
    print(f"Paths for {image_path}: {[p.name for p in paths]}")
    cv2.imwrite(f"debug_{image_path.split('/')[-1]}", mask)

test_image("/Users/andrewtrinh/.gemini/antigravity/brain/901f75bb-77f5-4382-a801-7889162a3208/.user_uploaded/media_1788215735314.jpg")
test_image("/Users/andrewtrinh/.gemini/antigravity/brain/901f75bb-77f5-4382-a801-7889162a3208/.user_uploaded/media_1788215747628.jpg")

