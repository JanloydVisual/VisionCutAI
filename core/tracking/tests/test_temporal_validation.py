import pytest
import numpy as np
from core.ai.anchor_manager import AnchorManager, AnchorState, QualityGrade
from core.tracking.mask_propagator import MaskPropagator
from core.tracking.temporal_metrics import TemporalMetricsCollector
from core.tracking_engine import TrackingEngine
from core.ai.object_tracker import TrackedFrameState
from core.tracking.tracking_confidence import TrackingConfidenceResult

def test_anchor_creation():
    manager = AnchorManager()
    mask = np.zeros((100, 100), dtype=np.uint8)
    anchor = AnchorState(
        frame_number=10,
        mask=mask,
        bounding_box=(10, 10, 20, 20),
        positive_points=[],
        negative_points=[],
        quality_grade=QualityGrade.GOOD
    )
    manager.add_anchor(anchor)
    assert manager.get_nearest_anchor(12).frame_number == 10

def test_mask_propagation_dimensions():
    prev_mask = np.zeros((100, 100), dtype=np.uint8)
    prev_mask[10:30, 10:30] = 255
    prev_bbox = (10, 10, 20, 20)
    curr_bbox = (15, 15, 20, 20)
    
    new_mask = MaskPropagator.propagate(prev_mask, prev_bbox, curr_bbox, (100, 100, 3))
    assert new_mask.shape == (100, 100)
    assert new_mask[15, 15] == 255

def test_iou_calculation():
    metrics = TemporalMetricsCollector()
    mask1 = np.zeros((10, 10), dtype=np.uint8)
    mask1[0:5, 0:5] = 1
    mask2 = np.zeros((10, 10), dtype=np.uint8)
    mask2[0:5, 0:5] = 1
    
    metrics.record_propagation(mask1, mask2, 10.0, frame_index=1, prev_bbox=(0,0,5,5), curr_bbox=(0,0,5,5))
    assert metrics.get_average_stability_iou() == 1.0
    
    mask3 = np.zeros((10, 10), dtype=np.uint8) # empty, union is 0? wait, prev mask2 union mask3 is 25
    metrics.record_propagation(mask2, mask3, 10.0, frame_index=2, prev_bbox=(0,0,5,5), curr_bbox=(0,0,5,5))
    assert metrics.get_average_stability_iou() == 0.5 # 1.0 + 0.0 / 2

class DummyVideoEngine:
    def get_frame(self, i):
        return np.zeros((100, 100, 3), dtype=np.uint8)

class DummyObjectTracker:
    def __init__(self):
        self.tracker_name = "Dummy"
    def get_state(self):
        return TrackedFrameState(0, (10, 10, 20, 20), [], [], 1.0)
    def update(self, frame, frame_number):
        return None # Simulates tracker failure

def test_failure_pause_signal():
    engine = TrackingEngine(DummyVideoEngine(), DummyObjectTracker())
    engine.start_frame = 0
    engine.end_frame = 10
    
    paused_called = False
    def on_paused(frame_num, conf):
        nonlocal paused_called
        paused_called = True
        
    engine.tracking_paused.connect(on_paused)
    
    engine._is_running = True
    engine.run() # Run synchronously for test
    
    assert paused_called
