
"""
pipeline_graph.py
7단계 Plaque SA 파이프라인을 LangGraph StateGraph로 구현 (mock 버전)

파이프라인 흐름:
  lhs → cad → mesh → qramp → fluid_1d ┐
                                        ├→ solid → post → sa
                               fluid_3d ┘

* fluid_1d / fluid_3d 는 병렬 실행 (Send API 또는 fan-out 패턴)
* 각 노드는 실제 시뮬레이션 대신 mock 함수로 대체
* 에러 발생 시 retry → 최대 2회 초과하면 fail 처리
"""

import random
import time
from langgraph.graph import StateGraph, END

from state import (
    SimulationPipelineState,
    STEP_ORDER,
    make_initial_state,
    summary,
)


# ── 설정 ────────────────────────────────────────────────────────────────────────
MAX_RETRIES = 2
MOCK_FAIL_RATE = 0.1   # 10% 확률로 랜덤 실패 (테스트용)


# ── Mock 실행 헬퍼 ───────────────────────────────────────────────────────────────
def mock_run(step_name: str, duration: float = 0.1, fail_rate: float = MOCK_FAIL_RATE) -> tuple[bool, str]:
    """
    실제 시뮬레이션 대신 성공/실패를 시뮬레이션.
    Returns: (success, message)
    """
    time.sleep(duration)
    if random.random() < fail_rate:
        return False, f"[{step_name}] mock error: 시뮬레이션 실패 (랜덤)"
    return True, f"[{step_name}] 완료"


def set_step(state: SimulationPipelineState, step: str, status: str) -> dict:
    """step_status 업데이트 헬퍼."""
    new_status = dict(state["step_status"])
    new_status[step] = status
    return {"step_status": new_status, "current_step": step}


def increment_retry(state: SimulationPipelineState, step: str) -> dict:
    new_retry = dict(state["retry_count"])
    new_retry[step] = new_retry.get(step, 0) + 1
    return {"retry_count": new_retry}


# ── 노드 함수들 ─────────────────────────────────────────────────────────────────

def node_lhs(state: SimulationPipelineState) -> dict:
    """Step 0: Latin Hypercube Sampling → parameters.csv 생성"""
    print(f"  [LHS] case={state['case_id']} 파라미터 샘플링 시작")
    update = set_step(state, "lhs", "running")

    success, msg = mock_run("lhs", duration=0.05, fail_rate=0.0)  # LHS는 실패 없음

    new_outputs = dict(state["outputs"])
    new_outputs["parameters_csv"] = f"outputs/{state['case_id']}/parameters.csv"

    new_status = dict(state["step_status"])
    new_status["lhs"] = "done"

    return {
        "step_status": new_status,
        "current_step": "lhs",
        "outputs": new_outputs,
        "error_log": [],
    }


def node_cad(state: SimulationPipelineState) -> dict:
    """Step 1: CAD 생성 (Inventor iLogic / Python-OCC mock)"""
    print(f"  [CAD] case={state['case_id']} CAD 생성 중")
    success, msg = mock_run("cad")

    new_status = dict(state["step_status"])
    new_outputs = dict(state["outputs"])
    errors = []

    if success:
        new_status["cad"] = "done"
        new_outputs.update({
            "lumen_stp": f"outputs/{state['case_id']}/lumen.stp",
            "fc_stp":    f"outputs/{state['case_id']}/fc.stp",
            "solid_stp": f"outputs/{state['case_id']}/solid.stp",
            "lipid_stp": f"outputs/{state['case_id']}/lipid.stp",
        })
    else:
        new_status["cad"] = "failed"
        errors = [msg]

    return {
        "step_status": new_status,
        "current_step": "cad",
        "outputs": new_outputs,
        "error_log": errors,
    }


