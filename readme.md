# LangGraph CAE Pipeline Agent

An agentic system built with LangGraph that automates a 7-step Computational Fluid/Solid Mechanics pipeline for **Plaque Sensitivity Analysis** — running 1000 parameter cases through CAD generation, meshing, HPC simulation, post-processing, and sensitivity analysis.

**Part of**: Master's Thesis — Cardiovascular Biomechanics, Plaque Rupture Risk Analysis

---

## What This Does

Automates the full simulation pipeline:

```
LHS Sampling → CAD → Meshing → Q-Ramp CFD → 1D+3D Fluid Sim → Solid FEM → Post-Processing → Sensitivity Analysis
```

The agent handles:
- Step transitions across Local / WK1/WK2 / Harvey HPC environments
- Per-case state tracking across 1000 parameter samples
- LLM-based error diagnosis and auto-recovery (mesh failures, solver divergence)
- Quality validation at each step
- Streamlit dashboard for real-time monitoring

---

## Pipeline Overview

| Step | Description | Tool | Output |
|------|-------------|------|--------|
| 0 | LHS parameter sampling | SALib | `parameters.csv` |
| 1 | CAD geometry generation | Inventor / Python-OCC | `*.stp` files |
| 2 | Meshing (fluid + solid) | gmsh + Simmetrix | `fluid.vtu`, `solid.msh` |
| 3 | Q-Ramp CFD | SimVascular (Harvey) | `slab/`, `Flow_hist/` |
| 4a | 1D pulsatile simulation | Tree Solver | `_1D.json` |
| 4b | 3D steady CFD | SimVascular (Harvey) | `wall_peak.csv` |
| 5 | 3D solid FEM | ANSYS pymapdl (Harvey) | `fc_peak.vtu` |
| 6 | Post-processing | VTK | `FFR.csv`, `stress.csv` |
| 7 | Sensitivity analysis | GPR + SALib Sobol | `sobol_indices.json` |

---

## Project Structure

```
├── CLAUDE.md                  # AI agent briefing (Claude CLI)
├── docs/
│   ├── pipeline_design.md     # Detailed pipeline spec
│   └── architecture.md        # Agent architecture & state design
├── src/
│   ├── state.py               # SimulationPipelineState
│   ├── pipeline_graph.py      # LangGraph StateGraph
│   ├── tools/                 # One tool per pipeline step
│   ├── validators/            # Mesh/CAD/result quality checks
│   ├── agents/                # LLM-based error analyzer
│   └── dashboard.py           # Streamlit UI
├── tests/
├── .env.example
└── pyproject.toml
```

---

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Copy and fill env vars
cp .env.example .env

# Run mock pipeline (10 cases, no real HPC)
python -m src.pipeline_graph --mock --cases 10

# Launch dashboard
streamlit run src/dashboard.py
```

---

## Tech Stack

- **Agent**: LangGraph + LangChain
- **LLM**: Claude API (`claude-sonnet-4-6`)
- **Meshing**: gmsh, Simmetrix
- **CFD/FEM**: SimVascular, ANSYS pymapdl
- **HPC**: Harvey (SLURM via SSH)
- **SA**: SALib (Sobol), scikit-learn (GPR)
- **UI**: Streamlit

---

## Timeline

| Week | Focus | Dates |
|------|-------|-------|
| 1 | LangGraph basics + mock pipeline graph | 3/17 ~ 3/23 |
| 2 | CAD + Meshing agents | 3/24 ~ 3/30 |
| 3 | Solver + Post-processing agents (HPC) | 3/31 ~ 4/6 |
| 4 | SA + Dashboard + demo | 4/7 ~ 4/13 |