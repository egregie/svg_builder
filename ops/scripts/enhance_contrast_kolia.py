import os
import cv2
import numpy as np

def main():
    original_path = 'input/kolia_01.jpg'
    backup_path = 'input/kolia_01_original.jpg'
    
    # 1. Backup original
    if not os.path.exists(backup_path):
        import shutil
        shutil.copy2(original_path, backup_path)
        print(f"Backed up original image to {backup_path}")
        
    # Read backup image to process
    img = cv2.imread(backup_path)
    if img is None:
        print(f"Error: Could not read {backup_path}")
        return
        
    # 2. Convert to LAB color space
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    # 3. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # clipLimit=4.0 and tileGridSize=(8,8) to bring out subtle details of the glass outline
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    
    # 4. Merge channels back
    enhanced_lab = cv2.merge((cl, a, b))
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    # 5. Overwrite the main input file
    cv2.imwrite(original_path, enhanced_bgr)
    print(f"Successfully enhanced contrast and saved to {original_path}")

if __name__ == "__main__":
    main()
