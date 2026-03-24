"""
state.py
SimulationPipelineState — 7단계 파이프라인 전체 상태 정의

파이프라인 구조:
  Step 0: LHS         → parameters.csv
  Step 1: CAD         → lumen.stp, fc.stp, solid.stp, lipid.stp
  Step 2: Mesh        → fluid.vtu, solid.msh
  Step 3: Q-Ramp      → slab/, Flow_hist/
  Step 4a: 1D Fluid   → _1D.json (P, Q, FFR)
  Step 4b: 3D Fluid   → wall_peak.csv, wall_low.csv
  Step 5: Solid       → FC peak/low .vtu
  Step 6: Post        → FFR.csv, stress.csv (PSS, ΔPSS)
  Step 7: SA          → Sobol indices
"""

from typing import TypedDict, Annotated, Literal
import operator

#Define states, Step name, Step status


# Class stepOutputs
class StateOutput(TypedDict):
    
    #Step 0: LHS
    paramaeter_csv: str

    #Step1: CAD
    lumen_stp: str
    fc_stp: str
    solid_stp: str
    lipid_stp: str

    #Step2: Mesh
    fluid_vtu: str
    solid_msh: str

    #Step3: Q-Ramp
    slab: str
    Flow_hist: str

    #Step4a: 1D Fluid
    _1D_json: str

    #Step4b: 3D Fluid
    wall_peak_csv: str
    wall_low_csv: str

    #Step5: Solid
    fc_peak_vtu: str
    fc_low_vtu: str

    #Step6: Post
    FFR_csv: str
    stress_csv: str

    #Step7: SA
    sobol_indices_json: str


StepName = Literal['LHS', 'CAD', 'Mesh', 'Q-Ramp', '1D Fluid', '3D Fluid', 'Solid', 'Post', 'SA']
StepStatus = Literal['running', 'done', 'failed', 'pending']


# Main state
# SimulationPipelineState

class SimulationPipelineState(TypedDict):

    '''
    tell me what we need while simulation

    - case id
    - where are u at (current step)
    - step's status (running, done, failed)
    - error log
    - retry counts
    - output path
    - where are u runnginat (local, wk1, wk2, harvey)
    '''

    case_id: str

    StepName = Literal['LHS', 'CAD', 'Mesh', 'Q-Ramp', '1D Fluid', '3D Fluid', 'Solid', 'Post', 'SA']
    current_step: StepName


    StepStatus = Literal['running', 'done', 'failed', 'pending']
    step_status: dict[StepName, StepStatus]

    error_log: Annotated[list[str], operator.add]

    outputs: StateOutput

    # retry counts
    retry_count: dict[StepName, int]

    #meta data
    case_params: dict
    run_on: str # local, wk1, wk2, harvey


#Make inital state helper (inital state on the local for the LHS)
def make_inital_state(case_id: str, case_params:dict, run_on: str = "local") -> SimulationPipelineState:
    '''
    create intital state
    all state satringn as pending
    return the state
    '''

    return SimulationPipelineState(
        case_id=case_id,
        current_step='LHS',
        step_status={
            'LHS': 'pending',
            'CAD': 'pending',
            'Mesh': 'pending',
            'Q-Ramp': 'pending',
            '1D Fluid': 'pending',
            '3D Fluid': 'pending',
            'Solid': 'pending',
            'Post': 'pending',
            'SA': 'pending',
        },
        error_log=[],
        outputs={},
        retry_count={},
        case_params=case_params,
        run_on=run_on,
    )

def get_step_status(state: SimulationPipelineState, step: StepName) -> StepStatus:
    '''
    get the status of the step
    '''
    return state['step_status'][step]

def set_step_status(state: SimulationPipelineState, step: StepName, status: StepStatus):
    '''
    set the status of the step
    '''
    state['step_status'][step] = status