def node_mesh(state: SimulationPipelineState) -> dict:
    """Step 2: 메싱 (gmsh + Simmetrix mock)"""
    print(f"  [Mesh] case={state['case_id']} 메싱 시작")
    success, msg = mock_run("mesh")

    new_status = dict(state["step_status"])
    new_outputs = dict(state["outputs"])
    errors = []

    if success:
        new_status["mesh"] = "done"
        new_outputs.update({
            "fluid_vtu": f"outputs/{state['case_id']}/fluid.vtu",
            "solid_msh": f"outputs/{state['case_id']}/solid.msh",
        })
    else:
        new_status["mesh"] = "failed"
        errors = [msg]

    return {
        "step_status": new_status,
        "current_step": "mesh",
        "outputs": new_outputs,
        "error_log": errors,
    }


def node_qramp(state: SimulationPipelineState) -> dict:
    """Step 3: Q-Ramp Fluid Simulation (Harvey HPC mock)"""
    print(f"  [Q-Ramp] case={state['case_id']} Q-Ramp 시뮬레이션")
    success, msg = mock_run("qramp", duration=0.2)

    new_status = dict(state["step_status"])
    new_outputs = dict(state["outputs"])
    errors = []

    if success:
        new_status["qramp"] = "done"
        new_outputs.update({
            "slab_dir":      f"outputs/{state['case_id']}/slab/",
            "flow_hist_dir": f"outputs/{state['case_id']}/Flow_hist/",
        })
    else:
        new_status["qramp"] = "failed"
        errors = [msg]

    return {
        "step_status": new_status,
        "current_step": "qramp",
        "outputs": new_outputs,
        "error_log": errors,
    }


def node_fluid_1d(state: SimulationPipelineState) -> dict:
    """Step 4a: 1D Pulsatile Simulation (Tree Solver mock)"""
    print(f"  [1D Fluid] case={state['case_id']} 1D 시뮬레이션")
    success, msg = mock_run("fluid_1d", duration=0.15)

    new_status = dict(state["step_status"])
    new_outputs = dict(state["outputs"])
    errors = []

    if success:
        new_status["fluid_1d"] = "done"
        new_outputs["result_1d_json"] = f"outputs/{state['case_id']}/_1D.json"
    else:
        new_status["fluid_1d"] = "failed"
        errors = [msg]

    return {
        "step_status": new_status,
        "current_step": "fluid_1d",
        "outputs": new_outputs,
        "error_log": errors,
    }


def node_fluid_3d(state: SimulationPipelineState) -> dict:
    """Step 4b: 3D Steady Fluid Simulation (SimVascular mock)"""
    print(f"  [3D Fluid] case={state['case_id']} 3D CFD 시뮬레이션")
    success, msg = mock_run("fluid_3d", duration=0.3)

    new_status = dict(state["step_status"])
    new_outputs = dict(state["outputs"])
    errors = []

    if success:
        new_status["fluid_3d"] = "done"
        new_outputs.update({
            "wall_peak_csv": f"outputs/{state['case_id']}/wall_peak.csv",
            "wall_low_csv":  f"outputs/{state['case_id']}/wall_low.csv",
        })
    else:
        new_status["fluid_3d"] = "failed"
        errors = [msg]

    return {
        "step_status": new_status,
        "current_step": "fluid_3d",
        "outputs": new_outputs,
        "error_log": errors,
    }


def node_solid(state: SimulationPipelineState) -> dict:
    """Step 5: 3D Solid Simulation (ANSYS pymapdl mock)"""
    print(f"  [Solid] case={state['case_id']} 구조 해석 시뮬레이션")
    success, msg = mock_run("solid", duration=0.3)

    new_status = dict(state["step_status"])
    new_outputs = dict(state["outputs"])
    errors = []

    if success:
        new_status["solid"] = "done"
        new_outputs.update({
            "fc_peak_vtu": f"outputs/{state['case_id']}/fc_peak.vtu",
            "fc_low_vtu":  f"outputs/{state['case_id']}/fc_low.vtu",
        })
    else:
        new_status["solid"] = "failed"
        errors = [msg]

    return {
        "step_status": new_status,
        "current_step": "solid",
        "outputs": new_outputs,
        "error_log": errors,
    }


