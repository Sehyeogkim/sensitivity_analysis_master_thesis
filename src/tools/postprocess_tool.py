"""
Step 6: Post-Processing Tool
Extracts scalar outputs (FFR, von Mises stress) from simulation results.

Week 3 implementation.
"""

# TODO Week 3: VTK Python API + JSON parsing

def extract_ffr(json_1d_path: str) -> float:
    """Extract FFR value from _1D.json"""
    raise NotImplementedError("Week 3: implement FFR extraction from _1D.json")


def extract_stress(fc_peak_vtu: str, fc_low_vtu: str) -> dict:
    """Extract PSS and ΔPSS from VTU files. Returns {PSS: float, dPSS: float}"""
    raise NotImplementedError("Week 3: implement stress extraction from VTU")
