"""
Step 1: CAD Generation Tool
Generates .stp geometry files from parameters.

Week 2 implementation: Autodesk Inventor iLogic or Python-OCC
"""

# TODO Week 2: implement CAD generation
# Options:
#   A) Inventor iLogic: call via COM automation (Windows only)
#   B) Python-OCC: install pythonocc-core, parametric NURBS modeling

def generate_cad(case_id: int, params: dict, output_dir: str) -> dict:
    """
    Generate CAD geometry for one case.

    Returns:
        dict with keys: lumen_stp, fc_stp, solid_stp, lipid_stp
        (file paths to generated .stp files)
    """
    raise NotImplementedError("Week 2: implement CAD generation")
