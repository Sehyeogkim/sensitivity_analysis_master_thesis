# CLAUDE.md — Agent Briefing for LangGraph CAE Pipeline Agent

This file is auto-loaded by Claude CLI. Read this before doing anything in this repo.

---

## Project Summary

Build a **LangGraph-based agentic system** that automates a 7-step Computational Fluid/Solid Mechanics (CAE) pipeline for **Plaque Sensitivity Analysis** — running 1000 parameter cases through CAD generation, meshing, HPC simulation, post-processing, and sensitivity analysis.

**Timeline**: 2026.03.17 ~ 2026.04.13 (4 weeks)
**Owner**: Jeff (PhD researcher, cardiovascular biomechanics)

---

## Compute Topology

```
Local (Windows)          WK1 / WK2 (Linux workstations)      Harvey (HPC cluster, SLURM)
─────────────────        ──────────────────────────────       ───────────────────────────
Step 0: LHS sampling     Step 2: gmsh meshing (solid)         Step 3: Q-Ramp CFD (Harvey)
Step 1: CAD (Inventor)   Step 2: Simmetrix mesh (fluid)       Step 4a: 1D Tree Solver
                         Step 4b: SimVascular CFD             Step 5: ANSYS pymapdl FEM
                                                              (all via SSH + SLURM submit)
Step 6: Post-processing  ← pull results back locally
Step 7: SA (GPR + Sobol) ← runs locally
```

**Case distribution**: Cases 0–499 → WK1, Cases 500–999 → WK2
**HPC access**: SSH into Harvey, submit via `sbatch`, monitor via `squeue`

---

## The 7-Step Pipeline (File I/O)

```
Step 0: LHS Sampling
  IN:  param_ranges.json (morphology + hemodynamic bounds)
  OUT: parameters.csv  (1000 rows × N parameters)

Step 1: CAD Generation  [Local, Autodesk Inventor iLogic / Python-OCC]
  IN:  parameters.csv (one row per case)
  OUT: cases/{case_id}/lumen.stp, fc.stp, solid.stp, lipid.stp

Step 2: Meshing  [WK1/WK2, gmsh + Simmetrix]
  IN:  solid.stp, lumen.stp
  OUT: cases/{case_id}/fluid.vtu, solid.msh
  QUALITY: aspect_ratio < 5, skewness < 0.85

Step 3: Q-Ramp Fluid Simulation  [Harvey, SimVascular/svSolver]
  IN:  fluid.vtu, inlet Q-ramp waveform
  OUT: cases/{case_id}/slab/, Flow_hist/

Step 4a: 1D Pulsatile Simulation  [Harvey, Tree Solver + WK2 BC]
  IN:  Flow_hist/, Windkessel params
  OUT: cases/{case_id}/_1D.json  (P, Q, FFR per vessel)

Step 4b: 3D Steady Fluid Simulation  [Harvey, SimVascular]
  IN:  fluid.vtu, steady inlet Q
  OUT: cases/{case_id}/wall_peak.csv, wall_low.csv  (WSS fields)
  NOTE: Step 4a and 4b run in PARALLEL

Step 5: 3D Steady Solid Simulation  [Harvey, ANSYS pymapdl]
  IN:  solid.msh, pressure BCs from Step 4b wall_peak/low
  OUT: cases/{case_id}/fc_peak.vtu, fc_low.vtu  (von Mises stress)

Step 6: Post-Processing  [Local]
  IN:  _1D.json, fc_peak.vtu, fc_low.vtu
  OUT: results/FFR.csv, results/stress.csv  (PSS, ΔPSS per case)

Step 7: Sensitivity Analysis  [Local]
  IN:  parameters.csv, FFR.csv, stress.csv
  OUT: results/sobol_indices.json, results/sa_plots/
  METHOD: GPR surrogate (scikit-learn) → SALib Sobol indices
```

---

## Input Parameters (X)

**Hemodynamic (X1)**:
- Inlet flow rate (Q)
- Systolic/diastolic pressure
- Windkessel resistance (R1, R2, C)

**Morphology (X2)**:
- Stenosis severity (% area reduction)
- Plaque length
- Fibrous cap thickness
- Lipid core size
- Vessel curvature

**Outputs (Y)**:
- Y1: Von Mises stress (peak, amplitude) — from `stress.csv`
- Y2: FFR (Fractional Flow Reserve) — from `FFR.csv`

---

## Agent Roles (5)

1. **Orchestrator**: Manages step transitions, detects completion, triggers next step
2. **Case Tracker**: Maintains `SimulationPipelineState` for all 1000 cases
3. **Error Analyzer**: Parses solver logs, classifies failures (mesh/BC/divergence), auto-recovers
4. **Quality Validator**: Checks mesh quality, solver convergence, physical plausibility of results
5. **Dashboard**: Streamlit UI showing per-case status, error logs, SA results

---

## Key Source Files

```
src/
├── state.py              # SimulationPipelineState dataclass
├── pipeline_graph.py     # Main LangGraph StateGraph
├── tools/
│   ├── cad_tool.py       # Step 1: CAD generation tool
│   ├── mesh_tool.py      # Step 2: gmsh/Simmetrix tool
│   ├── hpc_submit_tool.py # Step 3-5: SLURM job submission
│   ├── hpc_monitor.py    # HPC job monitoring + result pull
│   ├── postprocess_tool.py # Step 6: result extraction
│   └── sa_tool.py        # Step 7: GPR + Sobol
├── validators/
│   ├── cad_validator.py
│   └── mesh_validator.py
├── agents/
│   └── error_analyzer.py # LLM-based log analysis
└── dashboard.py          # Streamlit UI
```

---

## Environment Variables

See `.env.example`. Required:
- `ANTHROPIC_API_KEY` — LLM calls
- `HARVEY_HOST`, `HARVEY_USER`, `HARVEY_KEY_PATH` — HPC SSH
- `WK1_HOST`, `WK2_HOST` — workstation SSH for meshing
- `CASES_DIR` — path to cases directory (local)
- `HARVEY_CASES_DIR` — path on Harvey

---

## Tech Stack

| Component | Tool |
|-----------|------|
| Agent framework | LangGraph + LangChain |
| LLM | Claude API (`claude-sonnet-4-6`) |
| CAD | Autodesk Inventor iLogic / Python-OCC |
| Fluid mesh | Simmetrix |
| Solid mesh | gmsh (quadratic elements) |
| CFD | SimVascular (svSolver) |
| FEM | ANSYS pymapdl |
| 1D solver | Tree Solver |
| HPC | Harvey (SLURM) via SSH |
| Post-processing | VTK, ParaView Python |
| SA | SALib (Sobol), scikit-learn (GPR) |
| UI | Streamlit |

---

## Current Status (as of 2026-03-17)

- [x] GitHub repo initialized
- [x] Notion plan finalized
- [ ] `state.py` — SimulationPipelineState skeleton
- [ ] `pipeline_graph.py` — mock 7-node graph
- [ ] Tool stubs (all steps)
- [ ] HPC SSH integration
- [ ] Dashboard

## Weekly Goals

- **Week 1** (3/17~3/23): LangGraph basics + mock pipeline graph
- **Week 2** (3/24~3/30): CAD + Meshing agents (real tools)
- **Week 3** (3/31~4/6): Solver + Post-processing agents (HPC)
- **Week 4** (4/7~4/13): SA + Dashboard + demo
