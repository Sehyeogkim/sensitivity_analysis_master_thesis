"""
Step 2: Meshing Tool
Generates fluid.vtu (Simmetrix) and solid.msh (gmsh) from .stp files.

Week 2 implementation.
"""

# TODO Week 2
# solid mesh: gmsh Python API — quadratic tetrahedral elements
# fluid mesh: Simmetrix via CLI or Python bindings

def generate_solid_mesh(case_id: int, solid_stp: str, output_dir: str) -> str:
    """Run gmsh on solid.stp → solid.msh"""
    raise NotImplementedError("Week 2: implement gmsh meshing")


def generate_fluid_mesh(case_id: int, lumen_stp: str, output_dir: str) -> str:
    """Run Simmetrix on lumen.stp → fluid.vtu"""
    raise NotImplementedError("Week 2: implement Simmetrix meshing")
