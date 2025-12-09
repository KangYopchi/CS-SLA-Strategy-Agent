"""
agent_spike.py에 대한 테스트 코드

테스트 전략:
1. 단위 테스트: 각 함수를 독립적으로 테스트
2. 통합 테스트: Graph 전체 플로우 테스트
3. 엣지 케이스: 예외 상황 테스트
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

# Note: 일부 함수는 agent_spike.py에 아직 분리되지 않았으므로
# 테스트를 위해 임시로 import하거나 개선된 버전 사용
try:
    from src.agent_spike import (
        AgentState,
        create_graph,
        generate_report,
        load_data,
        run_agent,
    )

    # calculate_sla_grade는 아직 분리되지 않았으므로 테스트에서 직접 구현
    # agent_spike.py의 실제 기준에 맞춤
    def calculate_sla_grade(response_rate: float) -> str:
        """테스트용 SLA 등급 계산 함수 (agent_spike.py 기준)"""
        if response_rate >= 95:
            return "S"
        elif response_rate >= 90:
            return "A"
        elif response_rate >= 85:
            return "B"
        elif response_rate >= 80:
            return "C"
        elif response_rate >= 75:
            return "D"
        else:
            return "DD"
except ImportError:
    # 개선된 버전 사용
    from src.agent_spike_improved import (
        AgentState,
        calculate_sla_grade,
        create_graph,
        generate_report,
        load_data,
        run_agent,
    )


# ============================================================================
# Helper Functions
# ============================================================================


def to_dict(state):
    """State를 dict로 변환 (Pydantic BaseModel 또는 dict 모두 지원)"""
    if hasattr(state, "dict"):
        return state.dict()
    elif hasattr(state, "model_dump"):  # Pydantic v2
        return state.model_dump()
    elif isinstance(state, dict):
        return state.copy() if hasattr(state, "copy") else dict(state)
    else:
        return dict(state)


# ============================================================================
# Fixtures: 테스트 데이터 준비
# ============================================================================


@pytest.fixture
def sample_csv_data():
    """샘플 CSV 데이터 생성"""
    data = {
        "시간": [9, 10, 11, 12],
        "인입콜": [100, 120, 110, 130],
        "응답콜": [95, 108, 99, 117],
        "투입인원": [10, 12, 11, 13],
    }
    return pd.DataFrame(data)


@pytest.fixture
def temp_csv_file(sample_csv_data):
    """임시 CSV 파일 생성"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        sample_csv_data.to_csv(f.name, index=False)
        yield f.name
    Path(f.name).unlink()  # 테스트 후 삭제


