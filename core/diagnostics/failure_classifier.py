from typing import Dict, List

class FailureClassifier:
    """
    Categorizes errors logged during beta testing to identify architectural weak points.
    """
    CATEGORIES = [
        "segmentation_failures",
        "tracking_failures",
        "export_failures",
        "cache_failures",
        "user_workflow_issues"
    ]
    
    @staticmethod
    def classify(error_logs: List[str]) -> Dict[str, int]:
        results = {cat: 0 for cat in FailureClassifier.CATEGORIES}
        for log in error_logs:
            log_lower = log.lower()
            if "sam" in log_lower or "mask" in log_lower:
                results["segmentation_failures"] += 1
            elif "flow" in log_lower or "lost" in log_lower:
                results["tracking_failures"] += 1
            elif "write" in log_lower or "composite" in log_lower:
                results["export_failures"] += 1
            elif "corrupt" in log_lower or "load" in log_lower:
                results["cache_failures"] += 1
            else:
                results["user_workflow_issues"] += 1
        return results
