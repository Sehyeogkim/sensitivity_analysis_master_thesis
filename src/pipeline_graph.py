"""
Main LangGraph StateGraph for the CAE simulation pipeline.

Week 1: Mock implementation — all nodes use placeholder functions.
Week 2+: Replace mock functions with real tool calls.

See docs/architecture.md for the full graph design.
"""

from langgraph.graph import StateGraph, END
from src.state import SimulationPipelineState, CaseStatus


# ── Mock node functions (Week 1) ──────────────────────────────────────────────

def node_lhs(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 0: LHS sampling — generates parameters.csv"""
    print("[mock] Step 0: LHS sampling")
    # TODO Week 1: implement SALib latin hypercube sampling
    return state


def node_cad(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 1: CAD generation for all PENDING cases"""
    print("[mock] Step 1: CAD generation")
    # TODO Week 2: call src/tools/cad_tool.py per case
    for case_id, case in state["cases"].items():
        if case["status"] == CaseStatus.PENDING:
            state["cases"][case_id]["status"] = CaseStatus.CAD_DONE
            state["cases"][case_id]["current_step"] = 1
    return state


def node_mesh(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 2: Meshing (gmsh + Simmetrix) on WK1/WK2"""
    print("[mock] Step 2: Meshing")
    # TODO Week 2: SSH to WK1/WK2, run gmsh + Simmetrix, validate quality
    for case_id, case in state["cases"].items():
        if case["status"] == CaseStatus.CAD_DONE:
            state["cases"][case_id]["status"] = CaseStatus.MESH_DONE
            state["cases"][case_id]["current_step"] = 2
    return state


def node_qramp(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 3: Q-Ramp CFD on Harvey HPC"""
    print("[mock] Step 3: Q-Ramp simulation")
    # TODO Week 3: submit SLURM jobs via SSH
    for case_id, case in state["cases"].items():
        if case["status"] == CaseStatus.MESH_DONE:
            state["cases"][case_id]["status"] = CaseStatus.QRAMP_DONE
            state["cases"][case_id]["current_step"] = 3
    return state


def node_sim_4a(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 4a: 1D pulsatile simulation (parallel with 4b)"""
    print("[mock] Step 4a: 1D simulation")
    # TODO Week 3: submit Tree Solver jobs
    for case_id, case in state["cases"].items():
        if case["status"] == CaseStatus.QRAMP_DONE:
            state["cases"][case_id]["status"] = CaseStatus.SIM_4A_RUNNING
            state["cases"][case_id]["current_step"] = 4
    return state


def node_sim_4b(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 4b: 3D steady CFD (parallel with 4a)"""
    print("[mock] Step 4b: 3D steady CFD")
    # TODO Week 3: submit SimVascular steady jobs
    for case_id, case in state["cases"].items():
        if case["status"] in (CaseStatus.QRAMP_DONE, CaseStatus.SIM_4A_RUNNING):
            state["cases"][case_id]["status"] = CaseStatus.SIM_4_DONE
            state["cases"][case_id]["current_step"] = 4
    return state


def node_solid(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 5: 3D solid FEM on Harvey"""
    print("[mock] Step 5: Solid FEM")
    # TODO Week 3: submit ANSYS pymapdl jobs
    for case_id, case in state["cases"].items():
        if case["status"] == CaseStatus.SIM_4_DONE:
            state["cases"][case_id]["status"] = CaseStatus.SOLID_DONE
            state["cases"][case_id]["current_step"] = 5
    return state


def node_postprocess(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 6: Post-processing → FFR.csv, stress.csv"""
    print("[mock] Step 6: Post-processing")
    # TODO Week 3: extract scalars from VTU/JSON
    for case_id, case in state["cases"].items():
        if case["status"] == CaseStatus.SOLID_DONE:
            state["cases"][case_id]["status"] = CaseStatus.COMPLETE
            state["cases"][case_id]["current_step"] = 6
            state["completed_cases"].append(case_id)
    return state


def node_sa(state: SimulationPipelineState) -> SimulationPipelineState:
    """Step 7: Sensitivity analysis (GPR + Sobol)"""
    print("[mock] Step 7: Sensitivity analysis")
    # TODO Week 4: GPR training + SALib Sobol computation
    return state


def node_error_analyzer(state: SimulationPipelineState) -> SimulationPipelineState:
    """LLM-based error diagnosis and recovery"""
    print("[mock] Error analyzer: diagnosing failures")
    # TODO Week 3: parse logs, call Claude API, propose fixes
    return state


# ── Routing functions ─────────────────────────────────────────────────────────

def route_after_mesh(state: SimulationPipelineState) -> str:
    # TODO: check mesh quality metrics, route to retry or proceed
    return "qramp"


def all_cases_done(state: SimulationPipelineState) -> str:
    total = len(state["cases"])
    done = len(state["completed_cases"]) + len(state["failed_cases"])
    if done >= total:
        return "sa"
    return "postprocess"


# ── Build the graph ───────────────────────────────────────────────────────────

def build_pipeline_graph() -> StateGraph:
    graph = StateGraph(SimulationPipelineState)

    graph.add_node("lhs", node_lhs)
    graph.add_node("cad", node_cad)
    graph.add_node("mesh", node_mesh)
    graph.add_node("qramp", node_qramp)
    graph.add_node("sim_4a", node_sim_4a)
    graph.add_node("sim_4b", node_sim_4b)
    graph.add_node("solid", node_solid)
    graph.add_node("postprocess", node_postprocess)
    graph.add_node("sa", node_sa)
    graph.add_node("error_analyzer", node_error_analyzer)

    graph.set_entry_point("lhs")
    graph.add_edge("lhs", "cad")
    graph.add_edge("cad", "mesh")
    graph.add_conditional_edges("mesh", route_after_mesh, {"qramp": "qramp", "error_analyzer": "error_analyzer"})
    graph.add_edge("qramp", "sim_4a")
    graph.add_edge("sim_4a", "sim_4b")
    graph.add_edge("sim_4b", "solid")
    graph.add_edge("solid", "postprocess")
    graph.add_conditional_edges("postprocess", all_cases_done, {"sa": "sa", "postprocess": "postprocess"})
    graph.add_edge("sa", END)

    return graph.compile()


if __name__ == "__main__":
    import argparse
    from src.state import make_initial_state
    import uuid

    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", default=True)
    parser.add_argument("--cases", type=int, default=5)
    args = parser.parse_args()

    # Minimal mock parameters for testing
    params = [{"case_id": i, "Q": 5.0, "SS": 0.5} for i in range(args.cases)]
    initial_state = make_initial_state(params, run_id=str(uuid.uuid4()), mock_mode=args.mock)

    app = build_pipeline_graph()
    final_state = app.invoke(initial_state)

    print(f"\nCompleted: {len(final_state['completed_cases'])}/{args.cases} cases")
    print(f"Failed:    {len(final_state['failed_cases'])}/{args.cases} cases")
