import json
from typing import Dict, Any, List
from core.diagnostics.issue_prioritizer import IssuePrioritizer

class ImprovementReportGenerator:
    """
    Translates beta issues into actionable engineering reports.
    """
    def __init__(self, output_path: str = "VisionCut_Improvement_Report.json"):
        self.output_path = output_path
        
    def generate(self, analytics_data: Dict[str, Any]) -> str:
        ranked_issues = IssuePrioritizer.rank_issues(analytics_data)
        
        report = {
            "top_problems": [],
            "affected_workflows": ["Talking Head", "Real Estate"],
            "suggested_engineering_areas": []
        }
        
        for issue in ranked_issues:
            problem = {
                "issue": issue["issue"],
                "frequency": issue["frequency"]
            }
            report["top_problems"].append(problem)
            report["suggested_engineering_areas"].append(f"Investigate {issue['issue']} pipeline module.")
            
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)
            
        return self.output_path
