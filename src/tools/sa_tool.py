"""
Step 7: Sensitivity Analysis Tool
GPR surrogate training + Sobol index computation.

Week 4 implementation.
"""

# TODO Week 4: scikit-learn GPR + SALib

def train_gpr(X, Y):
    """Train Gaussian Process Regression surrogate."""
    raise NotImplementedError("Week 4: implement GPR training")


def compute_sobol(model, param_ranges: dict, n_samples: int = 1024) -> dict:
    """Compute Sobol S1 and ST indices. Returns dict with indices."""
    raise NotImplementedError("Week 4: implement Sobol index computation via SALib")
