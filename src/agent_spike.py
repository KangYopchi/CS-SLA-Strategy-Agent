"""
SLA-Agent-Manager
"""

# 1 - Data Loader
# 2 - Analyze Data
# 3 - Create Strategy
# 4 - Show the result

from typing import Annotated, Literal

import pandas as pd
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

load_dotenv()


class AgentState(BaseModel):
    csv_path: str | None = Field(default=None, description="CSV file path")
    income_call: int = Field(default=0, description="income call counts")
    answer_call: int = Field(default=0, description="answer call counts")
    sla_goal: str | None = Field(default="S", description="Goal of SLA")
    sla_result: str | None = Field(default=None, description="Result of sla")
    report: dict | None = Field(
        default=None, description="Data from AI, Report from yesterday data"
    )
    simulation: str | None = Field(default=None, description="Story of simulation")
    message: Annotated[list, add_messages] = Field(default_factory=list)


class ReportFromYesterday(BaseModel):
    summary: str = Field(description="Summany of Strategy and report")
    urgency: Literal["low", "medium", "high", "critical"]
    report: str = Field(description="Report of today's strategy")


def load_data(state: AgentState) -> AgentState:
    # state에서 csv_path를 가져오거나 기본값 사용
    csv_path = getattr(state, "csv_path", "data/yesterday_calls.csv")

    sla_result: str = "ERROR"  # 초기값 설정 (에러 발생 시 사용)

    try:
        df = pd.read_csv(csv_path)
        income_call: int = int(df["인입콜"].sum())
        answer_call: int = int(df["응답콜"].sum())

        # 0으로 나누기 방지
        if income_call == 0:
            raise ValueError("인입콜이 0입니다. 계산할 수 없습니다.")

        # 계산 순서 수정: 곱하기 후 반올림
        result = round((answer_call / income_call) * 100, 2)

        if result >= 95:
            sla_result = "S"
        elif result >= 90:
            sla_result = "A"
        elif result >= 85:
            sla_result = "B"
        elif result >= 80:
            sla_result = "C"
        elif result >= 75:
            sla_result = "D"
        else:
            sla_result = "DD"

        print(f"calculate result: {sla_result} ")
        state.income_call = income_call
        state.answer_call = answer_call
        state.sla_result = sla_result
    except FileNotFoundError:
        print(f"Data Load error: 파일을 찾을 수 없습니다 - {csv_path}")
        state.income_call = 0
        state.answer_call = 0
        state.sla_result = "ERROR"
    except Exception as e:
        print(f"Data Load error: {e}")
        state.income_call = 0
        state.answer_call = 0
        state.sla_result = "ERROR"

    return state


def generate_report(state: AgentState) -> AgentState:
    prompt = f"""
    <persona>
    당신은 목표 SLA 달성을 위한 전략을 제안하는 AI Agent입니다. 어제 일자의 데이터를 바탕으로 나온 SLA 결과를 확인하고 금일 시뮬레이션 상황에 맞는 전략을 세워주세요.
    <persona>
    <simulation>
    {state.simulation}
    </simulation>
    <report>
    어제 콜 인입량: {state.income_call}
    어제 콜 응답량: {state.answer_call}
    어제 SLA: {state.sla_result}
    목표 SLA: {state.sla_goal}
    </report>
    """

    llm = ChatOpenAI(model="gpt-5-mini")

    structured_llm = llm.with_structured_output(ReportFromYesterday)

    report = structured_llm.invoke(prompt)

    state.report = report

    return state


def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("load_data", load_data)
    workflow.add_node("generate_report", generate_report)

    workflow.add_edge(START, "load_data")
    workflow.add_edge("load_data", "generate_report")
    workflow.add_edge("generate_report", END)

    app = workflow.compile()

    return app


def run_agent(
    csv_path: str = "data/yesterday_calls.csv",
    sla_goal: str = "A",
    simulation: str | None = None,
):
    """
    Agent를 실행합니다.

    Args:
        csv_path: CSV 파일 경로
        sla_goal: 목표 SLA 등급
        simulation: 시뮬레이션 시나리오 (선택사항)

    Returns:
        실행 결과 (AgentState 객체 또는 dict)
    """
    app = create_graph()

    default_simulation = (
        "오늘 점심부터 눈이 올 예정이며, 저녁에는 폭설이 예상된다. "
        "출근 인원은 20명이며, 고객사에서 60% 이상 콜 응대를 할 경우 A 등급으로 조정해준다고 한다."
    )

    initState = AgentState(
        csv_path=csv_path,
        sla_goal=sla_goal,
        sla_result=None,
        report=None,
        simulation=simulation if simulation is not None else default_simulation,
        message=[],
    )

    result = app.invoke(initState)

    # 테스트를 위해 dict 형태로도 반환 가능하도록
    if hasattr(result, "model_dump"):
        return result.model_dump()
    elif hasattr(result, "dict"):
        return result.dict()
    else:
        return result


if __name__ == "__main__":
    result = run_agent()

    print(result["report"])
