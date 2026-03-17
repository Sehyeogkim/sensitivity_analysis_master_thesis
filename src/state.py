"""
SimulationPipelineState — central state for LangGraph pipeline.

All nodes read from and write to this state.
See docs/architecture.md for full state design.
"""

from typing import TypedDict, Optional


# Case status progression (see docs/pipeline_design.md)
class CaseStatus:
    PENDING = "PENDING"
    CAD_RUNNING = "CAD_RUNNING"
    CAD_DONE = "CAD_DONE"
    MESHING = "MESHING"
    MESH_DONE = "MESH_DONE"
    QRAMP_RUNNING = "QRAMP_RUNNING"
    QRAMP_DONE = "QRAMP_DONE"
    SIM_4A_RUNNING = "SIM_4A_RUNNING"
    SIM_4B_RUNNING = "SIM_4B_RUNNING"
    SIM_4_DONE = "SIM_4_DONE"
    SOLID_RUNNING = "SOLID_RUNNING"
    SOLID_DONE = "SOLID_DONE"
    POSTPROCESS = "POSTPROCESS"
    COMPLETE = "COMPLETE"
    # Failure states
    FAILED_CAD = "FAILED_CAD"
    FAILED_MESH = "FAILED_MESH"
    FAILED_QRAMP = "FAILED_QRAMP"
    FAILED_4A = "FAILED_4A"
    FAILED_4B = "FAILED_4B"
    FAILED_SOLID = "FAILED_SOLID"
    FAILED_POST = "FAILED_POST"
    RETRYING = "RETRYING"


class CaseState(TypedDict):
    case_id: int
    status: str                      # CaseStatus constant
    current_step: int                # 0–7
    params: dict                     # row from parameters.csv
    outputs: dict                    # step -> file paths produced
    error_log: list[str]             # error messages per failure
    retry_count: int                 # retries for current step
    quality_metrics: dict            # mesh quality, convergence metrics
    hpc_job_id: Optional[str]        # current SLURM job ID if running on Harvey
    assigned_workstation: Optional[str]  # "wk1" or "wk2" for meshing


class SimulationPipelineState(TypedDict):
    cases: dict                      # int -> CaseState
    active_jobs: dict                # hpc_job_id -> case_id
    completed_cases: list[int]
    failed_cases: list[int]
    global_step: int                 # pipeline step currently being orchestrated
    run_id: str                      # unique identifier for this run
    mock_mode: bool                  # if True, skip real HPC calls


def make_initial_state(parameters: list[dict], run_id: str, mock_mode: bool = False) -> SimulationPipelineState:
    """Create initial pipeline state from list of parameter dicts."""
    cases = {}
    for row in parameters:
        case_id = int(row["case_id"])
        cases[case_id] = CaseState(
            case_id=case_id,
            status=CaseStatus.PENDING,
            current_step=0,
            params=row,
            outputs={},
            error_log=[],
            retry_count=0,
            quality_metrics={},
            hpc_job_id=None,
            assigned_workstation="wk1" if case_id < 500 else "wk2",
        )
    return SimulationPipelineState(
        cases=cases,
        active_jobs={},
        completed_cases=[],
        failed_cases=[],
        global_step=0,
        run_id=run_id,
        mock_mode=mock_mode,
    )
