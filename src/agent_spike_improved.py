"""
SLA-Agent-Manager (개선 버전)

개선 사항:
1. TypedDict 사용으로 LangGraph 호환성 향상
2. 계산 로직 정확도 개선
3. 에러 처리 강화
4. 함수 분리 및 재사용성 향상
5. 타입 힌트 및 문서화 추가
"""

from datetime import datetime, timedelta
from typing import Annotated, TypedDict

import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

load_dotenv()


# ============================================================================
# 상수 정의
# ============================================================================

SLA_GRADE_THRESHOLDS = {
    "S": 95.0,
    "A": 90.0,
    "B": 80.0,
    "C": 70.0,
    "D": 0.0,
}


# ============================================================================
# State 정의
# ============================================================================


class AgentState(TypedDict, total=False):
    """
    Agent 상태를 관리하는 TypedDict

    Attributes:
        csv_path: CSV 파일 경로
        income_call: 총 인입콜 수
        answer_call: 총 응답콜 수
        sla_goal: 목표 SLA 등급
        sla_result: 계산된 SLA 등급
        report: 생성된 리포트
        simulation: 시뮬레이션 시나리오
        messages: LangGraph 메시지 리스트
    """

    csv_path: str
    income_call: int
    answer_call: int
    sla_goal: str
    sla_result: str
    report: str
    simulation: str
    messages: Annotated[list, add_messages]


# ============================================================================
# 유틸리티 함수
# ============================================================================


def calculate_sla_grade(response_rate: float) -> str:
    """
    응답률을 기반으로 SLA 등급을 계산합니다.

    Args:
        response_rate: 응답률 (0-100 사이의 값)

    Returns:
        SLA 등급 (S, A, B, C, D 중 하나)

    Examples:
        >>> calculate_sla_grade(95.5)
        'S'
        >>> calculate_sla_grade(87.3)
        'B'
        >>> calculate_sla_grade(65.0)
        'D'
    """
    if response_rate >= SLA_GRADE_THRESHOLDS["S"]:
        return "S"
    elif response_rate >= SLA_GRADE_THRESHOLDS["A"]:
        return "A"
    elif response_rate >= SLA_GRADE_THRESHOLDS["B"]:
        return "B"
    elif response_rate >= SLA_GRADE_THRESHOLDS["C"]:
        return "C"
    else:
        return "D"


def is_goal_achieved(current_grade: str, goal_grade: str) -> bool:
    """
    목표 등급 달성 여부를 판단합니다.

    Args:
        current_grade: 현재 SLA 등급
        goal_grade: 목표 SLA 등급

    Returns:
        목표 달성 여부
    """
    grade_order = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, "DD": 0}
    current_score = grade_order.get(current_grade, 0)
    goal_score = grade_order.get(goal_grade, 0)
    return current_score >= goal_score