def node_post(state: SimulationPipelineState) -> dict:
    """Step 6: Post-Processing → FFR.csv, stress.csv"""
    print(f"  [Post] case={state['case_id']} 후처리 중")
    success, msg = mock_run("post", duration=0.1, fail_rate=0.05)

    new_status = dict(state["step_status"])
    new_outputs = dict(state["outputs"])
    errors = []

    if success:
        new_status["post"] = "done"
        new_outputs.update({
            "ffr_csv":    f"outputs/{state['case_id']}/FFR.csv",
            "stress_csv": f"outputs/{state['case_id']}/stress.csv",
        })
    else:
        new_status["post"] = "failed"
        errors = [msg]

    return {
        "step_status": new_status,
        "current_step": "post",
        "outputs": new_outputs,
        "error_log": errors,
    }


def node_sa(state: SimulationPipelineState) -> dict:
    """Step 7: Sensitivity Analysis (GPR Surrogate + Sobol Indices mock)"""
    print(f"  [SA] case={state['case_id']} 민감도 분석")
    success, msg = mock_run("sa", duration=0.1, fail_rate=0.0)  # SA는 실패 없음

    new_status = dict(state["step_status"])
    new_outputs = dict(state["outputs"])

    new_status["sa"] = "done"
    new_outputs["sobol_indices_json"] = f"outputs/{state['case_id']}/sobol_indices.json"

    return {
        "step_status": new_status,
        "current_step": "sa",
        "outputs": new_outputs,
        "error_log": [],
    }


# ── 조건 분기 (Conditional Edges) ───────────────────────────────────────────────

def route_after_cad(state: SimulationPipelineState) -> str:
    if state["step_status"].get("cad") == "done":
        return "mesh"
    retry = state["retry_count"].get("cad", 0)
    if retry < MAX_RETRIES:
        return "retry_cad"
    return "fail"


def route_after_mesh(state: SimulationPipelineState) -> str:
    if state["step_status"].get("mesh") == "done":
        return "qramp"
    retry = state["retry_count"].get("mesh", 0)
    if retry < MAX_RETRIES:
        return "retry_mesh"
    return "fail"


def route_after_qramp(state: SimulationPipelineState) -> str:
    if state["step_status"].get("qramp") == "done":
        return "fluid_1d"   # fluid_1d, fluid_3d 동시 fan-out
    retry = state["retry_count"].get("qramp", 0)
    if retry < MAX_RETRIES:
        return "retry_qramp"
    return "fail"


def route_after_fluids(state: SimulationPipelineState) -> str:
    """1D + 3D 모두 완료되면 solid로 진행."""
    done_1d = state["step_status"].get("fluid_1d") == "done"
    done_3d = state["step_status"].get("fluid_3d") == "done"
    if done_1d and done_3d:
        return "solid"
    # 어느 한쪽이라도 실패
    failed_1d = state["step_status"].get("fluid_1d") == "failed"
    failed_3d = state["step_status"].get("fluid_3d") == "failed"
    if failed_1d or failed_3d:
        return "fail"
    return "wait_fluids"   # 아직 실행 중 (실제 구현에서는 polling)


def route_after_solid(state: SimulationPipelineState) -> str:
    if state["step_status"].get("solid") == "done":
        return "post"
    retry = state["retry_count"].get("solid", 0)
    if retry < MAX_RETRIES:
        return "retry_solid"
    return "fail"


def route_after_post(state: SimulationPipelineState) -> str:
    if state["step_status"].get("post") == "done":
        return "sa"
    return "fail"


# ── Retry 노드 ──────────────────────────────────────────────────────────────────

def make_retry_node(step: str):
    """retry 카운트를 올리고 해당 step을 pending으로 리셋."""
    def retry_node(state: SimulationPipelineState) -> dict:
        print(f"  [RETRY] {step} 재시도 (attempt {state['retry_count'].get(step, 0) + 1})")
        new_status = dict(state["step_status"])
        new_status[step] = "pending"
        new_retry = dict(state["retry_count"])
        new_retry[step] = new_retry.get(step, 0) + 1
        return {"step_status": new_status, "retry_count": new_retry}
    retry_node.__name__ = f"retry_{step}"
    return retry_node


