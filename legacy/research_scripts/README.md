# Historical plaque simulation scripts

Recovered from [Sehyeogkim/Sensitivity_Analysis](https://github.com/Sehyeogkim/Sensitivity_Analysis/tree/3c9fb6f761fc7cb6677051740625c3eb2fc336dd), commit `3c9fb6f761fc7cb6677051740625c3eb2fc336dd` (the last snapshot before all files were removed).

These scripts are kept together to preserve their local imports. They are research code, not an installed package, and are not connected to the LangGraph prototype in `../../src/`.

| Files | Purpose |
| --- | --- |
| `main_CAD.py`, `utils_CAD.py` | Vessel/plaque parameters and CAD helpers, including Autodesk Inventor integration |
| `sub_gmshing.py`, `utils_gmsh.py`, `check.py` | Mesh generation, quality checks and case inspection |
| `pymapdl_simulation.py`, `Voronoi_tesselation_KDTREE.py` | ANSYS MAPDL structural simulation and spatial/material assignment helpers |
| `utils_bc.py` | Pressure/traction interpolation onto structural mesh nodes |
| `utils_prep.py`, `utils_post.py`, `vtp_modify.py` | Mesh/result preparation and postprocessing |
| `pulsatile/` | Four historical SimVascular input files |

## Using this code

Inspect each script before execution: some scripts perform work at import or top level, and paths reference the original workstation/HPC layout. Dependencies include NumPy, SciPy, pandas, PyVista, meshio, Gmsh and ANSYS MAPDL; CAD operations may require Autodesk Inventor and the original platform. Solver licenses, external geometry/meshes and result data are not bundled here. No end-to-end solver run was performed during consolidation.

The source repository's original history remains available. Installed `node_modules`, Python bytecode caches, CAD example binaries, generated meshes and wall-result datasets were not copied into this directory. This is a source-code consolidation, not a complete runnable dataset.

`SOURCE_MANIFEST.json` records the original Git blob IDs and SHA-256 checksums of the 15 recovered files. The source scripts and solver inputs were restored without algorithm changes.
