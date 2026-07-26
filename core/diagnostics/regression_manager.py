from typing import List, Dict

class RegressionManager:
    """
    Stores beta failure scenarios and links them to test cases to prevent regressions.
    """
    def __init__(self):
        self.regression_cases: List[Dict[str, str]] = []
        
    def add_case(self, description: str, benchmark_id: str):
        self.regression_cases.append({
            "description": description,
            "benchmark_link": benchmark_id,
            "status": "pending"
        })
        
    def verify_all(self) -> bool:
        # Mock logic
        return True