def validate_dataframe(df: pd.DataFrame) -> tuple[bool, str | None]:
    """
    데이터프레임의 유효성을 검증합니다.

    Args:
        df: 검증할 데이터프레임

    Returns:
        (유효성 여부, 에러 메시지)
    """
    if df.empty:
        return False, "CSV 파일이 비어있습니다"

    required_columns = ["인입콜", "응답콜"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"필수 컬럼이 없습니다: {missing_columns}"

    # 음수 값 체크
    if (df["인입콜"] < 0).any() or (df["응답콜"] < 0).any():
        return False, "인입콜 또는 응답콜에 음수 값이 있습니다"

    # 응답콜이 인입콜을 초과하는 경우 경고 (에러는 아님)
    if (df["응답콜"] > df["인입콜"]).any():
        print("⚠️ 경고: 일부 시간대에서 응답콜이 인입콜을 초과합니다")

    return True, None


# ============================================================================
# Node 함수들
# ============================================================================


def load_data(state: AgentState) -> AgentState:
    """
    CSV 파일을 읽어서 데이터를 로드하고 SLA를 계산합니다.

    Args:
        state: 현재 Agent 상태

    Returns:
        업데이트된 Agent 상태
    """
    csv_path = state.get("csv_path", "data/yesterday_calls.csv")

    try:
        # CSV 파일 읽기
        df = pd.read_csv(csv_path)

        # 데이터 검증
        is_valid, error_message = validate_dataframe(df)
        if not is_valid:
            raise ValueError(error_message or "데이터 검증 실패")

        # 집계 계산
        income_call = int(df["인입콜"].sum())
        answer_call = int(df["응답콜"].sum())

        # 0으로 나누기 방지
        if income_call == 0:
            raise ValueError("인입콜이 0입니다. 계산할 수 없습니다.")

        # 응답률 계산 (정확한 순서: 곱하기 후 반올림)
        response_rate = (answer_call / income_call) * 100
        response_rate = round(response_rate, 2)

        # SLA 등급 계산
        sla_result = calculate_sla_grade(response_rate)

        # 상태 업데이트
        state["income_call"] = income_call
        state["answer_call"] = answer_call
        state["sla_result"] = sla_result

        print(
            f"✅ 데이터 로드 완료: 인입콜={income_call:,}, 응답콜={answer_call:,}, SLA={sla_result} ({response_rate}%)"
        )

    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {csv_path}")
        state["sla_result"] = "ERROR"
        state["income_call"] = 0
        state["answer_call"] = 0
    except ValueError as e:
        print(f"❌ 데이터 검증 실패: {e}")
        state["sla_result"] = "ERROR"
        state["income_call"] = 0
        state["answer_call"] = 0
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        state["sla_result"] = "ERROR"
        state["income_call"] = 0
        state["answer_call"] = 0

    return state


def generate_report(state: AgentState) -> AgentState:
    """
    계산된 SLA 데이터를 바탕으로 리포트를 생성합니다.

    Args:
        state: 현재 Agent 상태

    Returns:
        업데이트된 Agent 상태 (report 필드 포함)
    """
    # 데이터 검증
    if state.get("sla_result") is None or state.get("sla_result") == "ERROR":
        state["report"] = "❌ 데이터 로드 실패로 리포트를 생성할 수 없습니다."
        return state

    # 날짜 정보
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y년 %m월 %d일")

    # 데이터 추출
    income_call = state.get("income_call", 0)
    answer_call = state.get("answer_call", 0)
    sla_result = state.get("sla_result", "N/A")
    sla_goal = state.get("sla_goal", "N/A")
    simulation = state.get("simulation")

    # 응답률 계산
    response_rate = (
        round((answer_call / income_call * 100), 2) if income_call > 0 else 0.0
    )

    # 목표 달성 여부
    goal_achieved = (
        is_goal_achieved(sla_result, sla_goal) if sla_goal != "N/A" else None
    )

    # 리포트 생성
    report = f"""
# 📊 콜센터 SLA 분석 리포트

## 📅 분석 일자
{yesterday}

## 📈 전체 통계
- **전체 인입콜**: {income_call:,}건
- **전체 응답콜**: {answer_call:,}건
- **전체 응답률**: {response_rate:.2f}%
- **현재 SLA 등급**: {sla_result}
- **목표 SLA 등급**: {sla_goal}
"""

    # 목표 달성 여부
    if goal_achieved is not None:
        status_emoji = "✅" if goal_achieved else "⚠️"
        status_text = (
            "목표를 달성했습니다!" if goal_achieved else "목표를 달성하지 못했습니다."
        )
        report += f"""
## {status_emoji} 목표 달성 여부
{status_text}
"""

    # 시뮬레이션 정보가 있으면 추가
    if simulation:
        report += f"""
## 🎯 시뮬레이션 시나리오
{simulation}
"""

    report += """
---
*리포트 생성 완료*
"""

    state["report"] = report
    print("✅ 리포트 생성 완료")

    return state


# ============================================================================
# Graph 구성
# ============================================================================


def create_graph():
    """
    LangGraph를 생성하고 구성합니다.

    Returns:
        컴파일된 LangGraph 앱
    """
    workflow = StateGraph(AgentState)

    # Node 추가
    workflow.add_node("load_data", load_data)
    workflow.add_node("generate_report", generate_report)

    # Edge 추가
    workflow.add_edge(START, "load_data")
    workflow.add_edge("load_data", "generate_report")
    workflow.add_edge("generate_report", END)

    # 컴파일
    app = workflow.compile()

    return app


# ============================================================================
# 실행 함수
# ============================================================================


def run_agent(
    csv_path: str = "data/yesterday_calls.csv",
    sla_goal: str = "S",
    simulation: str | None = None,
) -> dict:
    """
    Agent를 실행합니다.

    Args:
        csv_path: CSV 파일 경로
        sla_goal: 목표 SLA 등급
        simulation: 시뮬레이션 시나리오 (선택사항)

    Returns:
        실행 결과 딕셔너리
        - success: 성공 여부
        - report: 생성된 리포트
        - sla_result: 계산된 SLA 등급
        - income_call: 총 인입콜
        - answer_call: 총 응답콜
        - error: 에러 메시지 (실패 시)
    """
    app = create_graph()

    initial_state: AgentState = {
        "csv_path": csv_path,
        "income_call": 0,
        "answer_call": 0,
        "sla_goal": sla_goal,
        "sla_result": None,
        "report": None,
        "simulation": simulation,
        "messages": [],
    }

    print("=" * 60)
    print("📊 콜센터 SLA 분석 Agent 시작")
    print("=" * 60)
    print(f"CSV 경로: {csv_path}")
    print(f"목표 등급: {sla_goal}")
    if simulation:
        print(f"시뮬레이션: {simulation[:50]}...")
    print("=" * 60 + "\n")

    try:
        result = app.invoke(initial_state)

        return {
            "success": True,
            "report": result.get("report"),
            "sla_result": result.get("sla_result"),
            "income_call": result.get("income_call", 0),
            "answer_call": result.get("answer_call", 0),
            "sla_goal": result.get("sla_goal"),
        }
    except Exception as e:
        print(f"❌ Agent 실행 실패: {e}")
        return {
            "success": False,
            "error": str(e),
            "report": None,
            "sla_result": None,
            "income_call": 0,
            "answer_call": 0,
        }


# ============================================================================
# 메인 실행
# ============================================================================

if __name__ == "__main__":
    print("=== 콜센터 SLA 분석 Agent (개선 버전) ===\n")

    # 리포트 생성
    result = run_agent(
        csv_path="data/yesterday_calls.csv",
        sla_goal="A",
        simulation="오늘 점심부터 눈이 올 예정이며, 저녁에는 폭설이 예상된다. 출근 인원은 20명이며, 고객사에서 60% 이상 콜 응대를 할 경우 A 등급으로 조정해준다고 한다.",
    )

    if result["success"]:
        print(result["report"])
    else:
        print(f"❌ 실행 실패: {result.get('error')}")