def node_fail(state: SimulationPipelineState) -> dict:
    """파이프라인 실패 처리."""
    failed_steps = [s for s, status in state["step_status"].items() if status == "failed"]
    print(f"  [FAIL] case={state['case_id']} 실패 단계: {failed_steps}")
    return {"error_log": [f"Pipeline terminated. Failed steps: {failed_steps}"]}


# ── 그래프 빌드 ─────────────────────────────────────────────────────────────────

def build_pipeline_graph() -> StateGraph:
    graph = StateGraph(SimulationPipelineState)

    # 노드 등록
    graph.add_node("lhs",      node_lhs)
    graph.add_node("cad",      node_cad)
    graph.add_node("mesh",     node_mesh)
    graph.add_node("qramp",    node_qramp)
    graph.add_node("fluid_1d", node_fluid_1d)
    graph.add_node("fluid_3d", node_fluid_3d)
    graph.add_node("solid",    node_solid)
    graph.add_node("post",     node_post)
    graph.add_node("sa",       node_sa)
    graph.add_node("fail",     node_fail)

    # Retry 노드
    for step in ["cad", "mesh", "qramp", "solid"]:
        graph.add_node(f"retry_{step}", make_retry_node(step))

    # 시작점
    graph.set_entry_point("lhs")

    # 순차 엣지
    graph.add_edge("lhs", "cad")

    # 조건 분기 엣지
    graph.add_conditional_edges("cad", route_after_cad, {
        "mesh":      "mesh",
        "retry_cad": "retry_cad",
        "fail":      "fail",
    })
    graph.add_edge("retry_cad", "cad")

    graph.add_conditional_edges("mesh", route_after_mesh, {
        "qramp":      "qramp",
        "retry_mesh": "retry_mesh",
        "fail":       "fail",
    })
    graph.add_edge("retry_mesh", "mesh")

    graph.add_conditional_edges("qramp", route_after_qramp, {
        "fluid_1d":    "fluid_1d",
        "retry_qramp": "retry_qramp",
        "fail":        "fail",
    })
    graph.add_edge("retry_qramp", "qramp")

    # fluid_1d → fluid_3d fan-out (mock: 순차 실행)
    graph.add_edge("fluid_1d", "fluid_3d")

    graph.add_conditional_edges("fluid_3d", route_after_fluids, {
        "solid":       "solid",
        "fail":        "fail",
        "wait_fluids": "fluid_3d",   # polling fallback
    })

    graph.add_conditional_edges("solid", route_after_solid, {
        "post":        "post",
        "retry_solid": "retry_solid",
        "fail":        "fail",
    })
    graph.add_edge("retry_solid", "solid")

    graph.add_conditional_edges("post", route_after_post, {
        "sa":   "sa",
        "fail": "fail",
    })

    graph.add_edge("sa",   END)
    graph.add_edge("fail", END)

    return graph


# ── 실행 진입점 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("=" * 60)
    print("  Plaque SA Pipeline (mock) — LangGraph")
    print("=" * 60)

    # 테스트: 케이스 3개 순차 실행
    test_cases = [
        {"case_id": "case_001", "params": {"lumen_r": 1.5, "fc_thick": 0.08, "lipid_angle": 45}},
        {"case_id": "case_042", "params": {"lumen_r": 1.2, "fc_thick": 0.12, "lipid_angle": 30}},
        {"case_id": "case_100", "params": {"lumen_r": 1.8, "fc_thick": 0.06, "lipid_angle": 60}},
    ]

    graph = build_pipeline_graph()
    app = graph.compile()

    for tc in test_cases:
        init_state = make_initial_state(
            case_id=tc["case_id"],
            case_params=tc["params"],
            run_on="harvey",
        )
        print(f"\n▶ {tc['case_id']} 실행 시작")
        final_state = app.invoke(init_state)
        print(summary(final_state))
        print()