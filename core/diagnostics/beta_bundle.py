import os
import zipfile
from typing import List

class BetaBundleGenerator:
    """
    Collects telemetry, crash logs, and session reports into a single ZIP 
    for beta testers to submit back to the developers.
    """
    def __init__(self, output_zip: str = "VisionCut_Beta_Diagnostic.zip"):
        self.output_zip = output_zip
        
    def generate_bundle(self, files_to_include: List[str]) -> str:
        with zipfile.ZipFile(self.output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files_to_include:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
        return self.output_zip