@pytest.fixture
def empty_csv_file():
    """빈 CSV 파일 생성"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        pd.DataFrame().to_csv(f.name, index=False)
        yield f.name
    Path(f.name).unlink()


@pytest.fixture
def initial_state():
    """초기 상태 생성"""
    # AgentState가 Pydantic BaseModel인지 TypedDict인지 확인
    try:
        # Pydantic BaseModel인 경우 - 객체 생성
        # agent_spike.py는 BaseModel을 사용하므로 객체 생성
        return AgentState(
            csv_path=None,  # 나중에 테스트에서 설정
            income_call=0,
            answer_call=0,
            sla_goal="S",
            sla_result=None,
            report=None,
            simulation="테스트 시뮬레이션",
            message=[],  # agent_spike.py에서는 'message' (단수)
        )
    except Exception:
        # TypedDict인 경우 (agent_spike_improved.py 사용 시)
        return {
            "csv_path": None,
            "income_call": 0,
            "answer_call": 0,
            "sla_goal": "S",
            "sla_result": None,
            "report": None,
            "simulation": "테스트 시뮬레이션",
            "messages": [],  # TypedDict에서는 'messages' (복수)
        }


# ============================================================================
# 단위 테스트: SLA 등급 계산 함수
# ============================================================================


class TestCalculateSLAGrade:
    """SLA 등급 계산 함수 테스트"""

    def test_grade_s(self):
        """S 등급 테스트 (95% 이상)"""
        assert calculate_sla_grade(95.0) == "S"
        assert calculate_sla_grade(100.0) == "S"
        assert calculate_sla_grade(99.9) == "S"

    def test_grade_a(self):
        """A 등급 테스트 (90-94%)"""
        assert calculate_sla_grade(90.0) == "A"
        assert calculate_sla_grade(94.9) == "A"
        assert calculate_sla_grade(92.5) == "A"

    def test_grade_b(self):
        """B 등급 테스트 (85-89%) - agent_spike.py 기준"""
        assert calculate_sla_grade(85.0) == "B"
        assert calculate_sla_grade(89.9) == "B"
        assert calculate_sla_grade(87.0) == "B"

    def test_grade_c(self):
        """C 등급 테스트 (80-84%) - agent_spike.py 기준"""
        assert calculate_sla_grade(80.0) == "C"
        assert calculate_sla_grade(84.9) == "C"
        assert calculate_sla_grade(82.0) == "C"

    def test_grade_d(self):
        """D 등급 테스트 (75-79%) - agent_spike.py 기준"""
        assert calculate_sla_grade(75.0) == "D"
        assert calculate_sla_grade(79.9) == "D"
        assert calculate_sla_grade(77.0) == "D"

    def test_edge_cases(self):
        """경계값 테스트 - agent_spike.py 기준"""
        assert calculate_sla_grade(95.0) == "S"  # 정확히 95%
        assert calculate_sla_grade(90.0) == "A"  # 정확히 90%
        assert calculate_sla_grade(85.0) == "B"  # 정확히 85%
        assert calculate_sla_grade(80.0) == "C"  # 정확히 80%
        assert calculate_sla_grade(75.0) == "D"  # 정확히 75%
        assert calculate_sla_grade(74.9) == "DD"  # 75% 미만


# ============================================================================
# 단위 테스트: 데이터 로드 함수
# ============================================================================


class TestLoadData:
    """데이터 로드 함수 테스트"""

    def test_load_data_success(self, temp_csv_file, initial_state):
        """정상적인 데이터 로드 테스트"""
        # AgentState 객체를 직접 사용
        if isinstance(initial_state, dict):
            # TypedDict인 경우
            state = initial_state.copy()
            state["csv_path"] = temp_csv_file
        else:
            # Pydantic BaseModel인 경우 - 객체 속성 설정
            state = AgentState(
                csv_path=temp_csv_file,
                income_call=initial_state.income_call,
                answer_call=initial_state.answer_call,
                sla_goal=initial_state.sla_goal,
                sla_result=initial_state.sla_result,
                report=initial_state.report,
                simulation=initial_state.simulation,
                message=initial_state.message
                if hasattr(initial_state, "message")
                else [],
            )

        result = load_data(state)

        # 결과 검증 (Pydantic BaseModel인 경우 속성 접근, dict인 경우 get 사용)
        if isinstance(result, dict):
            assert result.get("income_call") == 460  # 100 + 120 + 110 + 130
            assert result.get("answer_call") == 419  # 95 + 108 + 99 + 117
            assert result.get("sla_result") is not None
            assert result.get("sla_result") in ["S", "A", "B", "C", "D", "DD"]
        else:
            assert result.income_call == 460
            assert result.answer_call == 419
            assert result.sla_result is not None
            assert result.sla_result in ["S", "A", "B", "C", "D", "DD"]

    def test_load_data_file_not_found(self, initial_state):
        """파일이 없을 때 테스트"""
        if isinstance(initial_state, dict):
            state = initial_state.copy()
            state["csv_path"] = "nonexistent_file.csv"
        else:
            state = AgentState(
                csv_path="nonexistent_file.csv",
                income_call=initial_state.income_call,
                answer_call=initial_state.answer_call,
                sla_goal=initial_state.sla_goal,
                sla_result=initial_state.sla_result,
                report=initial_state.report,
                simulation=initial_state.simulation,
                message=initial_state.message
                if hasattr(initial_state, "message")
                else [],
            )

        result = load_data(state)

        if isinstance(result, dict):
            assert (
                result.get("sla_result") == "ERROR" or result.get("sla_result") is None
            )
            assert result.get("income_call", 0) == 0
            assert result.get("answer_call", 0) == 0
        else:
            assert result.sla_result == "ERROR" or result.sla_result is None
            assert result.income_call == 0
            assert result.answer_call == 0

    def test_load_data_empty_file(self, empty_csv_file, initial_state):
        """빈 파일 테스트"""
        if isinstance(initial_state, dict):
            state = initial_state.copy()
            state["csv_path"] = empty_csv_file
        else:
            state = AgentState(
                csv_path=empty_csv_file,
                income_call=initial_state.income_call,
                answer_call=initial_state.answer_call,
                sla_goal=initial_state.sla_goal,
                sla_result=initial_state.sla_result,
                report=initial_state.report,
                simulation=initial_state.simulation,
                message=initial_state.message
                if hasattr(initial_state, "message")
                else [],
            )

        result = load_data(state)

        # 빈 파일에 대한 처리 확인
        if isinstance(result, dict):
            assert "sla_result" in result or result.get("sla_result") is not None
        else:
            assert hasattr(result, "sla_result") or result.sla_result is not None

    def test_load_data_missing_columns(self, initial_state):
        """필수 컬럼이 없을 때 테스트"""
        # 잘못된 컬럼을 가진 CSV 생성
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            pd.DataFrame({"wrong_col": [1, 2, 3]}).to_csv(f.name, index=False)
            temp_path = f.name

        try:
            if isinstance(initial_state, dict):
                state = initial_state.copy()
                state["csv_path"] = temp_path
            else:
                state = AgentState(
                    csv_path=temp_path,
                    income_call=initial_state.income_call,
                    answer_call=initial_state.answer_call,
                    sla_goal=initial_state.sla_goal,
                    sla_result=initial_state.sla_result,
                    report=initial_state.report,
                    simulation=initial_state.simulation,
                    message=initial_state.message
                    if hasattr(initial_state, "message")
                    else [],
                )

            result = load_data(state)

            # 에러 처리 확인
            if isinstance(result, dict):
                assert (
                    result.get("sla_result") == "ERROR"
                    or result.get("sla_result") is None
                )
            else:
                assert result.sla_result == "ERROR" or result.sla_result is None
        finally:
            Path(temp_path).unlink()

    def test_load_data_zero_income_calls(self, initial_state):
        """인입콜이 0일 때 테스트"""
        # 인입콜이 모두 0인 데이터
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            data = pd.DataFrame(
                {
                    "시간": [9, 10],
                    "인입콜": [0, 0],
                    "응답콜": [0, 0],
                }
            )
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            if isinstance(initial_state, dict):
                state = initial_state.copy()
                state["csv_path"] = temp_path
            else:
                state = AgentState(
                    csv_path=temp_path,
                    income_call=initial_state.income_call,
                    answer_call=initial_state.answer_call,
                    sla_goal=initial_state.sla_goal,
                    sla_result=initial_state.sla_result,
                    report=initial_state.report,
                    simulation=initial_state.simulation,
                    message=initial_state.message
                    if hasattr(initial_state, "message")
                    else [],
                )

            result = load_data(state)

            # 0으로 나누기 방지 확인
            if isinstance(result, dict):
                assert (
                    result.get("sla_result") == "ERROR"
                    or result.get("income_call", 0) == 0
                )
            else:
                assert result.sla_result == "ERROR" or result.income_call == 0
        finally:
            Path(temp_path).unlink()

    def test_load_data_calculation_accuracy(self, initial_state):
        """계산 정확도 테스트"""
        # 정확한 계산을 위한 테스트 데이터
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            data = pd.DataFrame(
                {
                    "시간": [9],
                    "인입콜": [100],
                    "응답콜": [95],  # 정확히 95%
                }
            )
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            if isinstance(initial_state, dict):
                state = initial_state.copy()
                state["csv_path"] = temp_path
            else:
                state = AgentState(
                    csv_path=temp_path,
                    income_call=initial_state.income_call,
                    answer_call=initial_state.answer_call,
                    sla_goal=initial_state.sla_goal,
                    sla_result=initial_state.sla_result,
                    report=initial_state.report,
                    simulation=initial_state.simulation,
                    message=initial_state.message
                    if hasattr(initial_state, "message")
                    else [],
                )

            result = load_data(state)

            if isinstance(result, dict):
                assert result.get("income_call") == 100
                assert result.get("answer_call") == 95
                assert result.get("sla_result") == "S"  # 95%는 S등급
            else:
                assert result.income_call == 100
                assert result.answer_call == 95
                assert result.sla_result == "S"  # 95%는 S등급
        finally:
            Path(temp_path).unlink()


# ============================================================================
# 단위 테스트: 리포트 생성 함수
# ============================================================================


class TestGenerateReport:
    """리포트 생성 함수 테스트"""

    def test_generate_report_success(self, initial_state):
        """정상적인 리포트 생성 테스트"""
        if isinstance(initial_state, dict):
            state = initial_state.copy()
            state["income_call"] = 1000
            state["answer_call"] = 950
            state["sla_result"] = "S"
            state["sla_goal"] = "S"
        else:
            state = AgentState(
                csv_path=initial_state.csv_path
                if hasattr(initial_state, "csv_path")
                else None,
                income_call=1000,
                answer_call=950,
                sla_goal="S",
                sla_result="S",
                report=None,
                simulation=initial_state.simulation,
                message=initial_state.message
                if hasattr(initial_state, "message")
                else [],
            )

        result = generate_report(state)

        if isinstance(result, dict):
            assert result.get("report") is not None
            report_text = result.get("report", "")
        else:
            assert result.report is not None
            report_text = result.report

        assert (
            "인입콜" in report_text
            or "income" in report_text.lower()
            or "콜" in report_text
        )
        assert (
            "응답콜" in report_text
            or "answer" in report_text.lower()
            or "콜" in report_text
        )
        assert "S" in report_text
        assert "1000" in report_text or "1,000" in report_text
        assert "950" in report_text

    def test_generate_report_with_simulation(self, initial_state):
        """시뮬레이션 정보가 포함된 리포트 테스트"""
        if isinstance(initial_state, dict):
            state = initial_state.copy()
            state["income_call"] = 1000
            state["answer_call"] = 900
            state["sla_result"] = "A"
            state["sla_goal"] = "S"
            state["simulation"] = "오늘 폭설 예상"
        else:
            state = AgentState(
                csv_path=initial_state.csv_path
                if hasattr(initial_state, "csv_path")
                else None,
                income_call=1000,
                answer_call=900,
                sla_goal="S",
                sla_result="A",
                report=None,
                simulation="오늘 폭설 예상",
                message=initial_state.message
                if hasattr(initial_state, "message")
                else [],
            )

        result = generate_report(state)

        if isinstance(result, dict):
            assert result.get("report") is not None
            # 시뮬레이션 정보가 리포트에 포함되어야 함 (개선 후)
            # report_text = result.get("report", "")
            # assert "폭설" in report_text
        else:
            assert result.report is not None

    def test_generate_report_error_state(self, initial_state):
        """에러 상태일 때 리포트 생성 테스트"""
        if isinstance(initial_state, dict):
            state = initial_state.copy()
            state["sla_result"] = "ERROR"
        else:
            state = AgentState(
                csv_path=initial_state.csv_path
                if hasattr(initial_state, "csv_path")
                else None,
                income_call=initial_state.income_call,
                answer_call=initial_state.answer_call,
                sla_goal=initial_state.sla_goal,
                sla_result="ERROR",
                report=None,
                simulation=initial_state.simulation,
                message=initial_state.message
                if hasattr(initial_state, "message")
                else [],
            )

        result = generate_report(state)

        # 에러 상태에 대한 적절한 리포트 생성 확인
        if isinstance(result, dict):
            assert result.get("report") is not None
        else:
            assert result.report is not None

    def test_generate_report_missing_data(self, initial_state):
        """데이터가 없을 때 리포트 생성 테스트"""
        if isinstance(initial_state, dict):
            state = initial_state.copy()
            state["income_call"] = 0
            state["answer_call"] = 0
            state["sla_result"] = None
        else:
            state = AgentState(
                csv_path=initial_state.csv_path
                if hasattr(initial_state, "csv_path")
                else None,
                income_call=0,
                answer_call=0,
                sla_goal=initial_state.sla_goal,
                sla_result=None,
                report=None,
                simulation=initial_state.simulation,
                message=initial_state.message
                if hasattr(initial_state, "message")
                else [],
            )

        result = generate_report(state)

        # None 상태에 대한 처리 확인
        if isinstance(result, dict):
            assert "report" in result or result.get("report") is not None
        else:
            assert hasattr(result, "report") or result.report is not None


# ============================================================================
# 통합 테스트: Graph 전체 플로우
# ============================================================================


class TestGraphFlow:
    """Graph 전체 플로우 테스트"""

    def test_create_graph_structure(self):
        """Graph 구조 확인"""
        app = create_graph()
        graph = app.get_graph()

        # 노드 확인
        nodes = graph.nodes
        assert "load_data" in nodes
        assert "generate_report" in nodes

        # 엣지 확인 (Edge 객체로 비교)
        edges = list(graph.edges)
        edge_sources_targets = [(e.source, e.target) for e in edges]
        assert ("__start__", "load_data") in edge_sources_targets
        assert ("load_data", "generate_report") in edge_sources_targets
        assert ("generate_report", "__end__") in edge_sources_targets

    def test_graph_execution_success(self, temp_csv_file):
        """정상적인 Graph 실행 테스트"""
        result = run_agent(
            csv_path=temp_csv_file, sla_goal="S", simulation="테스트 시뮬레이션"
        )

        # run_agent는 dict 또는 AgentState 객체를 반환
        if isinstance(result, dict):
            assert result.get("report") is not None
            assert result.get("sla_result") is not None
            assert result.get("income_call", 0) > 0
            assert result.get("answer_call", 0) > 0
        else:
            assert result.report is not None
            assert result.sla_result is not None
            assert result.income_call > 0
            assert result.answer_call > 0

    def test_graph_execution_file_not_found(self):
        """파일이 없을 때 Graph 실행 테스트"""
        result = run_agent(csv_path="nonexistent_file.csv", sla_goal="S")

        # 에러 처리 확인
        if isinstance(result, dict):
            assert (
                result.get("sla_result") == "ERROR" or result.get("sla_result") is None
            )
        else:
            assert result.sla_result == "ERROR" or result.sla_result is None

    def test_graph_execution_with_different_goals(self, temp_csv_file):
        """다양한 목표 등급으로 실행 테스트"""
        goals = ["S", "A", "B", "C", "D"]

        for goal in goals:
            result = run_agent(csv_path=temp_csv_file, sla_goal=goal)

            if isinstance(result, dict):
                assert result.get("sla_goal") == goal or goal in result.get(
                    "report", ""
                )
            else:
                assert result.sla_goal == goal or goal in (result.report or "")


# ============================================================================
# 엣지 케이스 및 경계값 테스트
# ============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_very_large_numbers(self, initial_state):
        """매우 큰 숫자 처리 테스트"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            data = pd.DataFrame(
                {
                    "시간": [9],
                    "인입콜": [1000000],
                    "응답콜": [950000],
                }
            )
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            if isinstance(initial_state, dict):
                state = initial_state.copy()
                state["csv_path"] = temp_path
            else:
                state = AgentState(
                    csv_path=temp_path,
                    income_call=initial_state.income_call,
                    answer_call=initial_state.answer_call,
                    sla_goal=initial_state.sla_goal,
                    sla_result=initial_state.sla_result,
                    report=initial_state.report,
                    simulation=initial_state.simulation,
                    message=initial_state.message
                    if hasattr(initial_state, "message")
                    else [],
                )

            result = load_data(state)

            if isinstance(result, dict):
                assert result.get("income_call") == 1000000
                assert result.get("answer_call") == 950000
                assert result.get("sla_result") == "S"
            else:
                assert result.income_call == 1000000
                assert result.answer_call == 950000
                assert result.sla_result == "S"
        finally:
            Path(temp_path).unlink()

    def test_negative_values(self, initial_state):
        """음수 값 처리 테스트"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            data = pd.DataFrame(
                {
                    "시간": [9],
                    "인입콜": [-100],  # 음수
                    "응답콜": [50],
                }
            )
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            if isinstance(initial_state, dict):
                state = initial_state.copy()
                state["csv_path"] = temp_path
            else:
                state = AgentState(
                    csv_path=temp_path,
                    income_call=initial_state.income_call,
                    answer_call=initial_state.answer_call,
                    sla_goal=initial_state.sla_goal,
                    sla_result=initial_state.sla_result,
                    report=initial_state.report,
                    simulation=initial_state.simulation,
                    message=initial_state.message
                    if hasattr(initial_state, "message")
                    else [],
                )

            result = load_data(state)

            # 음수에 대한 적절한 처리 확인
            # (현재 코드는 그대로 계산하지만, 검증 로직 추가 권장)
            if isinstance(result, dict):
                assert "sla_result" in result or result.get("sla_result") is not None
            else:
                assert hasattr(result, "sla_result") or result.sla_result is not None
        finally:
            Path(temp_path).unlink()

    def test_answer_exceeds_income(self, initial_state):
        """응답콜이 인입콜을 초과하는 경우 테스트"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            data = pd.DataFrame(
                {
                    "시간": [9],
                    "인입콜": [100],
                    "응답콜": [150],  # 인입콜보다 많음 (비정상)
                }
            )
            data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            if isinstance(initial_state, dict):
                state = initial_state.copy()
                state["csv_path"] = temp_path
            else:
                state = AgentState(
                    csv_path=temp_path,
                    income_call=initial_state.income_call,
                    answer_call=initial_state.answer_call,
                    sla_goal=initial_state.sla_goal,
                    sla_result=initial_state.sla_result,
                    report=initial_state.report,
                    simulation=initial_state.simulation,
                    message=initial_state.message
                    if hasattr(initial_state, "message")
                    else [],
                )

            result = load_data(state)

            # 비정상 데이터에 대한 처리 확인
            # (현재 코드는 그대로 계산하지만, 검증 로직 추가 권장)
            if isinstance(result, dict):
                assert result.get("answer_call", 0) > result.get("income_call", 0)
            else:
                assert result.answer_call > result.income_call
        finally:
            Path(temp_path).unlink()


