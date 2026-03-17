"""
LLM-based Error Analyzer
Reads solver logs, classifies failure type, proposes recovery action.

Week 3 implementation.
"""

# Failure categories
class FailureType:
    MESH_QUALITY = "MESH_QUALITY"
    BC_ERROR = "BC_ERROR"
    DIVERGENCE = "DIVERGENCE"
    HPC_NODE_FAILURE = "HPC_NODE_FAILURE"
    UNKNOWN = "UNKNOWN"


def analyze_error(log_text: str, step: int) -> dict:
    """
    Use Claude API to analyze a solver log and classify the failure.

    Returns:
        {
            "failure_type": str,        # FailureType constant
            "cause": str,               # human-readable diagnosis
            "suggested_fix": dict,      # parameter adjustments to apply
            "retry": bool               # whether to retry
        }

    TODO Week 3:
        - Call Claude API with log_text + step context
        - Parse structured response
        - Map to suggested parameter changes
    """
    raise NotImplementedError("Week 3: implement LLM-based error analysis")
