from abc import ABC, abstractmethod

class SegmentationModelAdapter(ABC):
    """
    Sprint P5: Common interface for evaluating different segmentation models.
    """
    @abstractmethod
    def segment(self, frame, prompt):
        pass

class MobileSAMAdapter(SegmentationModelAdapter):
    def __init__(self, processor):
        self.processor = processor

    def segment(self, frame, prompt):
        # Ensure the underlying processor is using MobileSAM
        self.processor.set_model("sam")
        rgbas = self.processor.process(frame, custom_prompt=prompt, quality_override="Best")
        return rgbas

class SAMViTBAdapter(SegmentationModelAdapter):
    def __init__(self, processor):
        self.processor = processor

    def segment(self, frame, prompt):
        # Ensure the underlying processor is using SAM ViT-B
        self.processor.set_model("sam_base")
        rgbas = self.processor.process(frame, custom_prompt=prompt, quality_override="Best")
        return rgbas
