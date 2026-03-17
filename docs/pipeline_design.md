# Pipeline Design — 7-Step CAE Simulation

## Overview

1000 Latin Hypercube Sampling (LHS) cases are run through a 7-step pipeline distributed across three compute environments.

---

## Step 0: LHS Parameter Sampling

**Where**: Local (Python)
**Tool**: SALib `latin`

**Input**:
- `config/param_ranges.json` — bounds for all parameters

**Output**:
- `data/parameters.csv` — 1000 rows × N columns

**Parameters**:

| Group | Parameter | Symbol | Unit | Range |
|-------|-----------|--------|------|-------|
| Hemodynamic | Inlet flow rate | Q | mL/s | TBD |
| Hemodynamic | Systolic pressure | P_sys | mmHg | TBD |
| Hemodynamic | Diastolic pressure | P_dia | mmHg | TBD |
| Hemodynamic | Windkessel R1 | R1 | Pa·s/m³ | TBD |
| Hemodynamic | Windkessel R2 | R2 | Pa·s/m³ | TBD |
| Hemodynamic | Windkessel C | C | m³/Pa | TBD |
| Morphology | Stenosis severity | SS | % | TBD |
| Morphology | Plaque length | PL | mm | TBD |
| Morphology | Fibrous cap thickness | FCT | mm | TBD |
| Morphology | Lipid core size | LCS | mm | TBD |
| Morphology | Vessel curvature | VC | 1/mm | TBD |

---

## Step 1: CAD Generation

**Where**: Local (Windows)
**Tool**: Autodesk Inventor iLogic OR Python-OCC

**Input**:
- `data/parameters.csv` — row for `case_id`

**Output** (per case at `cases/{case_id}/`):
- `lumen.stp` — vessel lumen geometry
- `fc.stp` — fibrous cap
- `solid.stp` — full solid (vessel wall + plaque)
- `lipid.stp` — lipid core

**Validation**:
- Volume > 0 for each .stp
- No self-intersecting surfaces
- Wall thickness > minimum threshold

**Failure modes**:
- Geometry degeneracy (cap too thin) → skip case, log error
- Inventor crash → retry up to 3x

---

## Step 2: Meshing

**Where**: WK1 (cases 0–499) / WK2 (cases 500–999)
**Tools**: gmsh (solid mesh), Simmetrix (fluid mesh)

**Input**:
- `solid.stp` → gmsh
- `lumen.stp` → Simmetrix

**Output** (per case):
- `solid.msh` — quadratic tetrahedral elements (ANSYS-compatible)
- `fluid.vtu` — fluid domain with labeled boundaries (inlet, outlet, wall)

**Quality thresholds**:
- Aspect ratio < 5.0
- Skewness < 0.85
- Min element quality > 0.2

**Failure recovery**:
- Below threshold → reduce mesh size factor by 0.8x, retry (max 3 attempts)
- Total failure → flag case, continue with remaining

---

## Step 3: Q-Ramp Fluid Simulation

**Where**: Harvey HPC (SLURM)
**Tool**: SimVascular svSolver

**Input**:
- `fluid.vtu`
- Q-ramp inlet waveform (shared config)
- SLURM job template: `config/templates/qramp.sbatch`

**Output** (per case):
- `slab/` — pressure/velocity field snapshots
- `Flow_hist/` — flow history at outlets

**Convergence check**:
- Residual < 1e-4 by final step
- Outlet flow conservation (< 1% error)

---

## Step 4a: 1D Pulsatile Simulation (parallel with 4b)

**Where**: Harvey HPC
**Tool**: Tree Solver + Windkessel BCs

**Input**:
- `Flow_hist/` — from Step 3
- Windkessel params from `parameters.csv` (R1, R2, C)

**Output**:
- `_1D.json` — pressure P(t), flow Q(t), FFR per vessel segment

---

## Step 4b: 3D Steady Fluid Simulation (parallel with 4a)

**Where**: Harvey HPC
**Tool**: SimVascular (steady solver)

**Input**:
- `fluid.vtu`
- Steady inlet Q (peak systole)

**Output**:
- `wall_peak.csv` — WSS at peak systole
- `wall_low.csv` — WSS at low flow

**Note**: Steps 4a and 4b run in parallel. Step 5 waits for both.

---

## Step 5: 3D Steady Solid Simulation

**Where**: Harvey HPC
**Tool**: ANSYS pymapdl

**Input**:
- `solid.msh`
- Pressure BCs: from `wall_peak.csv`, `wall_low.csv` (Step 4b)

**Output**:
- `fc_peak.vtu` — von Mises stress field at peak pressure
- `fc_low.vtu` — von Mises stress field at low pressure

**Convergence check**:
- Newton-Raphson convergence
- Max displacement < anatomical threshold

---

## Step 6: Post-Processing

**Where**: Local
**Tool**: VTK Python API, custom scripts

**Input**:
- `_1D.json` (Step 4a)
- `fc_peak.vtu`, `fc_low.vtu` (Step 5)

**Output** (aggregated across all cases):
- `results/FFR.csv` — FFR per case
- `results/stress.csv` — PSS (peak systolic stress), ΔPSS per case

---

## Step 7: Sensitivity Analysis

**Where**: Local
**Tool**: scikit-learn (GPR surrogate), SALib (Sobol indices)

**Input**:
- `data/parameters.csv` (X)
- `results/FFR.csv` (Y2)
- `results/stress.csv` (Y1)

**Output**:
- `results/sobol_indices.json` — S1, ST indices for X→Y1, X→Y2
- `results/sa_plots/` — bar charts of Sobol indices

**Method**:
1. Split 80/20 train/test
2. Train GPR surrogate on training set
3. Validate on test set (R², RMSE)
4. Compute Sobol indices via SALib on surrogate

---

## Case Directory Structure

```
cases/
└── {case_id:04d}/           # e.g., cases/0042/
    ├── lumen.stp
    ├── fc.stp
    ├── solid.stp
    ├── lipid.stp
    ├── fluid.vtu
    ├── solid.msh
    ├── slab/
    ├── Flow_hist/
    ├── _1D.json
    ├── wall_peak.csv
    ├── wall_low.csv
    ├── fc_peak.vtu
    └── fc_low.vtu

data/
├── parameters.csv
└── param_ranges.json

results/
├── FFR.csv
├── stress.csv
├── sobol_indices.json
└── sa_plots/
```

---

## Case Status States

```
PENDING → CAD_RUNNING → CAD_DONE → MESHING → MESH_DONE →
QRAMP_RUNNING → QRAMP_DONE → SIM_4A_RUNNING + SIM_4B_RUNNING →
SIM_4_DONE → SOLID_RUNNING → SOLID_DONE → POSTPROCESS →
COMPLETE

(any step) → FAILED_{STEP} → RETRYING → ...
```
