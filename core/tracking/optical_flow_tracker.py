import cv2
import numpy as np

class OpticalFlowTracker:
    def __init__(self):
        # Prefer DISOpticalFlow for fast, dense flow
        if hasattr(cv2, 'DISOpticalFlow_create'):
            self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        else:
            self.dis = None

    def track(self, prev_frame: np.ndarray, curr_frame: np.ndarray, prev_mask: np.ndarray) -> tuple[np.ndarray, float]:
        """
        Calculates optical flow and warps the previous mask.
        Returns:
            warped_mask (np.ndarray): The predicted alpha mask.
            confidence (float): A confidence score between 0.0 and 1.0.
        """
        # 1. Convert to grayscale
        if len(prev_frame.shape) == 3:
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        # 2. Calculate optical flow
        if self.dis is not None:
            flow = self.dis.calc(prev_gray, curr_gray, None)
        else:
            flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 
                                                0.5, 3, 15, 3, 5, 1.2, 0)
                                                
        print(f"[DEBUG-FLOW] prev_gray: {prev_gray.shape}, curr_gray: {curr_gray.shape}, prev_mask: {prev_mask.shape}, flow: {flow.shape}")
        else:
            curr_gray = curr_frame

        # 2. Calculate optical flow
        if self.dis is not None:
            flow = self.dis.calc(prev_gray, curr_gray, None)
        else:
            flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 
                                                0.5, 3, 15, 3, 5, 1.2, 0)

        # 3. Warp previous alpha mask using the flow field
        h, w = prev_mask.shape[:2]
        
        # Create map for remap
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        
        # Backward mapping for remap
        map_x = x - flow[..., 0]
        map_y = y - flow[..., 1]
        
        warped_mask = cv2.remap(prev_mask, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        
        # Binarize mask
        warped_mask = (warped_mask > 127).astype(np.uint8) * 255

        # 5. Calculate confidence
        prev_area = np.count_nonzero(prev_mask)
        curr_area = np.count_nonzero(warped_mask)
        
        if prev_area == 0:
        confidence = (area_ratio * 0.3) + (flow_consistency * 0.7)
        
        # Penalize drastically changing masks
        if area_ratio < 0.3:
            confidence *= 0.5
        # Flow magnitude consistency inside mask
        mask_flow = flow[prev_mask > 0]
        if len(mask_flow) > 0:
            magnitudes = np.linalg.norm(mask_flow, axis=1)
            mean_mag = np.mean(magnitudes)
            std_mag = np.std(magnitudes)
            # High standard deviation relative to mean indicates incoherent flow
            # Add a stable denominator base (e.g., 2.0 pixels) so noise on static objects doesn't zero out confidence
            flow_consistency = max(0.0, 1.0 - (std_mag / (mean_mag + 2.0)))
        else:

        confidence = (area_ratio * 0.5) + (flow_consistency * 0.5)
        
        # Penalize drastically changing masks
        if area_ratio < 0.5:
            confidence *= 0.5

        return warped_mask, confidence
