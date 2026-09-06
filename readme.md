# Plaque Sensitivity Analysis — Research Code and Automation Prototype

Computational biomechanics code for a KAIST master's thesis on **plaque rupture risk and sensitivity to morphology and hemodynamic parameters**. This repository brings together the historical research scripts from `Sensitivity_Analysis` and a later LangGraph prototype for orchestrating the simulation workflow.

## What is available

| Component | Contents | Current status |
|-----------|----------|----------------|
| [`legacy/research_scripts/`](legacy/research_scripts/) | 11 Python research scripts and 4 pulsatile solver input files | Recovered historical source; requires the original software environment and external model/data inputs. |
| [`src/`](src/) | LangGraph state model, pipeline graph, and interfaces for simulation tools | Mock orchestration prototype; it is not connected to the historical scripts. |
| [`docs/`](docs/) | Pipeline and agent architecture specifications | Design documents describing intended capabilities, including work that is not implemented. |

The prototype updates case status through placeholder nodes. It does **not** generate geometry, run CFD/FEM, calculate sensitivity indices, or demonstrate completed 1,000-case simulations. The tool adapters, mesh validator, LLM error analyzer, and dashboard raise `NotImplementedError`. Automatic recovery, real HPC submission, and live monitoring remain planned work.

## Historical research code

The source in `legacy/research_scripts/` covers these parts of the research workflow:

| Files | Purpose |
|-------|---------|
| `main_CAD.py`, `utils_CAD.py` | Vessel/plaque geometry parameters and CAD helper functions. |
| `sub_gmshing.py`, `utils_gmsh.py` | Gmsh meshing and mesh utilities. |
| `Voronoi_tesselation_KDTREE.py` | Spatial assignment for calcification modeling using a KD-tree. |
| `utils_bc.py` | Interpolate wall data and apply traction boundary conditions. |
| `pymapdl_simulation.py`, `utils_prep.py` | ANSYS MAPDL structural simulation setup and execution. |
| `utils_post.py`, `vtp_modify.py`, `check.py` | Stress/result processing, wall-data extraction, and data checks. |
| `pulsatile/` | `model.svpre`, `solver.inp`, `rcrt.dat`, and `pressbct.dat` solver input files. |

These files were recovered from [`Sensitivity_Analysis` commit `3c9fb6f`](https://github.com/Sehyeogkim/Sensitivity_Analysis/tree/3c9fb6f761fc7cb6677051740625c3eb2fc336dd), before that repository's file-deletion commit. This consolidation preserves source files, not a complete reproducible dataset: generated meshes, wall-result tables, caches, and `node_modules` are excluded. The original repository history retains the original snapshot.

Historical scripts contain machine-specific paths such as `/home/jeff/project/...` and expect parameter CSVs, geometry, meshes, and wall data from the research environment. Some helpers also remove generated files. Review their paths and entry points before running them against your own data.

Dependencies vary by script and include NumPy, pandas, SciPy, Gmsh, meshio, PyVista, `ansys-mapdl-core`, and `ansys-mapdl-reader`. Structural simulations require an installed and licensed ANSYS MAPDL environment; the pulsatile input files require the corresponding SimVascular solver environment and referenced model files. The root `pyproject.toml` describes the automation prototype and is not a complete environment specification for this historical code. End-to-end scientific reproducibility has not been verified as part of consolidation.

## Intended automation workflow

```text
LHS sampling → CAD → meshing → Q-ramp CFD → 1D / 3D flow simulation
            → solid FEM → post-processing → sensitivity analysis
```

The design targets local/workstation/HPC coordination, GPR surrogate modeling with Sobol analysis, and an agent-assisted recovery workflow. The current graph runs its 1D and 3D placeholder nodes sequentially; the diagram does not imply implemented parallel solver execution.

Read the [pipeline specification](docs/pipeline_design.md) for the intended simulation steps and the [architecture document](docs/architecture.md) for state and orchestration design. [`CLAUDE.md`](CLAUDE.md) contains the original agent development briefing.

## Run the mock state-transition demo

The demo requires Python 3.11+ and LangGraph. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'langgraph>=0.2'
python -m src.pipeline_graph --mock --cases 10
```

This exercises placeholder state transitions only. A printed completed-case count is a mock result, not evidence of simulations or validated scientific outputs. No HPC access, solver installation, or API credentials are used by this demo. The current entry point provides no real-simulation mode; omitting `--mock` still uses the mock nodes.

## Repository layout

```text
legacy/research_scripts/  Historical research code and pulsatile inputs
src/state.py             Case and pipeline state definitions
src/pipeline_graph.py    Mock LangGraph pipeline and demo entry point
src/tools/               Unimplemented CAD, mesh, HPC, post-processing and SA adapters
src/validators/          Unimplemented mesh validation
src/agents/              Unimplemented LLM error analysis
src/dashboard.py         Unimplemented Streamlit dashboard
pipeline/                Earlier experimental pipeline code
docs/                    Pipeline and architecture design documents
```