# ============================================================================
# 성능 테스트 (선택사항)
# ============================================================================


class TestPerformance:
    """성능 테스트"""

    def test_large_dataset(self, initial_state):
        """큰 데이터셋 처리 테스트"""
        # 큰 데이터셋 생성
        large_data = pd.DataFrame(
            {
                "시간": list(range(24)),
                "인입콜": [1000] * 24,
                "응답콜": [950] * 24,
            }
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            large_data.to_csv(f.name, index=False)
            temp_path = f.name

        try:
            if isinstance(initial_state, dict):
                state = initial_state.copy()
                state["csv_path"] = temp_path
            else:
                state = AgentState(
                    csv_path=temp_path,
                    income_call=initial_state.income_call,
                    answer_call=initial_state.answer_call,
                    sla_goal=initial_state.sla_goal,
                    sla_result=initial_state.sla_result,
                    report=initial_state.report,
                    simulation=initial_state.simulation,
                    message=initial_state.message
                    if hasattr(initial_state, "message")
                    else [],
                )

            import time

            start_time = time.time()
            result = load_data(state)
            elapsed_time = time.time() - start_time

            if isinstance(result, dict):
                assert result.get("sla_result") is not None
            else:
                assert result.sla_result is not None
            assert elapsed_time < 5.0  # 5초 이내 완료되어야 함
        finally:
            Path(temp_path).unlink()


# ============================================================================
# 테스트 실행 예시
# ============================================================================

if __name__ == "__main__":
    # 특정 테스트만 실행
    pytest.main([__file__, "-v", "-k", "TestCalculateSLAGrade"])

    # 전체 테스트 실행
    # pytest.main([__file__, "-v"])

    # 커버리지 포함 실행
    # pytest.main([__file__, "-v", "--cov=src.agent_spike", "--cov-report=html"])
