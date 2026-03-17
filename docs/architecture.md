# Agent Architecture

## System Overview

```
┌─────────────────────────────────────────────────┐
│              LangGraph StateGraph                │
│                                                  │
│  ┌──────────┐    ┌──────────┐    ┌───────────┐  │
│  │   LHS    │───▶│   CAD    │───▶│  Meshing  │  │
│  │  Node 0  │    │  Node 1  │    │  Node 2   │  │
│  └──────────┘    └──────────┘    └───────────┘  │
│                                        │         │
│                             ┌──────────▼──────┐  │
│                             │  Q-Ramp CFD     │  │
│                             │    Node 3       │  │
│                             └──────┬──────────┘  │
│                      ┌────────────┴──────────┐   │
│                 ┌────▼────┐           ┌──────▼─┐ │
│                 │  1D Sim │           │ 3D CFD │ │
│                 │  Node4a │           │ Node4b │ │
│                 └────┬────┘           └──────┬─┘ │
│                      └────────────┬──────────┘   │
│                             ┌─────▼───────────┐  │
│                             │  Solid FEM      │  │
│                             │    Node 5       │  │
│                             └──────┬──────────┘  │
│                             ┌──────▼──────────┐  │
│                             │  Post-Process   │  │
│                             │    Node 6       │  │
│                             └──────┬──────────┘  │
│                             ┌──────▼──────────┐  │
│                             │  Sensitivity    │  │
│                             │  Analysis Node7 │  │
│                             └─────────────────┘  │
└─────────────────────────────────────────────────┘
         │ error on any node
         ▼
┌──────────────────┐
│  Error Analyzer  │ ← LLM reads logs, classifies, suggests fix
│  (conditional    │
│   edge + retry)  │
└──────────────────┘
```

---

## SimulationPipelineState

The central state object passed through all graph nodes:

```python
class CaseState(TypedDict):
    case_id: int
    status: str                  # see pipeline_design.md status states
    current_step: int            # 0–7
    params: dict                 # row from parameters.csv
    outputs: dict                # file paths produced so far
    error_log: list[str]         # error messages
    retry_count: int             # per-step retry counter
    quality_metrics: dict        # mesh quality, convergence, etc.

class SimulationPipelineState(TypedDict):
    cases: dict[int, CaseState]  # key: case_id
    active_jobs: dict            # HPC job_id → case_id mapping
    completed_cases: list[int]
    failed_cases: list[int]
    global_step: int             # which pipeline step we're orchestrating
    run_id: str                  # unique run identifier
```

---

## Node Responsibilities

### Orchestrator Node
- Decides which cases to advance to next step
- Batches cases for parallel HPC submission
- Handles WK1/WK2 distribution (cases 0–499 / 500–999)

### CAD Node (Step 1)
- Calls `cad_tool.py` per case
- On success → updates `CaseState.outputs`
- On failure → routes to Error Analyzer

### Mesh Node (Step 2)
- Calls `mesh_tool.py` per case
- Runs `mesh_validator.py` on output
- Retry logic: up to 3 attempts with finer mesh settings

### HPC Submit Node (Steps 3, 4a, 4b, 5)
- SSH into Harvey, write SLURM script, `sbatch`
- Stores `job_id` in `active_jobs`
- Does NOT block — returns immediately

### HPC Monitor Node
- Polls `squeue` for job completion
- On completion: pulls result files via `rsync`
- On failure: routes to Error Analyzer

### Error Analyzer Node
- Reads solver log files
- Uses LLM to classify: `MESH_QUALITY | BC_ERROR | DIVERGENCE | UNKNOWN`
- Proposes fix parameters
- Routes back to failed step (if retries remain) or marks FAILED

### Post-Process Node (Step 6)
- Extracts scalar outputs from VTK/JSON files
- Appends row to `results/FFR.csv` and `results/stress.csv`

### SA Node (Step 7)
- Triggered once all cases reach COMPLETE or FAILED
- Trains GPR on completed cases
- Computes Sobol indices

---

## Conditional Edges

```python
def route_after_mesh(state) -> str:
    if mesh_quality_ok(state):
        return "qramp_node"
    elif state["retry_count"] < 3:
        return "mesh_node"        # retry
    else:
        return "error_analyzer"   # give up

def route_after_hpc(state) -> str:
    if job_succeeded(state):
        return "next_step_node"
    elif state["retry_count"] < 2:
        return "error_analyzer"   # LLM fixes params, resubmit
    else:
        return "mark_failed"
```

---

## Compute Topology (Agent Perspective)

```
Agent (runs locally)
  │
  ├── subprocess / Python-OCC  → CAD generation (local)
  │
  ├── SSH → WK1 / WK2          → gmsh + Simmetrix meshing
  │         (paramiko or fabric)
  │
  └── SSH → Harvey             → SLURM job submission
            ├── sbatch qramp.sh
            ├── sbatch 1d_sim.sh
            ├── sbatch 3d_cfd.sh
            └── sbatch solid.sh
            rsync ← pull results back
```

---

## Error Recovery Matrix

| Step | Failure Type | Recovery Action |
|------|-------------|-----------------|
| CAD | Geometry degeneracy | Adjust param bounds, retry |
| Mesh | Poor quality | Reduce mesh size factor 0.8x, retry |
| Mesh | Total failure | Mark FAILED, skip case |
| CFD | Divergence | Reduce time step / CFL, retry |
| CFD | BC mismatch | LLM re-reads log, adjusts resistance values |
| FEM | No convergence | Reduce load step size, retry |
| Any | HPC node failure | Re-submit to different queue |

---

## Dashboard Layout (Streamlit)

```
┌─────────────────────────────────────────────────────┐
│  Pipeline Progress: ████████░░ 812/1000 cases        │
│                                                      │
│  Step Status:                                        │
│  LHS ✓  CAD ✓  Mesh ✓  CFD ▶  1D/3D ▶  FEM ○  SA ○ │
│                                                      │
│  Case Status Table (filterable):                     │
│  ID  | Status        | Step | Errors                 │
│  042 | COMPLETE      | 7    | —                      │
│  347 | MESH_DONE     | 2    | —                      │
│  512 | FAILED_MESH   | 2    | aspect_ratio=6.2       │
│  800 | QRAMP_RUNNING | 3    | —                      │
│                                                      │
│  SA Results (when available):                        │
│  [Sobol bar chart: X1...Xn → Y1, Y2]                │
└─────────────────────────────────────────────────────┘
```
