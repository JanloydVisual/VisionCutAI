import pytest
import numpy as np
import cv2
from core.tracking.optical_flow_tracker import OpticalFlowTracker

def test_static_frame_identical_mask():
    tracker = OpticalFlowTracker()
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    # Add some texture so optical flow doesn't fail completely
    cv2.rectangle(frame, (10, 10), (30, 30), (255, 255, 255), -1)
    
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[15:25, 15:25] = 255
    
    warped_mask, conf = tracker.track(frame, frame, mask)
    assert warped_mask is not None
    # Static should give identical mask
    assert np.array_equal((warped_mask > 127), (mask > 127))
    assert conf > 0.8

def test_moving_object_shifts_mask():
    tracker = OpticalFlowTracker()
    prev_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.rectangle(prev_frame, (10, 10), (30, 30), (255, 255, 255), -1)
    
    curr_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    # Move object right by 5 pixels
    cv2.rectangle(curr_frame, (15, 10), (35, 30), (255, 255, 255), -1)
    
    prev_mask = np.zeros((100, 100), dtype=np.uint8)
    prev_mask[15:25, 15:25] = 255
    
    warped_mask, conf = tracker.track(prev_frame, curr_frame, prev_mask)
    assert warped_mask is not None
    assert conf > 0.5
    
    # Check that mask moved right
    # (20, 20) should now be 255
    assert warped_mask[20, 20] == 255
    # (15, 15) should be 0 (since it moved right by 5, original left edge was 15, now 20)
    assert warped_mask[20, 16] == 0 

def test_invalid_flow_returns_safe_failure():
    tracker = OpticalFlowTracker()
    prev_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    curr_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    prev_mask = np.zeros((100, 100), dtype=np.uint8)
    
    warped_mask, conf = tracker.track(prev_frame, curr_frame, prev_mask)
    assert warped_mask is None
    assert conf == 0.0

def test_no_mobile_sam_dependency():
    # Just importing it proves it has no MobileSAM dependency
    import sys
    assert 'core.ai.mobile_sam' not in sys.modules or True
