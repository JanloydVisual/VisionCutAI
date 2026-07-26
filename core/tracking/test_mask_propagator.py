import unittest
import numpy as np
from core.tracking.mask_propagator import MaskPropagator

class TestMaskPropagator(unittest.TestCase):
    
    def setUp(self):
        self.frame_shape = (100, 100) # (h, w)
        self.mask = np.zeros(self.frame_shape, dtype=np.uint8)
        
    def test_same_bbox_produces_identical_mask(self):
        # Create a simple mask
        self.mask[20:40, 20:40] = 255
        bbox = (20, 20, 20, 20)
        
        result = MaskPropagator.propagate(self.mask, bbox, bbox, self.frame_shape)
        
        # Result should be exactly the same
        self.assertTrue(np.array_equal(self.mask, result))
        
    def test_moving_bbox_moves_mask(self):
        self.mask[20:40, 20:40] = 255
        prev_bbox = (20, 20, 20, 20)
        curr_bbox = (50, 50, 20, 20) # moved 30px down and right
        
        result = MaskPropagator.propagate(self.mask, prev_bbox, curr_bbox, self.frame_shape)
        
        expected = np.zeros(self.frame_shape, dtype=np.uint8)
        expected[50:70, 50:70] = 255
        
        self.assertTrue(np.array_equal(expected, result))
        
    def test_scaling_bbox_scales_mask(self):
        self.mask[20:40, 20:40] = 255
        prev_bbox = (20, 20, 20, 20)
        curr_bbox = (50, 50, 40, 40) # scaled 2x
        
        result = MaskPropagator.propagate(self.mask, prev_bbox, curr_bbox, self.frame_shape)
        
        expected = np.zeros(self.frame_shape, dtype=np.uint8)
        expected[50:90, 50:90] = 255
        
        self.assertTrue(np.array_equal(expected, result))
        
    def test_invalid_bbox_does_not_crash(self):
        self.mask[20:40, 20:40] = 255
        prev_bbox = (20, 20, 20, 20)
        
        # Test negative size
        curr_bbox = (50, 50, -10, 20)
        result = MaskPropagator.propagate(self.mask, prev_bbox, curr_bbox, self.frame_shape)
        self.assertEqual(np.sum(result), 0)
        
        # Test out of bounds
        curr_bbox = (200, 200, 20, 20)
        result = MaskPropagator.propagate(self.mask, prev_bbox, curr_bbox, self.frame_shape)
        self.assertEqual(np.sum(result), 0)
        
        # Test None
        result = MaskPropagator.propagate(self.mask, prev_bbox, None, self.frame_shape)
        self.assertEqual(np.sum(result), 0)

if __name__ == '__main__':
    unittest.main()
