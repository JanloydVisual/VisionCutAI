
    def clamp_y(self, y: float) -> int:
        return max(0, min(int(y), self.height - 1))

from typing import Tuple, List

class RefinementHintType(Enum):
    ADD_NEGATIVE = "ADD_NEGATIVE"
    ADD_POSITIVE = "ADD_POSITIVE"

@dataclass
class RefinementHint:
    position: Tuple[int, int]
    hint_type: RefinementHintType
    confidence: float
    reason: str

@dataclass
class EvaluationResult:
    grade: QualityGrade
    hints: List[RefinementHint]

@dataclass
class EvaluationResult:
    grade: QualityGrade
    hints: List[RefinementHint]
    metrics: dict
